"""Auth routes."""

import hashlib
import html
import logging
import os
import re
import secrets
import sqlite3
import threading

from auth_utils import create_token, hash_password, require_auth, revoke_token, verify_password
from config import UPLOAD_DIR, ensure_upload_dir
from db import connect, get_db
from extensions import limiter
from flask import Blueprint, current_app, jsonify, request
from org_util import create_organization_for_employer
from password_util import validate_password
from resume_util import ALLOWED_EXT, MAX_SIZE, extract_resume_text
from session_util import clear_session_cookie, extract_bearer_or_cookie_token, set_session_cookie
from skills_util import extract_skills_fast
from timeutil import iso_after, utcnow, utcnow_iso
from validation import Email, Str, ValidationError, validate_payload

from email_notifier import is_configured as smtp_configured
from email_notifier import send_email

log = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

REGISTER_FIELDS = {
    'name': Str(max_len=120, required=True),
    'email': Email(required=True),
    'password': Str(max_len=256, strip=False, required=True),
}
EMPLOYER_REGISTER_FIELDS = {**REGISTER_FIELDS, 'company': Str(max_len=160, required=True)}
LOGIN_FIELDS = {'email': Email(required=True), 'password': Str(max_len=256, strip=False, required=True)}


def normalize_email(email: str | None) -> str:
    return (email or '').strip().lower()


def _hash_token(raw: str) -> str:
    """Reset/confirm tokens are stored hashed so a DB read can't mint links."""
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _auth_response(payload: dict, status: int = 200, token: str | None = None):
    resp = jsonify(payload)
    if token:
        set_session_cookie(resp, token)
    return resp, status


def _user_payload(user_id: int, name: str, email: str, role: str, **extra) -> dict:
    return {
        'id': user_id,
        'name': name,
        'email': email,
        'role': role,
        'employer_id': user_id if role == 'employer' else None,
        **extra,
    }


def _send_confirmation_email(to_email: str, user_name: str, confirm_link: str) -> dict:
    safe_name = html.escape(user_name or to_email.split('@')[0])
    safe_link = html.escape(confirm_link)
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f0f0f;color:#fff;padding:20px;">
      <div style="max-width:600px;margin:0 auto;text-align:center;">
        <h1 style="color:#00d4ff;">Confirm your email</h1>
        <p>Hi {safe_name}, click below to verify your OpenJobs account:</p>
        <div style="margin:30px 0;">
          <a href="{safe_link}" style="background:#00d4ff;color:#000;padding:15px 30px;text-decoration:none;border-radius:8px;font-weight:bold;">Confirm Email</a>
        </div>
        <p style="color:#888;font-size:12px;">This link expires in 24 hours.</p>
      </div>
    </body></html>"""
    return send_email(to_email, 'Confirm your OpenJobs account', html_body)


def _issue_confirmation(db, user_id: int, email: str, name: str) -> None:
    raw_token = secrets.token_urlsafe(32)
    db.execute(
        'UPDATE users SET confirm_token = ?, confirm_expires = ? WHERE id = ?',
        (_hash_token(raw_token), iso_after(hours=24), user_id),
    )
    db.commit()
    confirm_link = f"{current_app.config['BASE_URL']}/api/auth/confirm-email?token={raw_token}"
    _send_confirmation_email(email, name, confirm_link)


def _register_user(data: dict, role: str, company: str | None = None):
    pw_err = validate_password(data['password'])
    if pw_err:
        return jsonify({'error': pw_err}), 400

    db = get_db()
    # Without SMTP, confirmation email cannot arrive — auto-confirm (ekip pattern)
    confirmed = 0 if smtp_configured() else 1
    try:
        cur = db.execute(
            """INSERT INTO users (name, email, password_hash, role, company, created_at, email_confirmed)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (data['name'], data['email'], hash_password(data['password']), role, company, utcnow_iso(), confirmed),
        )
        user_id = cur.lastrowid
        if role == 'employer':
            create_organization_for_employer(db, company, user_id)
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify({'error': 'Email already registered'}), 409

    if not confirmed:
        _issue_confirmation(db, user_id, data['email'], data['name'])
        return jsonify({
            'success': True,
            'message': 'Registered! Check your email to confirm your account.',
            'email_confirmed': False,
        }), 201

    token = create_token({'id': user_id, 'email': data['email'], 'role': role})
    extra = {'company': company, 'employer_id': user_id} if role == 'employer' else {}
    return _auth_response({
        'success': True,
        'message': 'Registered successfully',
        'token': token,
        'email_confirmed': True,
        'user': _user_payload(user_id, data['name'], data['email'], role, **extra),
    }, 201, token)


@auth_bp.route('/api/auth/register', methods=['POST'])
@limiter.limit('5 per hour')
def register():
    try:
        data = validate_payload(request.json, REGISTER_FIELDS)
    except ValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return _register_user(data, 'user')


@auth_bp.route('/api/auth/register-employer', methods=['POST'])
@limiter.limit('5 per hour')
def register_employer():
    try:
        data = validate_payload(request.json, EMPLOYER_REGISTER_FIELDS)
    except ValidationError as exc:
        return jsonify({'error': str(exc)}), 400
    return _register_user(data, 'employer', company=data['company'])


@auth_bp.route('/api/auth/login', methods=['POST'])
@limiter.limit('10 per minute')
def login():
    data = request.json or {}
    email = normalize_email(data.get('email'))
    password = data.get('password') or ''
    db = get_db()
    user = db.execute(
        'SELECT id, name, email, password_hash, role, email_confirmed FROM users WHERE lower(email) = ?',
        (email,),
    ).fetchone()
    if not user or not verify_password(password, user['password_hash']):
        return jsonify({'error': 'Invalid credentials'}), 401
    if user['email_confirmed'] is not None and int(user['email_confirmed']) == 0:
        return jsonify({
            'error': 'email_not_confirmed',
            'message': 'Please confirm your email before logging in.',
        }), 403
    token = create_token(user)
    return _auth_response({
        'success': True,
        'token': token,
        'user': _user_payload(user['id'], user['name'], user['email'], user['role']),
    }, 200, token)


@auth_bp.route('/api/auth/forgot-password', methods=['POST'])
@limiter.limit('5 per hour')
def forgot_password():
    data = request.json or {}
    email = normalize_email(data.get('email'))
    if not email or '@' not in email:
        return jsonify({'error': 'Valid email is required'}), 400

    if not smtp_configured():
        # Nothing can be delivered; saying "link sent" would strand the user.
        # This message does not depend on whether the account exists.
        support = current_app.config.get('SUPPORT_EMAIL') or os.environ.get('SUPPORT_EMAIL')
        contact = f' Contact {support} to have it reset.' if support else ' Contact the site administrator to have it reset.'
        return jsonify({
            'message': 'Password reset by email is not available on this site.' + contact,
            'email_delivery': False,
        }), 200

    # Same response whether or not the account exists (no enumeration).
    generic = jsonify({'message': 'If that email exists, a reset link has been sent.', 'email_delivery': True}), 200

    db = get_db()
    user = db.execute('SELECT id, name FROM users WHERE lower(email) = ?', (email,)).fetchone()
    if not user:
        return generic

    raw_token = secrets.token_urlsafe(32)
    db.execute(
        'UPDATE users SET reset_token = ?, reset_expires = ? WHERE id = ?',
        (_hash_token(raw_token), iso_after(hours=1), user['id']),
    )
    db.commit()

    reset_link = f"{current_app.config['BASE_URL']}/reset-password.html?token={raw_token}"
    user_name = html.escape(user['name'] or email.split('@')[0])
    safe_link = html.escape(reset_link)
    html_body = f"""
    <html><body style="font-family: Inter, Arial, sans-serif; background: #0a0a0f; color: #e0e0e0; padding: 32px;">
      <div style="max-width: 480px; margin: 0 auto;">
        <h1 style="color: #00d4ff;">Password Reset Request</h1>
        <p>Hi <strong>{user_name}</strong>, reset your OpenJobs password:</p>
        <a href="{safe_link}" style="display:inline-block;background:#00d4ff;color:#000;padding:14px 28px;border-radius:10px;text-decoration:none;font-weight:700;">Reset Password</a>
        <p style="color:#888;font-size:12px;">This link expires in 1 hour.</p>
      </div>
    </body></html>"""
    result = send_email(email, 'Reset your OpenJobs password', html_body)
    if not result.get('success'):
        log.warning('password reset email not sent for user %s: %s', user['id'], result.get('error'))
    return generic


@auth_bp.route('/api/auth/reset-password', methods=['POST'])
@limiter.limit('10 per hour')
def reset_password():
    data = request.json or {}
    token = (data.get('token') or '').strip()
    password = data.get('password') or ''
    if not token or not password:
        return jsonify({'error': 'Token and new password are required'}), 400
    pw_err = validate_password(password)
    if pw_err:
        return jsonify({'error': pw_err}), 400

    db = get_db()
    user = db.execute(
        'SELECT id FROM users WHERE reset_token = ? AND reset_expires > ?',
        (_hash_token(token), utcnow_iso()),
    ).fetchone()
    if not user:
        return jsonify({'error': 'Invalid or expired reset token. Please request a new one.'}), 400

    db.execute(
        'UPDATE users SET password_hash = ?, reset_token = NULL, reset_expires = NULL WHERE id = ?',
        (hash_password(password), user['id']),
    )
    db.commit()
    return jsonify({'success': True, 'message': 'Password reset successful!'}), 200


@auth_bp.route('/api/auth/confirm-email', methods=['GET'])
def confirm_email():
    token = request.args.get('token', '').strip()
    if not token:
        return jsonify({'error': 'Confirmation token required'}), 400
    db = get_db()
    user = db.execute(
        'SELECT id, email_confirmed FROM users WHERE confirm_token = ? AND confirm_expires > ?',
        (_hash_token(token), utcnow_iso()),
    ).fetchone()
    if not user:
        return jsonify({'error': 'Invalid or expired confirmation token'}), 400
    if user['email_confirmed']:
        return jsonify({'success': True, 'message': 'Email already confirmed'}), 200
    db.execute(
        'UPDATE users SET email_confirmed = 1, confirm_token = NULL, confirm_expires = NULL WHERE id = ?',
        (user['id'],),
    )
    db.commit()
    return jsonify({'success': True, 'message': 'Email confirmed! You can now log in.'}), 200


@auth_bp.route('/api/auth/google', methods=['POST'])
@limiter.limit('10 per minute')
def google_auth():
    """Google Sign-In via ID token (ekip lineage). Requires google-auth + GOOGLE_CLIENT_ID."""
    data = request.json or {}
    google_token = data.get('token')
    if not google_token:
        return jsonify({'error': 'Google token required'}), 400

    client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
    if not client_id:
        return jsonify({
            'error': 'Google Sign-In is not configured',
            'message': 'Set GOOGLE_CLIENT_ID to enable Google authentication.',
        }), 503

    try:
        from google.auth.transport import requests as gauth
        from google.oauth2 import id_token as gid_token
        id_info = gid_token.verify_oauth2_token(
            google_token,
            gauth.Request(),
            audience=client_id,
        )
    except ImportError:
        return jsonify({'error': 'Google Sign-In not available (install google-auth)'}), 503
    except Exception as exc:
        log.info('google token rejected: %s', exc)
        return jsonify({'error': 'Invalid Google token'}), 401

    if not id_info.get('email_verified'):
        return jsonify({'error': 'Google email is not verified'}), 401

    google_id = id_info.get('sub')
    email = normalize_email(id_info.get('email'))
    name = id_info.get('name', '') or (email.split('@')[0] if email else 'Google User')
    if not email or not google_id:
        return jsonify({'error': 'Email not available from Google account'}), 400

    db = get_db()
    user = db.execute(
        'SELECT id, name, email, role FROM users WHERE google_id = ? OR lower(email) = ?',
        (google_id, email),
    ).fetchone()

    if not user:
        try:
            cur = db.execute(
                """INSERT INTO users (name, email, password_hash, google_id, email_confirmed, role, created_at)
                   VALUES (?, ?, '', ?, 1, 'user', ?)""",
                (name, email, google_id, utcnow_iso()),
            )
            db.commit()
            uid = cur.lastrowid
            role = 'user'
        except sqlite3.IntegrityError:
            db.rollback()
            return jsonify({
                'error': 'Email already registered with a password. Please sign in with email instead.',
            }), 409
    else:
        uid = user['id']
        role = user['role']
        db.execute(
            'UPDATE users SET google_id = COALESCE(google_id, ?), email_confirmed = 1 WHERE id = ?',
            (google_id, uid),
        )
        if name and name != user['name']:
            db.execute('UPDATE users SET name = ? WHERE id = ?', (name, uid))
        db.commit()

    token = create_token({'id': uid, 'email': email, 'role': role})
    return _auth_response({
        'success': True,
        'token': token,
        'user': _user_payload(uid, name, email, role),
    }, 200, token)


@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    token = extract_bearer_or_cookie_token(request)
    if token:
        revoke_token(token)
    resp = jsonify({'success': True, 'message': 'Logged out'})
    clear_session_cookie(resp)
    return resp


@auth_bp.route('/api/auth/me', methods=['GET'])
@require_auth
def me():
    db = get_db()
    user = db.execute(
        """SELECT id, name, email, role, skills, phone, company, preferred_location,
                  email_confirmed, kyc_status, country, created_at
           FROM users WHERE id = ?""",
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
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify({'error': 'File type not allowed. Upload PDF, DOC, or DOCX.'}), 400

    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_SIZE:
        return jsonify({'error': 'File too large. Maximum size is 5 MB.'}), 400

    ensure_upload_dir()
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', file.filename)[-100:]
    filename = f'user_{request.user_id}_{int(utcnow().timestamp())}_{safe_name}'
    filepath = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)

    text = extract_resume_text(filepath)
    if not text.strip():
        os.remove(filepath)
        return jsonify({'error': 'Could not extract text from file. Try a different format.'}), 400

    extracted_skills = extract_skills_fast(text)
    db = get_db()
    db.execute(
        'UPDATE users SET cv_link = ?, resume_text = ?, skills = COALESCE(NULLIF(?, \'\'), skills) WHERE id = ?',
        (filename, text[:50000], ','.join(extracted_skills), request.user_id),
    )
    db.commit()

    text_captured = text
    user_id = request.user_id

    def _parse_async():
        try:
            from ai_matcher import parse_resume
            parsed = parse_resume(text_captured)
            if parsed and parsed.get('skills'):
                conn = connect()
                try:
                    conn.execute(
                        'UPDATE users SET skills = ? WHERE id = ?',
                        (','.join(parsed['skills'][:20]), user_id),
                    )
                    conn.commit()
                finally:
                    conn.close()
        except Exception as exc:
            log.info('[resume/parse] background parse skipped: %s', exc)

    threading.Thread(target=_parse_async, daemon=True).start()
    return jsonify({
        'success': True,
        'filename': filename,
        'text_length': len(text),
        'resume_text': text[:50000],
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
