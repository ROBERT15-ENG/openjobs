"""Employer dashboard routes."""

from auth_utils import require_auth
from constants import APPLICATION_STATUSES
from db import get_db
from flask import Blueprint, jsonify, request
from status import normalize_status

employer_bp = Blueprint('employer', __name__)


@employer_bp.route('/api/employer/dashboard', methods=['GET'])
@require_auth
def employer_dashboard():
    emp_id = request.employer_id
    db = get_db()
    my_jobs = db.execute(
        'SELECT * FROM jobs WHERE employer_id = ? AND is_active = 1 ORDER BY created_at DESC',
        (emp_id,),
    ).fetchall()
    job_ids = [job['id'] for job in my_jobs]

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
        'SELECT COALESCE(SUM(view_count), 0) FROM jobs WHERE employer_id = ?', (emp_id,)
    ).fetchone()[0]

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
    emp_id = request.employer_id
    status = request.args.get('status', 'all')
    db = get_db()
    job_ids = [
        row['id'] for row in db.execute(
            'SELECT id FROM jobs WHERE employer_id = ? AND is_active = 1', (emp_id,)
        ).fetchall()
    ]
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
