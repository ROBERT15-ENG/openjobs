"""Application and kanban routes."""

import datetime
import os
import smtplib

from auth_utils import require_auth
from constants import APPLICATION_STATUSES, KANBAN_STAGES
from db import get_db
from extensions import limiter
from flask import Blueprint, jsonify, request
from status import is_valid_kanban_stage, is_valid_status, kanban_stage_for, normalize_status

applications_bp = Blueprint('applications', __name__)


@applications_bp.route('/api/applications', methods=['GET'])
@require_auth
def get_applications():
    db = get_db()
    if request.user_role == 'admin':
        apps = db.execute('SELECT * FROM applications ORDER BY applied_at DESC').fetchall()
    elif request.user_role == 'employer':
        job_ids = [row['id'] for row in db.execute(
            'SELECT id FROM jobs WHERE employer_id = ?', (request.employer_id,)
        ).fetchall()]
        if not job_ids:
            return jsonify([])
        placeholders = ','.join('?' * len(job_ids))
        apps = db.execute(
            f'SELECT * FROM applications WHERE job_id IN ({placeholders}) ORDER BY applied_at DESC',
            job_ids,
        ).fetchall()
    else:
        apps = db.execute(
            'SELECT * FROM applications WHERE user_id = ? ORDER BY applied_at DESC',
            (request.user_id,),
        ).fetchall()
    return jsonify([dict(app) for app in apps])


@applications_bp.route('/api/applications', methods=['POST'])
@require_auth
@limiter.limit('30 per hour')
def apply_job():
    data = request.json or {}
    db = get_db()
    job_id = data.get('job_id')
    resume_text = data.get('resume_text', '')

    job = db.execute('SELECT title, company, employer_id FROM jobs WHERE id = ?', (job_id,)).fetchone()
    applicant = db.execute('SELECT name, email FROM users WHERE id = ?', (request.user_id,)).fetchone()
    employer = None
    if job and job['employer_id']:
        employer = db.execute('SELECT name, email FROM users WHERE id = ?', (job['employer_id'],)).fetchone()

    db.execute(
        'INSERT INTO applications (job_id, user_id, status, applied_at, resume_text) VALUES (?, ?, ?, ?, ?)',
        (job_id, request.user_id, 'applied', datetime.datetime.now().isoformat(), resume_text[:50000]),
    )
    db.commit()
    app_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

    try:
        from email_notifier import send_application_confirm
        if applicant and applicant['email']:
            send_application_confirm(
                applicant['email'],
                job['title'] if job else 'the role',
                job['company'] if job else 'the company',
            )
    except Exception as exc:
        print(f'[apply_job] applicant email error: {exc}')

    try:
        if employer and employer['email'] and os.environ.get('SMTP_HOST'):
            from_email = os.environ.get('FROM_EMAIL', 'noreply@openjobs.com.au')
            subject = f"New Application: {job['title'] if job else 'a job'}"
            body = (
                f"You have a new applicant for {job['title']} at {job['company']}. "
                'Log in to your OpenJobs dashboard to review their application.'
            )
            msg = 'Subject: ' + subject + '\n\n' + body
            with smtplib.SMTP(os.environ['SMTP_HOST'], int(os.environ.get('SMTP_PORT', 587))) as smtp:
                smtp.starttls()
                smtp.login(os.environ['SMTP_USER'], os.environ['SMTP_PASS'])
                smtp.sendmail(from_email, employer['email'], msg)
    except Exception as exc:
        print(f'[apply_job] employer email error: {exc}')

    return jsonify({'success': True, 'message': 'Applied', 'application_id': app_id}), 201


@applications_bp.route('/api/applications/<int:app_id>', methods=['PATCH'])
@require_auth
def update_application(app_id):
    data = request.json or {}
    new_status = normalize_status(data.get('status'))
    if data.get('status') and not is_valid_status(new_status):
        return jsonify({'error': f'Invalid status. Must be one of: {list(APPLICATION_STATUSES)}'}), 400

    db = get_db()
    app_row = db.execute(
        """
        SELECT a.id, a.user_id, j.employer_id
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.id = ?
        """,
        (app_id,),
    ).fetchone()
    if not app_row:
        return jsonify({'error': 'Application not found'}), 404
    allowed = (
        request.user_role == 'admin'
        or app_row['employer_id'] == request.employer_id
        or app_row['user_id'] == request.user_id
    )
    if not allowed:
        return jsonify({'error': 'Not authorized'}), 403

    db.execute(
        'UPDATE applications SET status = ?, updated_at = ? WHERE id = ?',
        (new_status, datetime.datetime.now().isoformat(), app_id),
    )
    db.commit()
    updated = db.execute('SELECT * FROM applications WHERE id = ?', (app_id,)).fetchone()
    return jsonify({'success': True, 'application': dict(updated)})


@applications_bp.route('/api/applications/<int:app_id>', methods=['DELETE'])
@require_auth
def delete_application(app_id):
    db = get_db()
    app_row = db.execute('SELECT user_id FROM applications WHERE id = ?', (app_id,)).fetchone()
    if not app_row:
        return jsonify({'error': 'Application not found'}), 404
    if request.user_role != 'admin' and app_row['user_id'] != request.user_id:
        return jsonify({'error': 'Not authorized'}), 403
    db.execute('DELETE FROM applications WHERE id = ?', (app_id,))
    db.commit()
    return jsonify({'success': True})


@applications_bp.route('/api/kanban/<int:job_id>', methods=['GET'])
@require_auth
def get_kanban(job_id):
    db = get_db()
    job = db.execute('SELECT employer_id FROM jobs WHERE id=?', (job_id,)).fetchone()
    if not job or (job['employer_id'] != request.employer_id and request.user_role != 'admin'):
        return jsonify({'error': 'Not found'}), 404

    apps = db.execute(
        """
        SELECT a.id, a.status, a.applied_at, a.ats_score, a.cover_letter, a.resume_text,
               u.name as applicant_name, u.email as applicant_email
        FROM applications a
        JOIN users u ON a.user_id = u.id
        WHERE a.job_id = ?
        ORDER BY a.applied_at DESC
        """,
        (job_id,),
    ).fetchall()

    board = {stage: [] for stage in KANBAN_STAGES}
    for app in apps:
        stage = kanban_stage_for(app['status'])
        row = dict(app)
        row['status'] = stage
        board[stage].append(row)
    return jsonify({'success': True, 'board': board})


@applications_bp.route('/api/kanban/<int:job_id>/move', methods=['POST'])
@require_auth
def move_kanban_card(job_id):
    db = get_db()
    job = db.execute('SELECT employer_id FROM jobs WHERE id=?', (job_id,)).fetchone()
    if not job or (job['employer_id'] != request.employer_id and request.user_role != 'admin'):
        return jsonify({'error': 'Not found'}), 404

    data = request.json or {}
    app_id = data.get('application_id')
    new_status = normalize_status(data.get('stage'))
    if not is_valid_kanban_stage(new_status):
        return jsonify({'error': f'Invalid stage. Must be one of: {list(KANBAN_STAGES)}'}), 400

    db.execute(
        'UPDATE applications SET status=?, updated_at=? WHERE id=? AND job_id=?',
        (new_status, datetime.datetime.now().isoformat(), app_id, job_id),
    )
    db.commit()
    return jsonify({'success': True, 'status': new_status})
