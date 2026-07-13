"""Employer dashboard routes."""

from auth_utils import require_auth
from constants import APPLICATION_STATUSES
from db import get_db
from flask import Blueprint, jsonify, request
from org_util import get_employer_job_ids
from status import normalize_status

employer_bp = Blueprint('employer', __name__)


@employer_bp.route('/api/employer/dashboard', methods=['GET'])
@require_auth
def employer_dashboard():
    emp_id = request.user_id
    db = get_db()
    job_ids = get_employer_job_ids(db, emp_id)
    if job_ids:
        placeholders = ','.join('?' * len(job_ids))
        my_jobs = db.execute(
            f'SELECT * FROM jobs WHERE id IN ({placeholders}) AND is_active = 1 ORDER BY created_at DESC',
            job_ids,
        ).fetchall()
    else:
        my_jobs = []

    if job_ids:
        placeholders = ','.join('?' * len(job_ids))
        total_apps = db.execute(
            f'SELECT COUNT(*) FROM applications WHERE job_id IN ({placeholders})', job_ids
        ).fetchone()[0]
        applied_apps = db.execute(
            f"SELECT COUNT(*) FROM applications WHERE job_id IN ({placeholders}) AND status IN ('applied', 'pending')",
            job_ids,
        ).fetchone()[0]
        interviewing = db.execute(
            f"SELECT COUNT(*) FROM applications WHERE job_id IN ({placeholders}) AND status = 'interview'",
            job_ids,
        ).fetchone()[0]
        recent_apps = db.execute(
            f"""
            SELECT a.id, a.user_id, a.job_id, a.status, a.applied_at,
                   a.cover_letter, a.cv_link, j.title as job_title, j.company
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            WHERE a.job_id IN ({placeholders})
            ORDER BY a.applied_at DESC LIMIT 10
            """,
            job_ids,
        ).fetchall()
    else:
        total_apps = applied_apps = interviewing = 0
        recent_apps = []

    total_views = db.execute(
        f'SELECT COALESCE(SUM(view_count), 0) FROM jobs WHERE id IN ({placeholders})',
        job_ids,
    ).fetchone()[0] if job_ids else 0

    return jsonify({
        'stats': {
            'active_jobs': len(my_jobs),
            'total_applicants': total_apps,
            'applied': applied_apps,
            'pending': applied_apps,
            'interviewing': interviewing,
            'job_views': total_views,
        },
        'my_jobs': [dict(job) for job in my_jobs],
        'recent_applications': [dict(app) for app in recent_apps],
    })


@employer_bp.route('/api/employer/applications', methods=['GET'])
@require_auth
def employer_applications():
    db = get_db()
    status = request.args.get('status', 'all')
    job_ids = get_employer_job_ids(db, request.user_id)
    if not job_ids:
        return jsonify({'applications': []})

    placeholders = ','.join('?' * len(job_ids))
    query = f"""
        SELECT a.*, j.title as job_title, j.company, u.name as applicant_name, u.email as applicant_email
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        LEFT JOIN users u ON a.user_id = u.id
        WHERE a.job_id IN ({placeholders})
    """
    params = list(job_ids)
    if status != 'all':
        normalized = normalize_status(status)
        if normalized not in APPLICATION_STATUSES and normalized not in ('pending', 'reviewing'):
            return jsonify({'error': 'Invalid status filter'}), 400
        if normalized == 'applied':
            query += " AND a.status IN ('applied', 'pending')"
        elif normalized == 'screening':
            query += " AND a.status IN ('screening', 'reviewing')"
        else:
            query += ' AND a.status = ?'
            params.append(normalized)
    query += ' ORDER BY a.applied_at DESC'
    apps = db.execute(query, params).fetchall()
    return jsonify({'applications': [dict(app) for app in apps]})


@employer_bp.route('/api/employer/applications/bulk-status', methods=['POST'])
@require_auth
def employer_bulk_status():
    if request.user_role != 'employer':
        return jsonify({'error': 'Employer access required'}), 403
    data = request.json or {}
    ids = data.get('ids') or []
    status = (data.get('status') or '').strip().lower()
    if not ids:
        return jsonify({'error': 'ids array is required'}), 400
    if not status:
        return jsonify({'error': 'status is required'}), 400

    db = get_db()
    job_ids = set(get_employer_job_ids(db, request.user_id))
    updated = 0
    for app_id in ids:
        app_row = db.execute('SELECT job_id FROM applications WHERE id = ?', (int(app_id),)).fetchone()
        if not app_row or app_row['job_id'] not in job_ids:
            continue
        ok, _, _ = update_application_status(
            db, int(app_id), status, send_email=True, actor_role='employer'
        )
        if ok:
            updated += 1
    return jsonify({'success': True, 'updated': updated})
