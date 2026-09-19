"""Ollama AI routes with keyword fallbacks when Ollama is unavailable locally.

All generative AI endpoints require login. Rate limits are keyed by user id
(not IP) so quotas follow the account.
"""

import os
import threading
import time

import requests
from ats_util import compute_ats_score
from auth_utils import require_auth
from extensions import ai_rate_limit_key, limiter
from flask import Blueprint, jsonify, request

ai_bp = Blueprint('ai', __name__)

OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2')
OLLAMA_PROBE_TTL = int(os.environ.get('OLLAMA_PROBE_TTL', '60'))

_probe_lock = threading.Lock()
_probe_state = {'available': False, 'checked_at': 0.0}


def ollama_available(force: bool = False) -> bool:
    """Cached liveness probe; re-checked every OLLAMA_PROBE_TTL seconds so a
    restart of Ollama (either direction) is picked up without redeploying."""
    if os.environ.get('JOBSEEK_AI_ENABLED', 'true').lower() in ('0', 'false', 'no'):
        return False
    now = time.monotonic()
    with _probe_lock:
        if not force and now - _probe_state['checked_at'] < OLLAMA_PROBE_TTL:
            return _probe_state['available']
        try:
            available = requests.get(f'{OLLAMA_URL}/api/tags', timeout=2).status_code == 200
        except requests.RequestException:
            available = False
        _probe_state.update(available=available, checked_at=now)
        return available


def _ollama_generate(prompt: str, system: str = None, timeout: int = 45) -> str:
    if not ollama_available():
        return ''
    payload = {
        'model': OLLAMA_MODEL,
        'prompt': prompt,
        'stream': False,
    }
    if system:
        payload['system'] = system
    try:
        resp = requests.post(f'{OLLAMA_URL}/api/generate', json=payload, timeout=timeout)
        if resp.status_code == 200:
            return resp.json().get('response', '').strip()
    except Exception:
        pass
    return ''


def _fallback_cover_letter(job_title: str, company: str, resume_text: str) -> str:
    snippet = (resume_text or '').strip().split('\n')[0][:120]
    return (
        f'Dear Hiring Manager,\n\n'
        f'I am writing to apply for the {job_title} role at {company}. '
        f'{"My background includes " + snippet + "." if snippet else "I believe my experience aligns well with this opportunity."}\n\n'
        f'I am excited about the chance to contribute to {company} and would welcome the opportunity to discuss how I can add value to your team.\n\n'
        f'Kind regards'
    )


def _fallback_interview_questions(job_title: str) -> str:
    return '\n'.join([
        f'1. Walk me through your experience most relevant to a {job_title} role.',
        '2. Describe a challenging project you delivered and what you learned.',
        '3. How do you prioritise when multiple stakeholders need your attention?',
        '4. Tell me about a time you received critical feedback and how you responded.',
        f'5. What interests you about working as a {job_title}?',
        '6. Describe your approach to collaborating with cross-functional teams.',
    ])


def _ai_limit(limit: str):
    """Per-user quota. Keep @require_auth above this so user_id is set first."""
    return limiter.limit(limit, key_func=ai_rate_limit_key)


@ai_bp.route('/api/ai/ollama/status', methods=['GET'])
def ollama_status():
    """Public availability probe — no generation, no auth required."""
    return jsonify({
        'available': ollama_available(),
        'note': 'Ollama is optional — AI tools use keyword fallbacks when it is not running locally. Generative endpoints require login.',
        'auth_required_for_generation': True,
    })


@ai_bp.route('/api/ai/ollama/models', methods=['GET'])
@require_auth
def list_ollama_models():
    if not ollama_available():
        return jsonify({'error': 'Ollama not running', 'models': []})
    try:
        resp = requests.get(f'{OLLAMA_URL}/api/tags', timeout=5)
        return jsonify({'success': True, 'models': [model['name'] for model in resp.json().get('models', [])]})
    except Exception:
        return jsonify({'error': 'Could not list models', 'models': []})


@ai_bp.route('/api/ai/ollama/chat', methods=['POST'])
@require_auth
@_ai_limit('20 per hour')
def ollama_chat():
    data = request.json or {}
    message = (data.get('message') or '').strip()
    if not message:
        return jsonify({'error': 'message is required'}), 400
    if not ollama_available():
        return jsonify({
            'error': 'Ollama not running locally',
            'response': 'AI chat requires Ollama on your machine (ollama serve). Career tips: tailor your résumé to each role, quantify achievements, and research the company before applying.',
        }), 200
    try:
        resp = requests.post(
            f'{OLLAMA_URL}/api/chat',
            json={
                'model': data.get('model', OLLAMA_MODEL),
                'messages': [{'role': 'user', 'content': message}],
                'stream': False,
            },
            timeout=30,
        )
        return jsonify({'success': True, 'response': resp.json()['message']['content']})
    except Exception:
        return jsonify({'error': 'AI chat failed'}), 500


@ai_bp.route('/api/ai/ollama/score/resume', methods=['POST'])
@require_auth
@_ai_limit('30 per hour')
def score_resume():
    data = request.json or {}
    job_desc = (data.get('job_description') or '').strip()
    resume = (data.get('resume_text') or '').strip()
    if not job_desc or not resume:
        return jsonify({'error': 'job_description and resume_text are required'}), 400

    score = compute_ats_score(resume, '', job_desc)
    analysis = 'Keyword overlap between your résumé and the job description.'
    source = 'keyword'

    if ollama_available():
        prompt = (
            f'Job description:\n{job_desc[:1500]}\n\nRésumé:\n{resume[:1500]}\n\n'
            'In 2-3 sentences, explain fit strengths and gaps. Be concise.'
        )
        ai_text = _ollama_generate(prompt, system='You are a concise career coach.')
        if ai_text:
            analysis = ai_text
            source = 'ollama'

    return jsonify({'score': score, 'analysis': analysis, 'source': source})


@ai_bp.route('/api/ai/ollama/generate/cover-letter', methods=['POST'])
@require_auth
@_ai_limit('20 per hour')
def generate_cover_letter():
    data = request.json or {}
    job_title = (data.get('job_title') or '').strip()
    company = (data.get('company') or '').strip()
    resume = (data.get('resume_text') or '').strip()
    if not job_title or not company:
        return jsonify({'error': 'job_title and company are required'}), 400

    cover_letter = _fallback_cover_letter(job_title, company, resume)
    source = 'template'

    if ollama_available():
        prompt = (
            f'Write a professional cover letter for the {job_title} position at {company}. '
            f'Candidate background:\n{resume[:2000] or "Not provided"}\n'
            'Use a warm, professional tone. 3 short paragraphs.'
        )
        ai_text = _ollama_generate(prompt, system='You write concise, professional cover letters.')
        if ai_text and len(ai_text) > 80:
            cover_letter = ai_text
            source = 'ollama'

    return jsonify({'cover_letter': cover_letter, 'source': source})


@ai_bp.route('/api/ai/ollama/interview-prep', methods=['POST'])
@require_auth
@_ai_limit('20 per hour')
def interview_prep():
    data = request.json or {}
    job_title = (data.get('job_title') or '').strip()
    if not job_title:
        return jsonify({'error': 'job_title is required'}), 400

    questions = _fallback_interview_questions(job_title)
    source = 'template'

    if ollama_available():
        prompt = f'List 8 interview questions for a {job_title} role. Number each question.'
        ai_text = _ollama_generate(prompt, system='You are an interview coach.')
        if ai_text:
            questions = ai_text
            source = 'ollama'

    return jsonify({'questions': questions, 'source': source})
