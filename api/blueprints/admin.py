"""Admin analytics routes."""

import csv
import io

from application_status import update_application_status
from auth_utils import require_role
from constants import APPLICATION_STATUSES, SEEKER_ROLES
from db import get_db
from deletion import delete_job_cascade, delete_user_cascade
from flask import Blueprint, Response, jsonify, request
from status import is_valid_status, normalize_status
from timeutil import iso_before
from validation import ValidationError, int_list

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/api/admin/stats', methods=['GET'])
@require_role('admin')
def admin_stats():
    db = get_db()
    total_jobs = db.execute('SELECT COUNT(*) FROM jobs WHERE is_active=1').fetchone()[0]
    total_apps = db.execute('SELECT COUNT(*) FROM applications').fetchone()[0]
    seeker_roles = ','.join(f"'{role}'" for role in SEEKER_ROLES)
    total_seekers = db.execute(
        f'SELECT COUNT(*) FROM users WHERE role IN ({seeker_roles})'
    ).fetchone()[0]
    total_employers = db.execute("SELECT COUNT(*) FROM users WHERE role='employer'").fetchone()[0]

    app_rows = db.execute('SELECT status, COUNT(*) as cnt FROM applications GROUP BY status').fetchall()
    apps_by_status = {row['status']: row['cnt'] for row in app_rows}

    thirty_days_ago = iso_before(days=30)
    apps_over_time = db.execute(
        'SELECT DATE(applied_at) as day, COUNT(*) as cnt FROM applications WHERE applied_at >= ? GROUP BY day ORDER BY day',
        (thirty_days_ago,),
    ).fetchall()
    jobs_over_time = db.execute(
        'SELECT DATE(created_at) as day, COUNT(*) as cnt FROM jobs WHERE created_at >= ? GROUP BY day ORDER BY day',
        (thirty_days_ago,),
    ).fetchall()
    top_employers = db.execute(
        """
        SELECT u.name, u.email, COUNT(j.id) as job_count
        FROM users u
        LEFT JOIN jobs j ON j.employer_id = u.id AND j.is_active=1
        WHERE u.role='employer'
        GROUP BY u.id ORDER BY job_count DESC LIMIT 10
        """
    ).fetchall()
    by_category = db.execute(
        'SELECT category, COUNT(*) as cnt FROM jobs WHERE is_active=1 GROUP BY category ORDER BY cnt DESC'
    ).fetchall()
    by_work_type = db.execute(
        'SELECT work_type, COUNT(*) as cnt FROM jobs WHERE is_active=1 GROUP BY work_type'
    ).fetchall()
    avg_salary = db.execute(
        'SELECT AVG((salary_min + salary_max) / 2) FROM jobs WHERE is_active=1 AND salary_min > 0'
    ).fetchone()[0] or 0
    total_views = db.execute('SELECT COALESCE(SUM(view_count), 0) FROM jobs').fetchone()[0]
    recent_apps = db.execute(
        """
        SELECT a.id, a.status, a.applied_at, j.title as job_title,
               u.name as seeker_name, u.email as seeker_email
        FROM applications a
        JOIN jobs j ON j.id = a.job_id
        JOIN users u ON u.id = a.user_id
        ORDER BY a.applied_at DESC LIMIT 10
        """
    ).fetchall()
    recent_signups = db.execute(
        'SELECT id, name, email, role, created_at FROM users ORDER BY created_at DESC LIMIT 10'
    ).fetchall()

    return jsonify({
        'summary': {
            'total_jobs': total_jobs,
            'total_applications': total_apps,
            'total_seekers': total_seekers,
            'total_employers': total_employers,
            'avg_salary': round(avg_salary, 0),
            'total_views': total_views,
        },
        'apps_by_status': apps_by_status,
        'apps_over_time': [dict(row) for row in apps_over_time],
        'jobs_over_time': [dict(row) for row in jobs_over_time],
        'top_employers': [dict(row) for row in top_employers],
        'by_category': [dict(row) for row in by_category],
        'by_work_type': [dict(row) for row in by_work_type],
        'recent_applications': [dict(row) for row in recent_apps],
        'recent_signups': [dict(row) for row in recent_signups],
    })


@admin_bp.route('/api/admin/users', methods=['GET'])
@require_role('admin')
def admin_users():
    db = get_db()
    users = db.execute(
        """
        SELECT id, name, email, role, skills, phone, company, created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT 200
        """
    ).fetchall()
    return jsonify({'users': [dict(row) for row in users]})


@admin_bp.route('/api/admin/export/applications', methods=['GET'])
@require_role('admin')
def export_applications_csv():
    """Download applications as CSV for reporting."""
    db = get_db()
    rows = db.execute(
        """
        SELECT a.id, a.status, a.applied_at, a.ats_score,
               u.name as applicant_name, u.email as applicant_email,
               j.title as job_title, j.company as job_company
        FROM applications a
        JOIN users u ON u.id = a.user_id
        JOIN jobs j ON j.id = a.job_id
        ORDER BY a.applied_at DESC
        LIMIT 5000
        """
    ).fetchall()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['id', 'status', 'applied_at', 'ats_score', 'applicant', 'email', 'job', 'company'])
    for row in rows:
        writer.writerow([
            row['id'], row['status'], row['applied_at'], row['ats_score'],
            row['applicant_name'], row['applicant_email'], row['job_title'], row['job_company'],
        ])
    return Response(
        buffer.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=openjobs-applications.csv'},
    )


@admin_bp.route('/api/admin/job-alerts/run', methods=['POST'])
@require_role('admin')
def run_job_alerts():
    """Manually trigger job-alert matching (same logic as scripts/match_job_alerts.py)."""
    from job_alert_matcher import run_job_alert_matching

    data = request.json or {}
    since_hours = int(data.get('since_hours', 24))
    dry_run = bool(data.get('dry_run', False))
    result = run_job_alert_matching(since_hours=since_hours, dry_run=dry_run)
    return jsonify({'success': True, **result})


@admin_bp.route('/api/admin/email/outbox', methods=['GET'])
@require_role('admin')
def email_outbox_status():
    db = get_db()
    rows = db.execute('SELECT status, COUNT(*) as cnt FROM email_outbox GROUP BY status').fetchall()
    failed = db.execute(
        'SELECT id, to_email, subject, attempts, last_error, created_at FROM email_outbox '
        "WHERE status = 'failed' ORDER BY id DESC LIMIT 20"
    ).fetchall()
    return jsonify({
        'counts': {row['status']: row['cnt'] for row in rows},
        'recent_failures': [dict(row) for row in failed],
    })


@admin_bp.route('/api/admin/email/drain', methods=['POST'])
@require_role('admin')
def email_outbox_drain():
    """Deliver pending outbox mail now (same as scripts/send_outbox.py)."""
    from email_notifier import drain_outbox, is_configured

    if not is_configured():
        return jsonify({'error': 'SMTP not configured'}), 503
    data = request.json or {}
    limit = max(1, min(500, int(data.get('limit', 100))))
    return jsonify({'success': True, **drain_outbox(limit=limit)})


@admin_bp.route('/api/admin/jobs/bulk', methods=['POST'])
@require_role('admin')
def bulk_jobs():
    data = request.json or {}
    try:
        ids = int_list(data.get('ids'), 'ids')
    except ValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    action = (data.get('action') or '').strip().lower()
    if action not in ('deactivate', 'delete', 'reactivate'):
        return jsonify({'error': 'action must be deactivate, reactivate, or delete'}), 400

    db = get_db()
    placeholders = ','.join('?' * len(ids))
    if action == 'deactivate':
        # Moderation lock: employers cannot re-enable via PATCH until an admin reactivates.
        db.execute(
            f"UPDATE jobs SET is_active = 0, moderation_status = 'removed' WHERE id IN ({placeholders})",
            ids,
        )
    elif action == 'reactivate':
        db.execute(
            f"UPDATE jobs SET is_active = 1, moderation_status = 'ok' WHERE id IN ({placeholders})",
            ids,
        )
    else:
        for job_id in ids:
            delete_job_cascade(db, job_id)
    db.commit()
    return jsonify({'success': True, 'updated': len(ids), 'action': action})


@admin_bp.route('/api/admin/applications/bulk', methods=['POST'])
@require_role('admin')
def bulk_applications():
    data = request.json or {}
    try:
        ids = int_list(data.get('ids'), 'ids')
    except ValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    status = normalize_status(data.get('status'))
    if not data.get('status') or not is_valid_status(status):
        return jsonify({'error': f'status must be one of: {list(APPLICATION_STATUSES)}'}), 400

    db = get_db()
    updated = 0
    for app_id in ids:
        ok, _, _ = update_application_status(
            db, app_id, status, send_email=True, actor_role='admin'
        )
        if ok:
            updated += 1
    return jsonify({'success': True, 'updated': updated})


@admin_bp.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@require_role('admin')
def delete_user(user_id):
    db = get_db()
    user = db.execute('SELECT id, role FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user['role'] == 'admin':
        return jsonify({'error': 'Cannot delete admin accounts'}), 403
    delete_user_cascade(db, user_id)
    db.commit()
    return jsonify({'success': True})
