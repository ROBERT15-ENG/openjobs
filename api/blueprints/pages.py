"""HTML page routes."""

import datetime
import os

from config import TEMPLATES_DIR
from flask import Blueprint, jsonify, render_template

pages_bp = Blueprint('pages', __name__)


def _render_page(template, fallback=None):
    path = os.path.join(TEMPLATES_DIR, template)
    if os.path.exists(path):
        return render_template(template)
    return jsonify(fallback or {'error': 'Page not found'}), 404


@pages_bp.route('/ai')
def ai_page():
    return _render_page('ai.html', {'ai': True})


@pages_bp.route('/')
def index():
    return _render_page('index.html', {
        'msg': 'OpenJobs API',
        'endpoints': ['/api/jobs', '/api/companies', '/api/ai/ollama/status'],
    })


@pages_bp.route('/robots.txt')
def robots():
    return (
        'User-agent: *\nAllow: /\nDisallow: /user\nDisallow: /employer\nDisallow: /admin\nDisallow: /api/\n',
        {'Content-Type': 'text/plain'},
    )


@pages_bp.route('/job.html')
@pages_bp.route('/job')
def job_page():
    return _render_page('job.html')


@pages_bp.route('/companies')
def companies_page():
    return _render_page('company.html', {'companies': []})


@pages_bp.route('/salary')
def salary_page():
    return _render_page('salary.html', {'predict': True})


@pages_bp.route('/login')
def login_page():
    return _render_page('login.html')


@pages_bp.route('/register')
def register_page():
    return _render_page('register.html')


@pages_bp.route('/forgot-password')
def forgot_password_page():
    return _render_page('forgot-password.html')


@pages_bp.route('/reset-password.html')
def reset_password_page():
    return _render_page('reset-password.html')


@pages_bp.route('/user')
def user_page():
    return _render_page('user.html', {'dashboard': True})


@pages_bp.route('/employer')
def employer_page():
    return _render_page('employer.html', {'employer': True})


@pages_bp.route('/admin')
def admin_page():
    return _render_page('admin.html', {'admin': True})


@pages_bp.route('/privacy')
def privacy_page():
    return _render_page('privacy.html', {'privacy': True})


@pages_bp.route('/terms')
def terms_page():
    return _render_page('terms.html', {'terms': True})


@pages_bp.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.datetime.now().isoformat()})
