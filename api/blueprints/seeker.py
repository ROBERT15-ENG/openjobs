"""Seeker dashboard and profile routes."""

from auth_utils import require_auth
from db import get_db
from flask import Blueprint, jsonify, request
from semantic_matcher import rank_jobs_for_resume
from skills_util import extract_skills_fast
from timeutil import utcnow_iso
from validation import Bool, Int, IsoDate, Str, ValidationError, validate_payload

seeker_bp = Blueprint('seeker', __name__)

PROFILE_FIELDS = {
    'name': Str(max_len=120, min_len=1, nullable=False),
    'skills': Str(max_len=2000),
    'phone': Str(max_len=40),
    'preferred_location': Str(max_len=160),
    'experience': Str(max_len=10000),
    'company': Str(max_len=160),
    'resume_text': Str(max_len=50000),
    'salutation': Str(max_len=20),
    'address': Str(max_len=300),
    'country': Str(max_len=80),
    'county': Str(max_len=80),
    'dob': IsoDate(max_len=10),
    'nationality': Str(max_len=80),
    'visa_status': Str(max_len=80),
    'headline': Str(max_len=160),
    'bio': Str(max_len=4000),
    'desired_role': Str(max_len=120),
    'expected_salary': Int(min=0, max=100_000_000),
    'pref_work_type': Str(max_len=20, choices=('full_time', 'part_time', 'contract', 'internship'), lower=True),
    'pref_remote': Str(max_len=20, choices=('remote', 'hybrid', 'onsite'), lower=True),
}
PROFILE_COLUMNS = (
    'id, name, email, role, skills, phone, preferred_location, experience, resume_text, '
    'salutation, address, country, county, dob, nationality, visa_status, kyc_status, '
    'headline, bio, desired_role, expected_salary, pref_work_type, pref_remote, created_at'
)
KYC_FIELDS = {
    **{k: PROFILE_FIELDS[k] for k in (
        'name', 'salutation', 'phone', 'address', 'country', 'county', 'dob', 'nationality', 'visa_status',
    )},
    'kyc_doc_type': Str(max_len=40),
    'kyc_doc_number': Str(max_len=64),
}
ALERT_FIELDS = {
    'keyword': Str(max_len=200, min_len=1, nullable=False),
    'location': Str(max_len=160),
    'remote_only': Bool(),
    'salary_min': Int(min=0, max=100_000_000),
    'active': Bool(),
}


@seeker_bp.route('/api/dashboard/seeker', methods=['GET'])
@require_auth
def seeker_dashboard():
    db = get_db()
    user_id = request.user_id
    total_jobs = db.execute('SELECT COUNT(*) FROM jobs WHERE is_active = 1').fetchone()[0]
    total_applications = db.execute(
        'SELECT COUNT(*) FROM applications WHERE user_id = ?', (user_id,)
    ).fetchone()[0]
    applied_apps = db.execute(
        "SELECT COUNT(*) FROM applications WHERE user_id = ? AND status IN ('applied', 'pending')",
        (user_id,),
    ).fetchone()[0]
    interview_apps = db.execute(
        "SELECT COUNT(*) FROM applications WHERE user_id = ? AND status = 'interview'",
        (user_id,),
    ).fetchone()[0]
    recent_apps = db.execute(
        """
        SELECT a.*, j.title, j.company, j.location, j.salary_min, j.salary_max
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.user_id = ?
        ORDER BY a.applied_at DESC LIMIT 10
        """,
        (user_id,),
    ).fetchall()
    saved_count = db.execute(
        'SELECT COUNT(*) FROM saved_jobs WHERE user_id = ?', (user_id,)
    ).fetchone()[0]

    user_row = db.execute('SELECT skills, resume_text FROM users WHERE id = ?', (user_id,)).fetchone()
    user_skills = user_row['skills'] or '' if user_row else ''
    user_resume = user_row['resume_text'] if user_row else ''
    if not user_skills and user_resume:
        user_skills = ','.join(extract_skills_fast(user_resume))
    skill_list = [skill.strip().lower() for skill in user_skills.split(',') if skill.strip()]

    if skill_list:
        all_jobs = db.execute(
            """
            SELECT id, title, company, location, salary_min, salary_max, category, skills, description
            FROM jobs WHERE is_active = 1 ORDER BY posted_at DESC LIMIT 50
            """
        ).fetchall()
        if user_resume:
            rec_jobs = rank_jobs_for_resume([dict(job) for job in all_jobs], user_resume)[:4]
        else:
            scored = []
            for job in all_jobs:
                job_skills = (job['skills'] or '').lower()
                score = sum(1 for skill in skill_list if skill in job_skills)
                if score > 0:
                    job_dict = dict(job)
                    job_dict['match_score'] = score
                    scored.append((score, job_dict))
            scored.sort(key=lambda item: -item[0])
            rec_jobs = [job for _, job in scored[:4]]
    else:
        raw = db.execute(
            """
            SELECT id, title, company, location, salary_min, salary_max, category, skills
            FROM jobs WHERE is_active = 1 ORDER BY posted_at DESC LIMIT 4
            """
        ).fetchall()
        rec_jobs = [dict(job) for job in raw]
        for job in rec_jobs:
            job['match_score'] = 0

    return jsonify({
        'stats': {
            'total_jobs': total_jobs,
            'total_applications': total_applications,
            'applied': applied_apps,
            'pending': applied_apps,
            'interviews': interview_apps,
            'saved': saved_count,
        },
        'recent_applications': [dict(app) for app in recent_apps],
        'recommended': [dict(job) for job in rec_jobs],
    })


@seeker_bp.route('/api/recommendations', methods=['GET'])
@require_auth
def recommendations():
    db = get_db()
    user = db.execute(
        'SELECT skills, resume_text FROM users WHERE id = ?', (request.user_id,)
    ).fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    search_skills = user['skills'] or ''
    if not search_skills and user['resume_text']:
        search_skills = ','.join(extract_skills_fast(user['resume_text']))
    skill_list = [skill.strip() for skill in search_skills.split(',') if skill.strip()]

    if skill_list:
        params = {f's{i}': f'%{skill}%' for i, skill in enumerate(skill_list)}
        skill_like = ' OR '.join([f'skills LIKE :s{i}' for i in range(len(skill_list))])
        where_clause = f'({skill_like}) AND is_active = 1'
        case_clause = f"CASE WHEN skills LIKE :exact THEN 100 WHEN {skill_like} THEN 50 ELSE 0 END"
        params['exact'] = f'%{search_skills}%'
    else:
        where_clause = 'is_active = 1'
        case_clause = '0'
        params = {}

    sql = (
        f'SELECT *, {case_clause} as match_score FROM jobs WHERE {where_clause} '
        'ORDER BY match_score DESC, posted_at DESC LIMIT 20'
    )
    jobs = db.execute(sql, params).fetchall()
    return jsonify({
        'recommendations': [dict(job) for job in jobs],
        'skills_used': search_skills,
        'resume_enhanced': bool(user['resume_text'] and not user['skills']),
    })


@seeker_bp.route('/api/saved_jobs', methods=['GET'])
@require_auth
def get_saved_jobs():
    db = get_db()
    saved = db.execute(
        """
        SELECT j.*, sj.saved_at FROM jobs j
        JOIN saved_jobs sj ON j.id = sj.job_id
        WHERE sj.user_id = ? ORDER BY sj.saved_at DESC
        """,
        (request.user_id,),
    ).fetchall()
    return jsonify([dict(row) for row in saved])


@seeker_bp.route('/api/saved_jobs', methods=['POST'])
@require_auth
def save_job():
    data = request.json or {}
    try:
        job_id = Int(min=1, required=True)('job_id', data.get('job_id'))
    except ValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    db = get_db()
    if not db.execute('SELECT 1 FROM jobs WHERE id = ?', (job_id,)).fetchone():
        return jsonify({'error': 'Job not found'}), 404
    db.execute(
        'INSERT OR IGNORE INTO saved_jobs (user_id, job_id, saved_at) VALUES (?, ?, ?)',
        (request.user_id, job_id, utcnow_iso()),
    )
    db.commit()
    return jsonify({'success': True})


@seeker_bp.route('/api/saved_jobs', methods=['DELETE'])
@require_auth
def unsave_job():
    data = request.json or {}
    db = get_db()
    db.execute(
        'DELETE FROM saved_jobs WHERE user_id = ? AND job_id = ?',
        (request.user_id, data.get('job_id')),
    )
    db.commit()
    return jsonify({'success': True})


@seeker_bp.route('/api/user/profile', methods=['GET'])
@require_auth
def get_user_profile():
    db = get_db()
    user = db.execute(
        f'SELECT {PROFILE_COLUMNS} FROM users WHERE id = ?',
        (request.user_id,),
    ).fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(dict(user))


@seeker_bp.route('/api/user/profile', methods=['PATCH'])
@require_auth
def update_user_profile():
    try:
        updates = validate_payload(request.json, PROFILE_FIELDS, partial=True)
    except ValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    if not updates:
        return jsonify({'error': f'No valid fields. Allowed: {list(PROFILE_FIELDS)}'}), 400

    db = get_db()
    set_clause = ', '.join(f'{key} = ?' for key in updates)
    db.execute(
        f'UPDATE users SET {set_clause} WHERE id = ?',
        list(updates.values()) + [request.user_id],
    )
    db.commit()
    user = db.execute(
        f'SELECT {PROFILE_COLUMNS} FROM users WHERE id = ?',
        (request.user_id,),
    ).fetchone()
    return jsonify({'success': True, 'user': dict(user)})


@seeker_bp.route('/api/kyc/status', methods=['GET'])
@require_auth
def kyc_status():
    db = get_db()
    user = db.execute(
        """
        SELECT kyc_status, kyc_doc_type, kyc_doc_number, dob, nationality, country, county,
               salutation, phone, email, address, visa_status, name
        FROM users WHERE id = ?
        """,
        (request.user_id,),
    ).fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    row = dict(user)
    return jsonify({
        'success': True,
        'kyc_status': row.get('kyc_status') or 'none',
        'profile': row,
    })


@seeker_bp.route('/api/kyc/profile', methods=['PATCH'])
@require_auth
def update_kyc_profile():
    """Update KYC personal fields (ekip parity)."""
    try:
        updates = validate_payload(request.json, KYC_FIELDS, partial=True)
    except ValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    if not updates:
        return jsonify({'error': f'No valid fields. Allowed: {list(KYC_FIELDS)}'}), 400

    if any(updates.get(k) for k in ('dob', 'nationality', 'country', 'address')):
        updates.setdefault('kyc_status', 'submitted')

    db = get_db()
    set_clause = ', '.join(f'{key} = ?' for key in updates)
    db.execute(
        f'UPDATE users SET {set_clause} WHERE id = ?',
        list(updates.values()) + [request.user_id],
    )
    db.commit()
    return kyc_status()


@seeker_bp.route('/api/job_alerts', methods=['GET'])
@require_auth
def list_job_alerts():
    db = get_db()
    alerts = db.execute(
        """
        SELECT id, keyword, location, remote_only, salary_min, active
        FROM job_alerts WHERE user_id = ? ORDER BY id DESC
        """,
        (request.user_id,),
    ).fetchall()
    return jsonify({'alerts': [dict(row) for row in alerts]})


@seeker_bp.route('/api/job_alerts', methods=['POST'])
@require_auth
def create_job_alert():
    try:
        data = validate_payload(request.json, {**ALERT_FIELDS, 'keyword': Str(max_len=200, required=True)})
    except ValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    db = get_db()
    cur = db.execute(
        """
        INSERT INTO job_alerts (user_id, keyword, location, remote_only, salary_min, active)
        VALUES (?, ?, ?, ?, ?, 1)
        """,
        (
            request.user_id,
            data['keyword'],
            data.get('location') or None,
            data.get('remote_only') or 0,
            data.get('salary_min') or None,
        ),
    )
    db.commit()
    alert_id = cur.lastrowid
    alert = db.execute('SELECT * FROM job_alerts WHERE id = ?', (alert_id,)).fetchone()
    return jsonify({'success': True, 'alert': dict(alert)}), 201


@seeker_bp.route('/api/job_alerts/<int:alert_id>', methods=['PATCH'])
@require_auth
def update_job_alert(alert_id):
    data = request.json or {}
    db = get_db()
    existing = db.execute(
        'SELECT id FROM job_alerts WHERE id = ? AND user_id = ?',
        (alert_id, request.user_id),
    ).fetchone()
    if not existing:
        return jsonify({'error': 'Alert not found'}), 404
    try:
        updates = validate_payload(data, ALERT_FIELDS, partial=True)
    except ValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400
    set_clause = ', '.join(f'{k} = ?' for k in updates)
    db.execute(
        f'UPDATE job_alerts SET {set_clause} WHERE id = ? AND user_id = ?',
        list(updates.values()) + [alert_id, request.user_id],
    )
    db.commit()
    alert = db.execute('SELECT * FROM job_alerts WHERE id = ?', (alert_id,)).fetchone()
    return jsonify({'success': True, 'alert': dict(alert)})


@seeker_bp.route('/api/job_alerts/<int:alert_id>', methods=['DELETE'])
@require_auth
def delete_job_alert(alert_id):
    db = get_db()
    db.execute(
        'DELETE FROM job_alerts WHERE id = ? AND user_id = ?',
        (alert_id, request.user_id),
    )
    db.commit()
    return jsonify({'success': True})
