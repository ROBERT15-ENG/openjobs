"""Auth routes."""

import datetime
import secrets
import sqlite3
import threading

from auth_utils import create_token, hash_password, require_auth, verify_password
from db import get_db, get_db_path
from extensions import BLOCKED_TOKENS, limiter
from flask import Blueprint, jsonify, request
from resume_util import ALLOWED_EXT, extract_resume_text
from skills_util import extract_skills_fast

from email_notifier import send_email

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/auth/register', methods=['POST'])
@limiter.limit('5 per hour')
def register():
    data = request.json or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    role = 'user'

    if not name or not email or not password:
        return jsonify({'error': 'Missing required fields'}), 400
    if '@' not in email or '.' not in email:
        return jsonify({'error': 'Invalid email format'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    db = get_db()
    if db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone():
        return jsonify({'error': 'Email already registered'}), 400

    db.execute(
        'INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)',
        (name, email, hash_password(password), role, datetime.datetime.now().isoformat()),
    )
    db.commit()
    user_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    token = create_token({'id': user_id, 'email': email, 'role': role})
    return jsonify({
        'success': True,
        'message': 'Registered successfully',
        'token': token,
        'user': {'id': user_id, 'name': name, 'email': email, 'role': role, 'employer_id': None},
    }), 201


@auth_bp.route('/api/auth/login', methods=['POST'])
@limiter.limit('10 per minute')
def login():
    data = request.json or {}
    email = data.get('email', '')
    password = data.get('password', '')
    db = get_db()
    user = db.execute(
        'SELECT id, name, email, password_hash, role FROM users WHERE email = ?',
        (email,),
    ).fetchone()
    if not user or not verify_password(password, user['password_hash']):
        return jsonify({'error': 'Invalid credentials'}), 401
    token = create_token(user)
    return jsonify({
        'success': True,
        'token': token,
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role'],
            'employer_id': user['id'] if user['role'] == 'employer' else None,
        },
    })


@auth_bp.route('/api/auth/register-employer', methods=['POST'])
def register_employer():
    data = request.json or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    if not name or not email or not password:
        return jsonify({'error': 'Name, email, and password are required'}), 400
    if '@' not in email or '.' not in email:
        return jsonify({'error': 'Invalid email'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    db = get_db()
    if db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone():
        return jsonify({'error': 'Email already registered'}), 400

    db.execute(
        'INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)',
        (name, email, hash_password(password), 'employer', datetime.datetime.now().isoformat()),
    )
    db.commit()
    user_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    token = create_token({'id': user_id, 'email': email, 'role': 'employer'})
    return jsonify({
        'success': True,
        'token': token,
        'user': {'id': user_id, 'name': name, 'email': email, 'role': 'employer', 'employer_id': user_id},
    }), 201


@auth_bp.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json or {}
    email = data.get('email', '').strip()
    if not email or '@' not in email:
        return jsonify({'error': 'Valid email is required'}), 400

    db = get_db()
    user = db.execute('SELECT id, name FROM users WHERE email = ?', (email,)).fetchone()
    if not user:
        return jsonify({'message': 'If that email exists, a reset link has been sent.'}), 200

    token = secrets.token_urlsafe(32)
    expires = datetime.datetime.now() + datetime.timedelta(hours=1)
    db.execute(
        'UPDATE users SET reset_token = ?, reset_expires = ? WHERE id = ?',
        (token, expires.isoformat(), user['id']),
    )
    db.commit()

    from flask import current_app
    reset_link = f"{current_app.config['BASE_URL']}/reset-password.html?token={token}"
    user_name = user['name'] or email.split('@')[0]
    html = f"""
    <html><body style="font-family: Inter, Arial, sans-serif; background: #0a0a0f; color: #e0e0e0; padding: 32px;">
      <div style="max-width: 480px; margin: 0 auto;">
        <h1 style="color: #00d4ff;">Password Reset Request</h1>
        <p>Hi <strong>{user_name}</strong>, reset your OpenJobs password:</p>
        <a href="{reset_link}" style="display:inline-block;background:#00d4ff;color:#000;padding:14px 28px;border-radius:10px;text-decoration:none;font-weight:700;">Reset Password</a>
      </div>
    </body></html>"""
    result = send_email(email, 'Reset your OpenJobs password', html)
    if not result.get('success'):
        return jsonify({'error': 'Failed to send email. SMTP may not be configured.'}), 500
    return jsonify({'message': 'If that email exists, a reset link has been sent.'}), 200


@auth_bp.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.json or {}
    token = data.get('token', '').strip()
    password = data.get('password', '')
    if not token or not password:
        return jsonify({'error': 'Token and new password are required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    db = get_db()
    user = db.execute(
        'SELECT id FROM users WHERE reset_token = ? AND reset_expires > ?',
        (token, datetime.datetime.now().isoformat()),
    ).fetchone()
    if not user:
        return jsonify({'error': 'Invalid or expired reset token. Please request a new one.'}), 400

    db.execute(
        'UPDATE users SET password_hash = ?, reset_token = NULL, reset_expires = NULL WHERE id = ?',
        (hash_password(password), user['id']),
    )
    db.commit()
    return jsonify({'success': True, 'message': 'Password reset successful!'}), 200


@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        BLOCKED_TOKENS.add(auth.split(' ', 1)[1])
    return jsonify({'success': True, 'message': 'Logged out'})


@auth_bp.route('/api/auth/me', methods=['GET'])
@require_auth
def me():
    db = get_db()
    user = db.execute(
        'SELECT id, name, email, role, skills, phone, company, preferred_location, created_at FROM users WHERE id = ?',
        (request.user_id,),
    ).fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    user_dict = dict(user)
    user_dict['employer_id'] = user_dict['id'] if user_dict['role'] == 'employer' else None
    return jsonify({'user': user_dict})


@auth_bp.route('/api/resume/upload', methods=['POST'])
@require_auth
def upload_resume():
    import os
    import re

    from config import UPLOAD_DIR

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify({'error': 'File type not allowed. Upload PDF, DOC, or DOCX.'}), 400

    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', file.filename)
    filename = f'user_{request.user_id}_{int(datetime.datetime.now().timestamp())}_{safe_name}'
    filepath = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)

    from resume_util import MAX_SIZE
    if os.path.getsize(filepath) > MAX_SIZE:
        os.remove(filepath)
        return jsonify({'error': 'File too large. Maximum size is 5 MB.'}), 400

    text = extract_resume_text(filepath)
    if not text.strip():
        os.remove(filepath)
        return jsonify({'error': 'Could not extract text from file. Try a different format.'}), 400

    db = get_db()
    db.execute(
        'UPDATE users SET cv_link = ?, resume_text = ? WHERE id = ?',
        (filename, text[:50000], request.user_id),
    )
    db.commit()

    extracted_skills = extract_skills_fast(text)
    if extracted_skills:
        conn = sqlite3.connect(get_db_path())
        conn.execute(
            'UPDATE users SET skills = ? WHERE id = ?',
            (','.join(extracted_skills), request.user_id),
        )
        conn.commit()
        conn.close()

    text_captured = text
    user_id = request.user_id

    def _parse_async():
        try:
            from ai_matcher import parse_resume
            parsed = parse_resume(text_captured)
            if parsed and parsed.get('skills'):
                conn = sqlite3.connect(get_db_path())
                conn.execute(
                    'UPDATE users SET skills = ? WHERE id = ?',
                    (','.join(parsed['skills'][:20]), user_id),
                )
                conn.commit()
                conn.close()
        except Exception as exc:
            print(f'[resume/parse] background parse: {exc}')

    threading.Thread(target=_parse_async, daemon=True).start()
    return jsonify({
        'success': True,
        'filename': filename,
        'text_length': len(text),
        'skills_found': extracted_skills,
        'message': 'Resume uploaded. Skills extracted and stored.',
    }), 201


@auth_bp.route('/api/resume/parse', methods=['POST'])
@require_auth
def parse_resume_ai():
    data = request.json or {}
    resume_text = data.get('resume_text', '')
    if not resume_text:
        return jsonify({'error': 'resume_text required'}), 400
    try:
        from ai_matcher import parse_resume
        parsed = parse_resume(resume_text)
        return jsonify({'success': True, 'parsed': parsed})
    except Exception as exc:
        return jsonify({'error': f'Ollama unavailable: {exc}'}), 503
