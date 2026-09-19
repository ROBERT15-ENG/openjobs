"""Job report / flag routes."""

from auth_utils import optional_auth, require_role
from db import get_db
from extensions import limiter
from flask import Blueprint, jsonify, request
from timeutil import utcnow_iso

reports_bp = Blueprint('reports', __name__)

REPORT_REASONS = ('spam', 'misleading', 'discrimination', 'expired', 'other')


@reports_bp.route('/api/jobs/<int:job_id>/report', methods=['POST'])
@optional_auth
@limiter.limit('10 per hour')
def report_job(job_id):
    data = request.json or {}
    reason = (data.get('reason') or '').strip().lower()
    details = (data.get('details') or '').strip()[:2000]
    if reason not in REPORT_REASONS:
        return jsonify({'error': f'reason must be one of: {list(REPORT_REASONS)}'}), 400

    db = get_db()
    job = db.execute('SELECT id FROM jobs WHERE id = ? AND is_active = 1', (job_id,)).fetchone()
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    reporter_id = getattr(request, 'user_id', None)
    now = utcnow_iso()
    db.execute(
        """INSERT INTO job_reports (job_id, reporter_id, reason, details, status, created_at)
           VALUES (?, ?, ?, ?, 'open', ?)""",
        (job_id, reporter_id, reason, details, now),
    )
    db.commit()
    return jsonify({'success': True, 'message': 'Report submitted. Our team will review it.'}), 201


@reports_bp.route('/api/admin/reports', methods=['GET'])
@require_role('admin')
def list_reports():
    status = request.args.get('status', 'open')
    db = get_db()
    query = """
        SELECT r.*, j.title as job_title, j.company as job_company,
               u.email as reporter_email
        FROM job_reports r
        JOIN jobs j ON j.id = r.job_id
        LEFT JOIN users u ON u.id = r.reporter_id
    """
    params = []
    if status != 'all':
        query += ' WHERE r.status = ?'
        params.append(status)
    query += ' ORDER BY r.created_at DESC LIMIT 200'
    rows = db.execute(query, params).fetchall()
    return jsonify({'reports': [dict(row) for row in rows]})


@reports_bp.route('/api/admin/reports/<int:report_id>', methods=['PATCH'])
@require_role('admin')
def resolve_report(report_id):
    data = request.json or {}
    new_status = (data.get('status') or 'resolved').strip().lower()
    if new_status not in ('open', 'resolved', 'dismissed'):
        return jsonify({'error': 'Invalid status'}), 400

    db = get_db()
    row = db.execute('SELECT id, job_id FROM job_reports WHERE id = ?', (report_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Report not found'}), 404

    now = utcnow_iso()
    db.execute(
        'UPDATE job_reports SET status = ?, resolved_at = ? WHERE id = ?',
        (new_status, now, report_id),
    )
    if data.get('deactivate_job'):
        db.execute(
            "UPDATE jobs SET is_active = 0, moderation_status = 'removed' WHERE id = ?", (row['job_id'],)
        )
    db.commit()
    return jsonify({'success': True, 'status': new_status})
