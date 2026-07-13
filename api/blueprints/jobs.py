"""Job listing routes."""

import datetime
import json

from auth_utils import optional_auth, require_auth
from db import get_db
from extensions import limiter
from flask import Blueprint, jsonify, request
from geo_util import geocode_location, haversine_km
from job_util import enrich_job, geocode_job_location
from match_util import match_tier_label
from semantic_matcher import keyword_score
from org_util import employer_can_access_job
from seo_util import job_url_path

from skills_util import extract_skills_fast

jobs_bp = Blueprint('jobs', __name__)


def _user_match_context(db, user_id):
    user = db.execute(
        'SELECT skills, resume_text FROM users WHERE id = ?', (user_id,)
    ).fetchone()
    if not user:
        return '', ''
    resume = user['resume_text'] or ''
    skills = user['skills'] or ''
    if not skills and resume:
        skills = ','.join(extract_skills_fast(resume))
    return skills, resume


def _attach_match_scores(jobs, user_id, db, near_lat=None, near_lng=None):
    base = [enrich_job(j, near_lat, near_lng) for j in jobs]
    if not user_id:
        return base
    skills, resume = _user_match_context(db, user_id)
    match_text = resume or skills
    if not match_text:
        return base
    scored = []
    for row in base:
        score, matched, _ = keyword_score(row.get('skills', '') or '', match_text)
        if not score and skills:
            skill_list = [s.strip().lower() for s in skills.split(',') if s.strip()]
            job_skills = (row.get('skills') or '').lower()
            overlap = sum(1 for s in skill_list if s in job_skills)
            score = min(100, overlap * 25)
        row['score'] = score
        row['matched_skills'] = matched[:8]
        row['match_tier'] = match_tier_label(score)
        scored.append(row)
    return scored


@jobs_bp.route('/api/stats', methods=['GET'])
def public_stats():
    db = get_db()
    total_jobs = db.execute('SELECT COUNT(*) FROM jobs WHERE is_active = 1').fetchone()[0]
    total_companies = db.execute('SELECT COUNT(DISTINCT company) FROM jobs WHERE is_active = 1').fetchone()[0]
    today = datetime.datetime.now().date().isoformat()
    new_today = db.execute(
        "SELECT COUNT(*) FROM jobs WHERE is_active = 1 AND DATE(created_at) = ?",
        (today,),
    ).fetchone()[0]
    return jsonify({
        'total_jobs': total_jobs,
        'total_companies': total_companies,
        'new_today': new_today,
    })


@jobs_bp.route('/api/jobs', methods=['GET'])
@optional_auth
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

    visa = request.args.get('visa', '').lower()
    if visa in ('1', 'true', 'yes'):
        visa_clause = (
            "(LOWER(description) LIKE '%visa%' OR LOWER(description) LIKE '%sponsorship%' "
            "OR LOWER(skills) LIKE '%visa%' OR LOWER(search_summary) LIKE '%sponsorship%' "
            "OR LOWER(selling_points) LIKE '%visa%' OR LOWER(selling_points) LIKE '%sponsorship%')"
        )
        where.append(visa_clause)

    where_clause = ' AND '.join(where)

    sort = request.args.get('sort', 'newest')
    order = 'COALESCE(posted_at, created_at) DESC'
    if sort == 'salary_high':
        order = 'COALESCE(salary_max, salary_min, 0) DESC, COALESCE(posted_at, created_at) DESC'
    elif sort == 'salary_low':
        order = 'COALESCE(salary_min, salary_max, 999999999) ASC, COALESCE(posted_at, created_at) DESC'
    elif sort == 'featured':
        order = 'COALESCE(is_featured, 0) DESC, COALESCE(posted_at, created_at) DESC'

    near = request.args.get('near', '').strip() or location
    radius_km = request.args.get('radius_km', type=float)
    near_lat, near_lng = geocode_location(near) if near else (None, None)
    use_radius = near_lat is not None and radius_km and radius_km > 0

    fetch_limit = 500 if use_radius else limit
    fetch_offset = 0 if use_radius else offset
    jobs = db.execute(
        f'SELECT * FROM jobs WHERE {where_clause} ORDER BY {order} LIMIT ? OFFSET ?',
        params + [fetch_limit, fetch_offset],
    ).fetchall()

    if use_radius:
        filtered = []
        for job in jobs:
            jlat = job['latitude']
            jlng = job['longitude']
            if jlat is None or jlng is None:
                lat, lng = geocode_job_location(job['location'] or '')
                jlat, jlng = lat, lng
            if jlat is None:
                continue
            if haversine_km(near_lat, near_lng, jlat, jlng) <= radius_km:
                filtered.append(job)
        total = len(filtered)
        jobs = filtered[offset:offset + limit]
    else:
        total = db.execute(f'SELECT COUNT(*) FROM jobs WHERE {where_clause}', params).fetchone()[0]

    job_list = _attach_match_scores(jobs, getattr(request, 'user_id', None), db, near_lat, near_lng)
    if use_radius:
        job_list.sort(key=lambda j: j.get('distance_km') if j.get('distance_km') is not None else 99999)
    return jsonify({
        'jobs': job_list,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'pages': (total + limit - 1) // limit if limit else 0,
        },
    })


@jobs_bp.route('/api/jobs/<int:job_id>', methods=['GET'])
@optional_auth
def get_job(job_id):
    db = get_db()
    job = db.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    if not job:
        return jsonify({'error': 'Not found'}), 404
    row = enrich_job(job)
    if getattr(request, 'user_id', None):
        scored = _attach_match_scores([job], request.user_id, db)
        if scored:
            row.update({k: scored[0][k] for k in ('score', 'matched_skills', 'match_tier') if k in scored[0]})
    return jsonify(row)


@jobs_bp.route('/api/jobs', methods=['POST'])
@require_auth
def create_job():
    data = request.json or {}
    required = ['title', 'company', 'location', 'description']
    missing = [field for field in required if not data.get(field)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    db = get_db()
    now = datetime.datetime.now().isoformat()
    expires_at = data.get('expires_at') or (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
    employer_id = getattr(request, 'employer_id', None)
    lat, lng = geocode_job_location(data.get('location', ''))
    db.execute(
        """INSERT INTO jobs (
            title, company, location, description, salary, category, is_active, created_at, posted_at,
            work_type, work_arrangement, salary_min, salary_max, salary_currency,
            search_summary, selling_points, video_url, expires_at, skills, employer_id,
            latitude, longitude
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get('title'),
            data.get('company'),
            data.get('location'),
            data.get('description'),
            data.get('salary', 'Competitive'),
            data.get('category', 'General'),
            1,
            now,
            now,
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
            lat,
            lng,
        ),
    )
    db.commit()
    job_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

    try:
        from job_alert_matcher import notify_alerts_for_job
        notify_alerts_for_job(job_id)
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
    if not employer_can_access_job(db, request.user_id, request.user_role, dict(existing)):
        return jsonify({'error': 'Not authorized to update this job'}), 403

    if 'location' in updates:
        lat, lng = geocode_job_location(updates['location'])
        updates['latitude'] = lat
        updates['longitude'] = lng

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
    if not employer_can_access_job(db, request.user_id, request.user_role, dict(existing)):
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


@jobs_bp.route('/api/companies/directory', methods=['GET'])
def companies_directory():
    """Aggregate hiring companies from active job listings."""
    db = get_db()
    rows = db.execute(
        """
        SELECT company as name,
               COUNT(*) as job_count,
               MIN(salary_min) as salary_min,
               MAX(salary_max) as salary_max,
               GROUP_CONCAT(DISTINCT location) as locations,
               GROUP_CONCAT(DISTINCT category) as categories
        FROM jobs
        WHERE is_active = 1 AND company IS NOT NULL AND company != ''
        GROUP BY company
        ORDER BY job_count DESC, company ASC
        LIMIT 200
        """
    ).fetchall()
    return jsonify({'companies': [dict(row) for row in rows]})


@jobs_bp.route('/api/salary/insights', methods=['GET'])
def salary_insights():
    db = get_db()
    by_category = db.execute(
        """
        SELECT category,
               COUNT(*) as job_count,
               ROUND(AVG((salary_min + salary_max) / 2.0)) as avg_salary,
               MIN(salary_min) as min_salary,
               MAX(salary_max) as max_salary
        FROM jobs
        WHERE is_active = 1 AND salary_min > 0
        GROUP BY category
        ORDER BY avg_salary DESC
        """
    ).fetchall()
    by_location = db.execute(
        """
        SELECT location,
               COUNT(*) as job_count,
               ROUND(AVG((salary_min + salary_max) / 2.0)) as avg_salary
        FROM jobs
        WHERE is_active = 1 AND salary_min > 0 AND location IS NOT NULL
        GROUP BY location
        ORDER BY job_count DESC
        LIMIT 15
        """
    ).fetchall()
    overall = db.execute(
        """
        SELECT ROUND(AVG((salary_min + salary_max) / 2.0)) as avg_salary,
               MIN(salary_min) as min_salary,
               MAX(salary_max) as max_salary,
               COUNT(*) as job_count
        FROM jobs WHERE is_active = 1 AND salary_min > 0
        """
    ).fetchone()
    return jsonify({
        'overall': dict(overall) if overall else {},
        'by_category': [dict(row) for row in by_category],
        'by_location': [dict(row) for row in by_location],
    })


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
