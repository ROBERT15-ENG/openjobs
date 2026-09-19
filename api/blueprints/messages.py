"""Employer–seeker messaging (application-scoped threads)."""

from auth_utils import require_auth
from db import get_db
from extensions import limiter
from flask import Blueprint, jsonify, request
from org_util import employer_can_access_job, get_team_member_user_ids
from timeutil import utcnow_iso

messages_bp = Blueprint('messages', __name__)


def _conversation_access(db, conversation_id, user_id, user_role):
    conv = db.execute(
        'SELECT * FROM conversations WHERE id = ?',
        (conversation_id,),
    ).fetchone()
    if not conv:
        return None, 'Not found'
    if user_role == 'admin':
        return conv, None
    if conv['seeker_id'] == user_id:
        return conv, None
    job = db.execute('SELECT employer_id FROM jobs WHERE id = ?', (conv['job_id'],)).fetchone()
    if job and employer_can_access_job(db, user_id, user_role, dict(job)):
        return conv, None
    return None, 'Not authorized'


def _get_or_create_conversation(db, application_id):
    existing = db.execute(
        'SELECT * FROM conversations WHERE application_id = ?',
        (application_id,),
    ).fetchone()
    if existing:
        return existing

    app_row = db.execute(
        """
        SELECT a.id, a.user_id as seeker_id, j.id as job_id, j.employer_id
        FROM applications a
        JOIN jobs j ON j.id = a.job_id
        WHERE a.id = ?
        """,
        (application_id,),
    ).fetchone()
    if not app_row:
        return None

    now = utcnow_iso()
    db.execute(
        """INSERT INTO conversations (application_id, job_id, employer_id, seeker_id, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (app_row['id'], app_row['job_id'], app_row['employer_id'], app_row['seeker_id'], now),
    )
    db.commit()
    return db.execute(
        'SELECT * FROM conversations WHERE application_id = ?',
        (application_id,),
    ).fetchone()


@messages_bp.route('/api/conversations', methods=['GET'])
@require_auth
def list_conversations():
    db = get_db()
    if request.user_role == 'admin':
        rows = db.execute(
            """
            SELECT c.*, j.title as job_title, j.company as job_company,
                   su.name as seeker_name, eu.name as employer_name
            FROM conversations c
            JOIN jobs j ON j.id = c.job_id
            JOIN users su ON su.id = c.seeker_id
            JOIN users eu ON eu.id = c.employer_id
            ORDER BY c.created_at DESC LIMIT 100
            """
        ).fetchall()
    elif request.user_role == 'employer':
        team_ids = get_team_member_user_ids(db, request.user_id)
        placeholders = ','.join('?' * len(team_ids))
        rows = db.execute(
            f"""
            SELECT c.*, j.title as job_title, j.company as job_company,
                   su.name as seeker_name
            FROM conversations c
            JOIN jobs j ON j.id = c.job_id
            JOIN users su ON su.id = c.seeker_id
            WHERE c.employer_id IN ({placeholders})
            ORDER BY c.created_at DESC
            """,
            team_ids,
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT c.*, j.title as job_title, j.company as job_company,
                   eu.name as employer_name
            FROM conversations c
            JOIN jobs j ON j.id = c.job_id
            JOIN users eu ON eu.id = c.employer_id
            WHERE c.seeker_id = ?
            ORDER BY c.created_at DESC
            """,
            (request.user_id,),
        ).fetchall()
    return jsonify({'conversations': [dict(row) for row in rows]})


@messages_bp.route('/api/conversations', methods=['POST'])
@require_auth
@limiter.limit('60 per hour')
def start_conversation():
    data = request.json or {}
    application_id = data.get('application_id')
    if not application_id:
        return jsonify({'error': 'application_id is required'}), 400

    db = get_db()
    app_row = db.execute(
        """
        SELECT a.id, a.user_id, j.employer_id, j.id as job_id
        FROM applications a JOIN jobs j ON j.id = a.job_id WHERE a.id = ?
        """,
        (application_id,),
    ).fetchone()
    if not app_row:
        return jsonify({'error': 'Application not found'}), 404

    if request.user_role == 'admin':
        pass
    elif app_row['user_id'] == request.user_id:
        pass
    elif request.user_role == 'employer' and employer_can_access_job(
        db, request.user_id, request.user_role, {'employer_id': app_row['employer_id']}
    ):
        pass
    else:
        return jsonify({'error': 'Not authorized'}), 403

    conv = _get_or_create_conversation(db, application_id)
    return jsonify({'success': True, 'conversation': dict(conv)})


@messages_bp.route('/api/conversations/<int:conversation_id>/messages', methods=['GET'])
@require_auth
def get_messages(conversation_id):
    db = get_db()
    conv, err = _conversation_access(db, conversation_id, request.user_id, request.user_role)
    if err:
        return jsonify({'error': err}), 404 if err == 'Not found' else 403

    rows = db.execute(
        'SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC',
        (conversation_id,),
    ).fetchall()
    return jsonify({'messages': [dict(row) for row in rows]})


@messages_bp.route('/api/conversations/<int:conversation_id>/messages', methods=['POST'])
@require_auth
@limiter.limit('120 per hour')
def post_message(conversation_id):
    data = request.json or {}
    body = (data.get('body') or '').strip()
    if not body:
        return jsonify({'error': 'body is required'}), 400
    if len(body) > 10000:
        return jsonify({'error': 'Message too long'}), 400

    db = get_db()
    conv, err = _conversation_access(db, conversation_id, request.user_id, request.user_role)
    if err:
        return jsonify({'error': err}), 404 if err == 'Not found' else 403

    now = utcnow_iso()
    db.execute(
        'INSERT INTO messages (conversation_id, sender_id, body, created_at) VALUES (?, ?, ?, ?)',
        (conversation_id, request.user_id, body, now),
    )
    db.commit()
    msg_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    msg = db.execute('SELECT * FROM messages WHERE id = ?', (msg_id,)).fetchone()
    return jsonify({'success': True, 'message': dict(msg)}), 201
