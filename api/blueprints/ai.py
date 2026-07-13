"""Ollama AI routes."""

import os

import requests
from flask import Blueprint, jsonify, request

ai_bp = Blueprint('ai', __name__)

OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')

try:
    OLLAMA_AVAILABLE = requests.get(f'{OLLAMA_URL}/api/tags', timeout=2).status_code == 200
except Exception:
    OLLAMA_AVAILABLE = False


@ai_bp.route('/api/ai/ollama/status', methods=['GET'])
def ollama_status():
    return jsonify({'available': OLLAMA_AVAILABLE, 'url': OLLAMA_URL})


@ai_bp.route('/api/ai/ollama/models', methods=['GET'])
def list_ollama_models():
    if not OLLAMA_AVAILABLE:
        return jsonify({'error': 'Ollama not running', 'models': []})
    try:
        resp = requests.get(f'{OLLAMA_URL}/api/tags', timeout=5)
        return jsonify({'success': True, 'models': [model['name'] for model in resp.json().get('models', [])]})
    except Exception as exc:
        return jsonify({'error': str(exc)})


@ai_bp.route('/api/ai/ollama/chat', methods=['POST'])
def ollama_chat():
    if not OLLAMA_AVAILABLE:
        return jsonify({'error': 'Ollama not running'}), 500
    data = request.json or {}
    try:
        resp = requests.post(
            f'{OLLAMA_URL}/api/chat',
            json={
                'model': data.get('model', 'llama3.2'),
                'messages': [{'role': 'user', 'content': data.get('message')}],
                'stream': False,
            },
            timeout=30,
        )
        return jsonify({'success': True, 'response': resp.json()['message']['content']})
    except Exception as exc:
        return jsonify({'error': str(exc)})
