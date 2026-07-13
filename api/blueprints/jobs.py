"""Job listing routes."""

import datetime
import json

from auth_utils import require_auth
from constants import SEEKER_ROLES
from db import get_db
from extensions import limiter
from flask import Blueprint, jsonify, request

jobs_bp = Blueprint('jobs', __name__)


@jobs_bp.route('/api/jobs', methods=['GET'])
def get_jobs():
    db = get_db()
    page = request.args.get('page', 1, type=int)
    limit = min(request.args.get('limit', 50, type=int), 100)
    offset = (page - 1) * limit

    where = ['is_active = 1']
    params = []

    category = request.args.get('category')
    location = request.args.get('location')
    work_type = request.args.get('work_type')
    work_arrangement = request.args.get('work_arrangement')
    search = request.args.get('q', '').strip()
    min_salary = request.args.get('min_salary', type=int)
    max_salary = request.args.get('max_salary', type=int)

    if category:
        where.append('category = ?')
        params.append(category)
    if location:
        where.append('location LIKE ?')
        params.append(f'%{location}%')
    if work_type:
        wts = [w.strip() for w in work_type.split(',') if w.strip()]
        if len(wts) == 1:
            where.append('work_type = ?')
            params.append(wts[0])
        else:
            placeholders = ','.join('?' * len(wts))
            where.append(f'work_type IN ({placeholders})')
            params.extend(wts)
    if work_arrangement:
        was = [w.strip() for w in work_arrangement.split(',') if w.strip()]
        if len(was) == 1:
            where.append('work_arrangement = ?')
            params.append(was[0])
        else:
            placeholders = ','.join('?' * len(was))
            where.append(f'work_arrangement IN ({placeholders})')
            params.extend(was)
    if min_salary:
        where.append('(salary_max >= ? OR (salary_max IS NULL AND salary_min >= ?))')
        params.extend([min_salary, min_salary])
    if max_salary:
        where.append('(salary_min <= ? OR (salary_min IS NULL AND salary_max <= ?))')
        params.extend([max_salary, max_salary])
    if search:
        where.append('(title LIKE ? OR company LIKE ? OR description LIKE ? OR search_summary LIKE ?)')
        params.extend([f'%{search}%'] * 4)

    where_clause = ' AND '.join(where)
    total = db.execute(f'SELECT COUNT(*) FROM jobs WHERE {where_clause}', params).fetchone()[0]
    jobs = db.execute(
        f'SELECT * FROM jobs WHERE {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?',
        params + [limit, offset],
    ).fetchall()
    return jsonify({
        'jobs': [dict(job) for job in jobs],
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'pages': (total + limit - 1) // limit,
        },
    })


@jobs_bp.route('/api/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    db = get_db()
    job = db.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    if not job:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(job))


@jobs_bp.route('/api/jobs', methods=['POST'])
@require_auth
def create_job():
    data = request.json or {}
    required = ['title', 'company', 'location', 'description']
    missing = [field for field in required if not data.get(field)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    db = get_db()
    expires_at = data.get('expires_at') or (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
    employer_id = getattr(request, 'employer_id', None)
    db.execute(
        """INSERT INTO jobs (
            title, company, location, description, salary, category, is_active, created_at,
            work_type, work_arrangement, salary_min, salary_max, salary_currency,
            search_summary, selling_points, video_url, expires_at, skills, employer_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get('title'),
            data.get('company'),
            data.get('location'),
            data.get('description'),
            data.get('salary', 'Competitive'),
            data.get('category', 'General'),
            1,
            datetime.datetime.now().isoformat(),
            data.get('work_type', 'full_time'),
            data.get('work_arrangement', 'remote'),
            data.get('salary_min'),
            data.get('salary_max'),
            data.get('salary_currency', 'AUD'),
            data.get('search_summary', '')[:300],
            json.dumps(data.get('selling_points', []))[:500],
            data.get('video_url', ''),
            expires_at,
            data.get('skills', ''),
            employer_id,
        ),
    )
    db.commit()
    job_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

    try:
        from email_notifier import send_job_alert
        skills_raw = data.get('skills', '')
        keywords = skills_raw.split(',')[0].strip() if skills_raw else data.get('title', '')[:50]
        role_filter = ' OR '.join(f"role='{role}'" for role in SEEKER_ROLES)
        matching_users = db.execute(
            f'SELECT name, email FROM users WHERE ({role_filter}) AND email IS NOT NULL LIMIT 50'
        ).fetchall()
        if keywords and matching_users:
            sample_jobs = [dict(db.execute(
                'SELECT id, title, company, location, salary FROM jobs WHERE id=?', (job_id,)
            ).fetchone())]
            for user in matching_users:
                send_job_alert(user['email'], user['name'] or 'there', sample_jobs, keywords)
    except Exception as exc:
        print(f'[create_job] alert error: {exc}')

    return jsonify({'success': True, 'message': 'Job created', 'job_id': job_id}), 201


@jobs_bp.route('/api/jobs/<int:job_id>', methods=['PATCH'])
@require_auth
def update_job(job_id):
    data = request.json or {}
    if not data:
        return jsonify({'error': 'No update fields provided'}), 400
    allowed = [
        'title', 'description', 'location', 'salary', 'salary_min', 'salary_max',
        'salary_currency', 'category', 'work_type', 'work_arrangement',
        'is_active', 'expires_at', 'skills', 'selling_points', 'video_url',
    ]
    updates = {key: value for key, value in data.items() if key in allowed}
    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400

    db = get_db()
    existing = db.execute('SELECT id, employer_id FROM jobs WHERE id = ?', (job_id,)).fetchone()
    if not existing:
        return jsonify({'error': 'Job not found'}), 404
    if existing['employer_id'] and existing['employer_id'] != request.employer_id and request.user_role != 'admin':
        return jsonify({'error': 'Not authorized to update this job'}), 403

    set_clause = ', '.join(f'{key} = ?' for key in updates)
    db.execute(f'UPDATE jobs SET {set_clause} WHERE id = ?', list(updates.values()) + [job_id])
    db.commit()
    updated = db.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    return jsonify({'success': True, 'job': dict(updated)})


@jobs_bp.route('/api/jobs/<int:job_id>', methods=['DELETE'])
@require_auth
def delete_job(job_id):
    db = get_db()
    existing = db.execute('SELECT id, employer_id FROM jobs WHERE id = ?', (job_id,)).fetchone()
    if not existing:
        return jsonify({'error': 'Job not found'}), 404
    if existing['employer_id'] and existing['employer_id'] != request.employer_id and request.user_role != 'admin':
        return jsonify({'error': 'Not authorized to delete this job'}), 403
    db.execute('UPDATE jobs SET is_active = 0 WHERE id = ?', (job_id,))
    db.commit()
    return jsonify({'success': True, 'message': 'Job removed'})


@jobs_bp.route('/api/jobs/<int:job_id>/view', methods=['PATCH'])
def track_job_view(job_id):
    db = get_db()
    db.execute('UPDATE jobs SET view_count = view_count + 1 WHERE id = ?', (job_id,))
    db.commit()
    job = db.execute('SELECT view_count FROM jobs WHERE id = ?', (job_id,)).fetchone()
    return jsonify({'success': True, 'view_count': job['view_count'] if job else 0})


@jobs_bp.route('/api/companies', methods=['GET'])
def get_companies():
    db = get_db()
    companies = db.execute('SELECT * FROM companies ORDER BY name').fetchall()
    return jsonify([dict(company) for company in companies])


@jobs_bp.route('/api/skills', methods=['GET'])
def get_skills():
    db = get_db()
    skills = db.execute('SELECT * FROM skills_taxonomy ORDER BY category, demand_score DESC').fetchall()
    return jsonify([dict(skill) for skill in skills])


@jobs_bp.route('/api/search', methods=['GET'])
@limiter.limit('10 per minute')
def search_all():
    query = request.args.get('q', '').lower()
    if len(query) < 2:
        return jsonify({'error': 'Query too short'}), 400
    db = get_db()
    jobs = db.execute(
        'SELECT id, title, company, location FROM jobs WHERE is_active = 1 AND (title LIKE ? OR description LIKE ?)',
        (f'%{query}%', f'%{query}%'),
    ).fetchall()
    companies = db.execute(
        'SELECT id, name, industry FROM companies WHERE name LIKE ? OR industry LIKE ?',
        (f'%{query}%', f'%{query}%'),
    ).fetchall()
    return jsonify({
        'jobs': [dict(job) for job in jobs],
        'companies': [dict(company) for company in companies],
        'count': len(jobs) + len(companies),
    })


@jobs_bp.route('/api/trending', methods=['GET'])
def trending_jobs():
    db = get_db()
    categories = db.execute(
        'SELECT category, COUNT(*) as count FROM jobs WHERE is_active = 1 GROUP BY category ORDER BY count DESC LIMIT 10'
    ).fetchall()
    locations = db.execute(
        'SELECT location, COUNT(*) as count FROM jobs WHERE is_active = 1 GROUP BY location ORDER BY count DESC LIMIT 10'
    ).fetchall()
    return jsonify({
        'trending_categories': [dict(row) for row in categories],
        'trending_locations': [dict(row) for row in locations],
    })


@jobs_bp.route('/api/salary/predict', methods=['POST'])
def predict_salary():
    data = request.json or {}
    title = data.get('title', '')
    base = 80000
    title_lower = title.lower()
    if 'senior' in title_lower:
        base += 40000
    if 'junior' in title_lower:
        base -= 20000
    if 'lead' in title_lower:
        base += 30000
    return jsonify({'success': True, 'predicted': base, 'range': {'min': base * 0.85, 'max': base * 1.15}})
