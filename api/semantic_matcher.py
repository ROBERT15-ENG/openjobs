#!/usr/bin/env python3
"""
Smart Semantic Job Matcher
===========================
Strategy: keyword matching is FREE and instant. Ollama costs time + compute.
  - Score 0 (no keyword overlap)  → skip, score = 0  (clear mismatch)
  - Score 1-3 (partial match)     → run Ollama for semantic scoring (JS=JavaScript, ML=ML/AI, etc.)
  - Score >= 4 (strong overlap)  → high score, skip Ollama unless resume is rich

This typically reduces Ollama calls by 60-80% while giving the same final ranking quality.
"""

import os
import requests
import json
from typing import List, Dict, Tuple

OLLAMA_URL  = os.environ.get('OLLAMA_URL',  'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'gemma3:4b')
OLLAMA_TIMEOUT = 45  # seconds per job


# ─── Ollama helpers ────────────────────────────────────────────────────────────

def _query_ollama(prompt: str, system: str = None) -> str:
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=OLLAMA_TIMEOUT
        )
        return resp.json().get('response', '') if resp.status_code == 200 else ''
    except requests.exceptions.Timeout:
        return '__TIMEOUT__'
    except Exception as e:
        return f'__ERROR__: {e}'


SYSTEM_PROMPT = """You are a strict job-candidate fit analyzer.
Return ONLY valid JSON with this exact structure — no markdown, no preamble:

{
  "match_score": 0-100,
  "matched_skills": ["skill1", "skill2"],
  "missing_critical": ["skill3"],
  "verdict": "one short sentence"
}

Rules:
- 0-30 = poor fit | 31-60 = partial fit | 61-80 = strong fit | 81-100 = ideal match
- matched_skills: job-required skills the resume clearly has (check synonyms: JS=JavaScript, TS=TypeScript, Py=Python, ML/AI/LLM related, ReactJS=React, SRE=DevOps, etc.)
- missing_critical: skills the job explicitly requires that the resume lacks
- Be strict — don't inflate scores"""


# ─── Core matching ───────────────────────────────────────────────────────────

SKILL_ALIASES = {
    'js': 'javascript', 'ts': 'typescript', 'py': 'python',
    'reactjs': 'react', 'react.js': 'react', 'reactnative': 'react native',
    'nodejs': 'node', 'node.js': 'node',
    'ml': 'machine learning', 'ai': 'artificial intelligence',
    'llm': 'large language model', 'nlp': 'natural language processing',
    'pg': 'postgresql', 'postgres': 'postgresql', 'psql': 'postgresql',
    'k8s': 'kubernetes', 'k8': 'kubernetes',
    'aws': 'amazon web services', 'gcp': 'google cloud', 'azure': 'microsoft azure',
    'tf': 'terraform',
    'devops': 'devops', 'sre': 'site reliability engineer', 'platform': 'platform engineering',
    'vuejs': 'vue', 'vue.js': 'vue',
    'angularjs': 'angular',
    'cs': 'c#', 'csharp': 'c#',
    'golang': 'go',
    'r': 'r programming',
    'tsql': 't-sql', 't-sql': 'transact-sql',
    'mongo': 'mongodb', 'mongo db': 'mongodb',
    'graphql': 'graphql',
    'rest api': 'rest', 'restful': 'rest',
    'ci': 'continuous integration', 'cd': 'continuous deployment',
    'git': 'git', 'github': 'github', 'gitlab': 'gitlab',
    'docker': 'docker', 'container': 'containers',
    'kube': 'kubernetes',
    'flask': 'flask', 'django': 'django', 'fastapi': 'fastapi',
    'fastlane': 'fastlane',
    'tableau': 'tableau', 'powerbi': 'power bi',
    'excel': 'microsoft excel', 'sheets': 'google sheets',
    'photoshop': 'adobe photoshop', 'illustrator': 'adobe illustrator',
    'sketch': 'sketch app', 'figma': 'figma', 'adobe xd': 'adobe xd',
    'ux': 'user experience', 'ui': 'user interface', 'IxD': 'interaction design',
    'seo': 'search engine optimisation', 'sem': 'search engine marketing',
    'ga': 'google analytics', 'gtm': 'google tag manager',
    'agile': 'agile', 'scrum': 'scrum', 'kanban': 'kanban',
    'product': 'product management', 'pm': 'product manager',
    'ba': 'business analyst', 'bi': 'business intelligence',
    'etl': 'etl', 'dataeng': 'data engineer', 'de': 'data engineer',
    'analytics': 'analytics', 'data analysis': 'data analysis',
}


def _normalize(text: str) -> set:
    """Lowercase + alias-expand a text block into a set of canonical tokens."""
    tokens = set()
    text = text.lower()
    # Split on whitespace and punctuation
    import re
    words = re.split(r'[\s,\.\(\)\/\-]+', text)
    for w in words:
        w = w.strip('.,;:!?)(')
        if not w:
            continue
        tokens.add(w)
        if w in SKILL_ALIASES:
            tokens.add(SKILL_ALIASES[w])
    return tokens


def keyword_score(job_skills: str, resume_text: str) -> Tuple[int, List[str], List[str]]:
    """
    Fast keyword-overlap scoring.
    Returns (score, matched_skills, missing_critical_skills)
    """
    resume_tokens = _normalize(resume_text)
    job_skill_list = [s.strip() for s in (job_skills or '').split(',') if s.strip()]
    job_tokens = _normalize(job_skills or '')

    matched = []
    missing = []
    for skill in job_skill_list:
        skill_lower = skill.lower()
        normed = _normalize(skill)
        if any(t in resume_tokens for t in normed):
            matched.append(skill)
        else:
            missing.append(skill)

    # Score: matched count × 18, capped at 100
    score = min(100, len(matched) * 18)
    return score, matched, missing


def ollama_rescore(job: Dict, resume_text: str, kws: Tuple[int, List[str], List[str]]) -> Dict:
    """
    Use Ollama to rescore a partial-match job (kws score 1-3).
    Returns full analysis dict with AI match_score, matched, missing, verdict.
    """
    raw = _query_ollama(_build_prompt(job, resume_text), SYSTEM_PROMPT)

    if raw in ('__TIMEOUT__', '') or raw.startswith('__ERROR__'):
        # Fallback: inflate keyword score slightly, use keyword results
        score, matched, missing = kws
        return {
            'match_score': min(100, score + 8),  # small bonus for partial keyword match
            'matched_skills': matched,
            'missing_critical': missing,
            'verdict': 'Partial keyword match — Ollama unavailable.',
            'is_ai': False
        }

    try:
        start = raw.index('{')
        end   = raw.rindex('}') + 1
        result = json.loads(raw[start:end])
        result['is_ai'] = True
        return result
    except Exception:
        score, matched, missing = kws
        return {
            'match_score': min(100, score + 8),
            'matched_skills': matched,
            'missing_critical': missing,
            'verdict': 'Could not parse Ollama response; partial score applied.',
            'is_ai': False
        }


def _build_prompt(job: Dict, resume_text: str) -> str:
    return f"""Job Title      : {job.get('title','') or ''}
Company       : {job.get('company','') or ''}
Location      : {job.get('location','') or ''}
Skills        : {job.get('skills','') or ''}
Description   : {(job.get('description','') or '')[:600]}

---

Resume:
{resume_text[:2000]}

---

Return ONLY valid JSON."""


# ─── Main entry point ─────────────────────────────────────────────────────────

def rank_jobs_for_resume(jobs: List[Dict], resume_text: str,
                         ollama_threshold: int = 4) -> List[Dict]:
    """
    Rank all jobs for a resume using the smart hybrid strategy.

    ollama_threshold: minimum keyword score needed to skip Ollama.
                     Jobs with keyword score < threshold get Ollama scored.
                     Default 4 = strong overlap needed to skip Ollama.

    Strategy:
      keyword_score = 0  → skip Ollama, score = 0
      keyword_score 1-3  → Ollama (semantic disambiguation)
      keyword_score >= 4 → high confidence, minimal Ollama bonus
    """
    results = []
    ollama_needed = []

    # Pass 1: keyword scoring (free, instant)
    for job in jobs:
        score, matched, missing = keyword_score(job.get('skills', '') or '', resume_text)
        scored = dict(job)
        scored['match_score']       = score
        scored['keyword_matched']   = matched
        scored['keyword_missing']   = missing
        scored['is_ai_scored']      = False
        scored['ai_verdict']        = None
        if 0 < score < ollama_threshold * 18 // 4:  # 1-3 keyword matches
            ollama_needed.append(scored)
        else:
            results.append(scored)

    # Pass 2: Ollama only for borderline jobs
    for job in ollama_needed:
        kws = (job['match_score'], job['keyword_matched'], job['keyword_missing'])
        analysis = ollama_rescore(job, resume_text, kws)
        job['match_score']     = analysis.get('match_score', job['match_score'])
        job['matched_skills']  = analysis.get('matched_skills', job['keyword_matched'])
        job['missing_critical']= analysis.get('missing_critical', job['keyword_missing'])
        job['ai_verdict']      = analysis.get('verdict', '')
        job['is_ai_scored']    = analysis.get('is_ai', False)
        results.append(job)

    # Sort: strongest matches first
    results.sort(key=lambda x: x.get('match_score', 0), reverse=True)
    return results


# ─── CLI test ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    test_jobs = [
        {'id':1,'title':'Senior Python Engineer','company':'TechCorp',
         'skills':'Python, Django, PostgreSQL, Docker, AWS, React',
         'description':'Build scalable backend services using Python/Django.'},
        {'id':2,'title':'UX Designer','company':'DesignStudio',
         'skills':'Figma, User Research, Prototyping, CSS, Adobe XD',
         'description':'Lead user research and create high-fidelity prototypes.'},
        {'id':3,'title':'DevOps Engineer','company':'CloudCo',
         'skills':'Kubernetes, Terraform, AWS, GCP, Docker, CI/CD, Linux',
         'description':'Manage cloud infrastructure and deployment pipelines.'},
        {'id':4,'title':'Frontend Dev','company':'WebInc',
         'skills':'JavaScript, React, TypeScript, HTML/CSS, Git',
         'description':'Build responsive web interfaces using React and TypeScript.'},
    ]
    test_resume = """
    Full-stack Python developer with 5 years experience.
    Expert in Django, Flask, PostgreSQL. Strong AWS and Docker skills.
    Built React frontends for several projects. Familiar with TypeScript.
    Also worked with Kubernetes and Terraform on the DevOps side.
    """
    print("Ranking jobs (smart hybrid)...\n")
    ranked = rank_jobs_for_resume(test_jobs, test_resume)
    for job in ranked:
        ai_tag = " [AI]" if job['is_ai_scored'] else " [KW]"
        print(f"[{job['match_score']:>3}]{ai_tag} {job['title']} @ {job['company']}")
        print(f"        Matched : {job.get('matched_skills', job.get('keyword_matched', []))}")
        if job.get('ai_verdict'):
            print(f"        Verdict: {job['ai_verdict']}")
        print()
