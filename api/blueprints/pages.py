"""HTML page routes."""

import datetime
import os

from config import TEMPLATES_DIR
from db import get_db
from flask import Blueprint, current_app, jsonify, redirect, render_template, request
from seo_util import job_posting_json_ld, job_url_path, slugify

pages_bp = Blueprint('pages', __name__)


def _render_page(template, fallback=None, **context):
    path = os.path.join(TEMPLATES_DIR, template)
    if os.path.exists(path):
        return render_template(template, **context)
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
    base = current_app.config.get('BASE_URL', '').rstrip('/')
    return (
        'User-agent: *\n'
        'Allow: /\n'
        'Disallow: /user\n'
        'Disallow: /employer\n'
        'Disallow: /admin\n'
        'Disallow: /api/\n'
        f'Sitemap: {base}/sitemap.xml\n',
        {'Content-Type': 'text/plain'},
    )


@pages_bp.route('/sitemap.xml')
def sitemap():
    db = get_db()
    base = current_app.config.get('BASE_URL', '').rstrip('/')
    jobs = db.execute(
        'SELECT id, title, created_at FROM jobs WHERE is_active = 1 ORDER BY created_at DESC LIMIT 500'
    ).fetchall()
    urls = [
        f'  <url><loc>{base}/</loc><changefreq>hourly</changefreq><priority>1.0</priority></url>',
        f'  <url><loc>{base}/companies</loc><changefreq>daily</changefreq><priority>0.8</priority></url>',
        f'  <url><loc>{base}/salary</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>',
    ]
    for job in jobs:
        loc = f"{base}{job_url_path(job['id'], job['title'])}"
        lastmod = (job['created_at'] or '')[:10]
        urls.append(
            f'  <url><loc>{loc}</loc>'
            + (f'<lastmod>{lastmod}</lastmod>' if lastmod else '')
            + '<changefreq>weekly</changefreq><priority>0.9</priority></url>'
        )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + '\n'.join(urls)
        + '\n</urlset>'
    )
    return body, {'Content-Type': 'application/xml'}


@pages_bp.route('/jobs/<int:job_id>')
@pages_bp.route('/jobs/<int:job_id>/<slug>')
def job_seo_page(job_id, slug=None):
    db = get_db()
    job = db.execute('SELECT * FROM jobs WHERE id = ? AND is_active = 1', (job_id,)).fetchone()
    if not job:
        return _render_page('job.html'), 404
    job_dict = dict(job)
    canonical_slug = slugify(job_dict.get('title', ''))
    if slug and slug != canonical_slug:
        return redirect(job_url_path(job_id, job_dict.get('title', '')), code=301)
    base_url = current_app.config.get('BASE_URL', 'http://localhost:5700')
    json_ld = job_posting_json_ld(job_dict, base_url)
    return _render_page(
        'job.html',
        job=job_dict,
        json_ld=json_ld,
        canonical_url=f"{base_url.rstrip('/')}{job_url_path(job_id, job_dict.get('title', ''))}",
    )


@pages_bp.route('/job.html')
@pages_bp.route('/job')
def job_page():
    job_id = request.args.get('id', type=int)
    if job_id:
        db = get_db()
        job = db.execute('SELECT title FROM jobs WHERE id = ?', (job_id,)).fetchone()
        if job:
            return redirect(job_url_path(job_id, job['title']), code=301)
    return _render_page('job.html')


@pages_bp.route('/companies')
def companies_page():
    return _render_page('company.html', {'companies': []})


@pages_bp.route('/salary')
def salary_page():
    return _render_page('salary.html', {'predict': True})


@pages_bp.route('/cad')
def cad_redirect():
    return redirect('/?q=autocad', code=302)


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
@pages_bp.route('/reset-password')
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
