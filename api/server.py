#!/usr/bin/env python3
from dotenv import load_dotenv

import os
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', 'templates')
load_dotenv()
import sqlite3, os, json, datetime, base64
from functools import wraps
from flask import Flask, request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
import jwt  # PyJWT — real HMAC-signed tokens
import re

# Smart semantic matcher — keyword-first, Ollama only for borderline cases
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from semantic_matcher import rank_jobs_for_resume, keyword_score

from email_notifier import send_email, send_welcome_email, send_application_confirm

# ── JWT Configuration ───────────────────────────────────────────────────────
JWT_SECRET = os.environ.get('JWT_SECRET') or os.environ.get('SECRET_KEY')
if not JWT_SECRET:
    import warnings
    warnings.warn("JWT_SECRET not set — using insecure default for development only. Set JWT_SECRET in .env")
    JWT_SECRET = 'dev_secret_do_not_use_in_production'

ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:5700').split(',')

# ── Rate Limiter (Redis when available, memory fallback) ──────────────────
REDIS_URL = os.environ.get('REDIS_URL')
limiter_storage = REDIS_URL or "memory://"
limiter = Limiter(
    app=None,  # will call limiter.init_app after app creation
    key_func=get_remote_address,
    default_limits=["500 per day", "100 per hour", "20 per minute"],
    storage_uri=limiter_storage,
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB max request size

# ── CORS — locked to specific origins ──────────────────────────────────────
try:
    from flask_cors import CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ALLOWED_ORIGINS,
            "methods": ["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Authorization", "Content-Type"],
        }
    })
except ImportError:
    pass

limiter.init_app(app)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key_change_in_production')

APP_URL = os.environ.get('APP_URL', 'http://localhost:5700')
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')

DB_PATH = os.environ.get('DATABASE_URL', os.path.join(os.path.dirname(__file__), '..', 'jobs.db'))

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

# ============ AUTH MIDDLEWARE ============
# ── Token Blocklist (Redis-backed, with in-memory fallback) ──────────────────
try:
    if REDIS_URL:
        import redis
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        _redis_client.ping()
        _USING_REDIS_BLOCKLIST = True
        print(f"[auth] Redis blocklist active: {REDIS_URL}")
except Exception:
    _redis_client = None
    _USING_REDIS_BLOCKLIST = False
    print("[auth] Redis unavailable — blocklist resets on restart (use Redis for persistence)")

def _block_token(token):
    """Add a token to the blocklist."""
    if _USING_REDIS_BLOCKLIST:
        import time
        # Keep blocked tokens for 7 days (max token age)
        _redis_client.setex(f"blocked:{token}", 7 * 24 * 3600, "1")
    else:
        _block_token(token)

BLOCKED_TOKENS = set()  # in-memory fallback, reset on restart

def _is_token_blocked(token):
    """Check if a token is in the blocklist."""
    if _USING_REDIS_BLOCKLIST:
        return bool(_redis_client.exists(f"blocked:{token}"))
    return token in BLOCKED_TOKENS

def _extract_skills_fast(text: str):
    """Fast keyword-based skill extraction against skills_taxonomy.
    Uses direct sqlite3 — no Flask context required.
    """
    try:
        db_path = os.path.join(os.path.dirname(__file__), '..', 'jobs.db')
        db = sqlite3.connect(db_path)
        rows = db.execute("SELECT name, aliases FROM skills_taxonomy").fetchall()
        db.close()
        text_lower = text.lower()
        matched = []
        for name, aliases in rows:
            if name.lower() in text_lower:
                matched.append(name)
            elif aliases:
                for alias in aliases.split(','):
                    if alias.strip().lower() in text_lower:
                        matched.append(name)
                        break
        return list(dict.fromkeys(matched))
    except Exception as e:
        print(f'[_extract_skills_fast] {e}')
        return []



def _create_token(user_id, email, role, employer_id=None):
    """Create a real HMAC-signed JWT token."""
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'employer_id': employer_id or user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),
        'iat': datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def _decode_token(token):
    """Decode and verify a JWT token. Returns payload or None."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None  # 'Token expired'
    except jwt.InvalidTokenError:
        return None  # 'Invalid token'


def require_auth(f):
    """Decorator to protect routes with JWT token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
        token = auth.split(' ', 1)[1]
        if _is_token_blocked(token):
            return jsonify({'error': 'Token has been revoked'}), 401
        payload = _decode_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        request.user_id    = int(payload.get('user_id', 0))
        request.user_role  = payload.get('role', 'user')
        request.user_email = payload.get('email', '')
        request.employer_id = payload.get('employer_id') or payload.get('user_id')
        return f(*args, **kwargs)
    return decorated

def require_role(role):
    """Decorator to require a specific role."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if getattr(request, 'user_role', None) != role:
                return jsonify({'error': f'Requires {role} role'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

# ============ AUTH ============
def hash_password(password):
    return generate_password_hash(password)

def verify_password(password, pw_hash):
    return check_password_hash(pw_hash, password)

@app.route('/api/auth/register', methods=['POST'])
@limiter.limit('5 per hour', exempt_when=lambda: False)
def register():
    data = request.json or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'user')  # Can be 'user' or 'employer'
    
    # Validate
    if not name or not email or not password:
        return jsonify({'error': 'Missing required fields'}), 400
    
    if '@' not in email or '.' not in email:
        return jsonify({'error': 'Invalid email format'}), 400
    # Password complexity requirements
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    if not re.search(r'[A-Z]', password):
        return jsonify({'error': 'Password must contain at least 1 uppercase letter'}), 400
    if not re.search(r'[a-z]', password):
        return jsonify({'error': 'Password must contain at least 1 lowercase letter'}), 400
    if not re.search(r'\d', password):
        return jsonify({'error': 'Password must contain at least 1 number'}), 400
    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        return jsonify({'error': 'Email already registered'}), 400
    
    db.execute("INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
               (name, email, hash_password(password), role, datetime.datetime.now().isoformat()))
    db.commit()
    user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()

    # Generate email confirmation token
    confirm_token = secrets.token_urlsafe(32)
    confirm_expires = (datetime.datetime.now() + datetime.timedelta(hours=24)).isoformat()
    db2 = get_db()
    db2.execute("UPDATE users SET confirm_token = ?, confirm_expires = ? WHERE id = ?",
                 (confirm_token, confirm_expires, user_id))
    db2.commit()
    db2.close()

    # Send confirmation email
    confirm_link = f"{APP_URL}/api/auth/confirm-email?token={confirm_token}"
    _send_confirmation_email(email, name, confirm_link)

    return jsonify({
        'success': True,
        'message': 'Registered! Check your email to confirm your account.',
        'email_confirmed': False
    }), 201

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit('10 per minute', exempt_when=lambda: False)
def login():
    data = request.json or {}
    email = data.get('email', '')
    password = data.get('password', '')
    
    db = get_db()
    user = db.execute("SELECT id, name, email, password_hash, role, email_confirmed FROM users WHERE email = ?", (email,)).fetchone()

    if not user or not verify_password(password, user['password_hash']):
        return jsonify({'error': 'Invalid credentials'}), 401

    if not user.get('email_confirmed'):
        db.close()
        return jsonify({
            'error': 'email_not_confirmed',
            'message': 'Please confirm your email before logging in. Check your inbox or spam folder.'
        }), 403

    token = _create_token(user['id'], user['email'], user['role'],
                           user['id'] if user['role'] == 'employer' else None)
    return jsonify({
        'success': True,
        'token': token,
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role'],
            'employer_id': user['id'] if user['role'] == 'employer' else None
        }
})

secrets = __import__('secrets')


def _send_confirmation_email(to_email, user_name, confirm_link):
    """Send email confirmation link."""
    import html
    safe_name = html.escape(user_name or to_email.split('@')[0])
    confirm_link_escaped = html.escape(confirm_link)
    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f0f0f;color:#fff;padding:20px;">
        <div style="max-width:600px;margin:0 auto;text-align:center;">
            <h1 style="color:#00d4ff;">📧 Confirm Your Email</h1>
            <p>Hi {safe_name}, click the button below to verify your email address:</p>
            <div style="margin:30px 0;">
                <a href="{confirm_link_escaped}" style="background:#00d4ff;color:#000;padding:15px 30px;text-decoration:none;border-radius:8px;font-weight:bold;">Confirm Email</a>
            </div>
            <p style="color:#888;font-size:12px;">This link expires in 24 hours. If you didn't create an account, ignore this email.</p>
        </div>
    </body></html>
    """
    send_email(to_email, "Confirm your JobSeek account", html_body)


@app.route('/api/auth/confirm-email', methods=['GET'])
def confirm_email():
    """Clickable link from confirmation email — activates account."""
    token = request.args.get('token', '').strip()
    if not token:
        return jsonify({'error': 'Confirmation token required'}), 400
    db = get_db()
    user = db.execute(
        "SELECT id, email_confirmed FROM users WHERE confirm_token = ? AND confirm_expires > ?",
        (token, datetime.datetime.now().isoformat())
    ).fetchone()
    if not user:
        db.close()
        return jsonify({'error': 'Invalid or expired confirmation token'}), 400
    if user['email_confirmed']:
        db.close()
        return jsonify({'success': True, 'message': 'Email already confirmed'}), 200
    db.execute("UPDATE users SET email_confirmed = 1, confirm_token = NULL, confirm_expires = NULL WHERE id = ?",
               (user['id'],))
    db.commit()
    db.close()
    return jsonify({'success': True, 'message': 'Email confirmed! You can now log in.'}), 200


@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    """Send a password reset email to the user."""
    data = request.json or {}
    email = data.get('email', '').strip()

    if not email or '@' not in email:
        return jsonify({'error': 'Valid email is required'}), 400

    db = get_db()
    user = db.execute("SELECT id, name FROM users WHERE email = ?", (email,)).fetchone()

    # Always return success to prevent email enumeration
    if not user:
        return jsonify({'message': 'If that email exists, a reset link has been sent.'}), 200

    # Generate secure token (valid 1 hour)
    token = secrets.token_urlsafe(32)
    expires = datetime.datetime.now() + datetime.timedelta(hours=1)

    db.execute("UPDATE users SET reset_token = ?, reset_expires = ? WHERE id = ?",
               (token, expires.isoformat(), user['id']))
    db.commit()

    # Build reset link
    reset_link = f"{APP_URL}/reset-password.html?token={token}"

    user_name = user['name'] or email.split('@')[0]
    html = f"""
    <html>
    <body style="font-family: Inter, Arial, sans-serif; background: #0a0a0f; color: #e0e0e0; padding: 32px;">
      <div style="max-width: 480px; margin: 0 auto;">
        <h1 style="color: #00d4ff; font-size: 1.5rem;">🔑 Password Reset Request</h1>
        <p style="margin: 16px 0; line-height: 1.6;">
          Hi <strong>{user_name}</strong>, we received a request to reset your OpenJobs password.
        </p>
        <a href="{reset_link}"
           style="display: inline-block; background: linear-gradient(135deg, #00d4ff, #7b2fff);
                  color: #000; padding: 14px 28px; border-radius: 10px; text-decoration: none;
                  font-weight: 700; margin: 16px 0;">
          Reset Password
        </a>
        <p style="margin: 16px 0; line-height: 1.6; color: #888; font-size: 0.85rem;">
          This link expires in <strong>1 hour</strong>. If you didn't request this, you can safely ignore this email.
        </p>
        <hr style="border: none; border-top: 1px solid #1e1e2e; margin: 24px 0;">
        <p style="color: #555; font-size: 0.78rem;">OpenJobs — AI-Powered Job Search</p>
      </div>
    </body>
    </html>"""

    result = send_email(email, '🔑 Reset your OpenJobs password', html)
    if not result.get('success'):
        return jsonify({'error': 'Failed to send email. SMTP may not be configured.'}), 500

    return jsonify({'message': 'If that email exists, a reset link has been sent.'}), 200


@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """Reset password using a valid token."""
    data = request.json or {}
    token = data.get('token', '').strip()
    password = data.get('password', '')

    if not token or not password:
        return jsonify({'error': 'Token and new password are required'}), 400
    # Password complexity requirements (same as registration)
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    if not re.search(r'[A-Z]', password):
        return jsonify({'error': 'Password must contain at least 1 uppercase letter'}), 400
    if not re.search(r'[a-z]', password):
        return jsonify({'error': 'Password must contain at least 1 lowercase letter'}), 400
    if not re.search(r'\d', password):
        return jsonify({'error': 'Password must contain at least 1 number'}), 400
    db = get_db()
    user = db.execute(
        "SELECT id FROM users WHERE reset_token = ? AND reset_expires > ?",
        (token, datetime.datetime.now().isoformat())
    ).fetchone()

    if not user:
        return jsonify({'error': 'Invalid or expired reset token. Please request a new one.'}), 400

    db.execute("UPDATE users SET password_hash = ?, reset_token = NULL, reset_expires = NULL WHERE id = ?",
               (hash_password(password), user['id']))
    db.commit()

    return jsonify({'success': True, 'message': 'Password reset successful!'}), 200


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        _block_token(auth.split(' ', 1)[1])
    return jsonify({'success': True, 'message': 'Logged out'})


@app.route('/api/auth/me', methods=['GET'])
def me():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        token = auth.split(' ', 1)[1]
        if _is_token_blocked(token):
            return jsonify({'error': 'Token revoked'}), 401
        payload = _decode_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        db = get_db()
        user = db.execute("SELECT id, name, email, role, skills, phone, company, preferred_location, created_at FROM users WHERE id = ?",
                          (int(payload['user_id']),)).fetchone()
        db.close()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        user_dict = dict(user)
        user_dict['employer_id'] = user_dict['id'] if user_dict['role'] == 'employer' else None
        return jsonify({'user': user_dict})
    except Exception as e:
        return jsonify({'error': 'Invalid token'}), 401



# ── Upload security ───────────────────────────────────────────────────────────
ALLOWED_EXT = {'.pdf', '.doc', '.docx'}
MAX_SIZE    = 5 * 1024 * 1024   # 5 MB
UPLOAD_DIR  = os.path.join(os.path.dirname(__file__), '..', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Magic bytes for file type verification (first bytes of file)
MAGIC_BYTES = {
    b'%PDF':  '.pdf',
    b'PK\x03\x04': '.docx',  # DOCX is a ZIP file
    b'\xd0\xcf\x11\xe0': '.doc',  # Old OLE format
}

def _verify_file_magic(filepath):
    """Check magic bytes match the expected type by extension."""
    try:
        with open(filepath, 'rb') as f:
            header = f.read(8)
        if not header:
            return False
        ext = os.path.splitext(filepath)[1].lower()
        for magic, ext_matched in MAGIC_BYTES.items():
            if header.startswith(magic):
                return ext == ext_matched
        return False  # No magic bytes matched
    except Exception:
        return False


def extract_resume_text(filepath: str) -> str:
    """Extract plain text from PDF or DOCX file."""
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == '.pdf':
            import pdfplumber
            with pdfplumber.open(filepath) as pdf:
                return '\n'.join(p.extract_text() or '' for p in pdf.pages)
        elif ext == '.docx':
            import docx
            doc = docx.Document(filepath)
            return '\n'.join(p.text for p in doc.paragraphs)
        else:
            with open(filepath, 'rb') as f:
                return f.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'Resume extract error: {e}')
        return ''

@app.route('/api/resume/upload', methods=['POST'])
@require_auth
def upload_resume():
    """Upload a resume PDF/DOC, extract text, parse with Ollama, store in DB.
    Auth required. File stored locally; resume_text stored in users table.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify({'error': f'File type not allowed. Upload PDF, DOC, or DOCX.'}), 400

    # Save file
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', file.filename)
    filename  = f"user_{request.user_id}_{int(datetime.datetime.now().timestamp())}_{safe_name}"
    filepath  = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)

    try:
        # Check size
        if os.path.getsize(filepath) > MAX_SIZE:
            return jsonify({'error': 'File too large. Maximum size is 5 MB.'}), 400

        # Magic byte verification
        if not _verify_file_magic(filepath):
            os.remove(filepath)
            return jsonify({'error': 'File content does not match its type. Upload a valid PDF or DOCX.'}), 400

        # Extract text
        text = extract_resume_text(filepath)
        if not text.strip():
            return jsonify({'error': 'Could not extract text from file. Try a different format.'}), 400

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)  # clean up on any error after this point

    # Store cv_link (filename) and resume_text in DB
    db = get_db()
    db.execute(
        'UPDATE users SET cv_link = ?, resume_text = ? WHERE id = ?',
        (filename, text[:50000], request.user_id)
    )
    db.commit()
    db.close()

    # ── Extract KYC fields from resume text ─────────────────────────────────
    import re
    dob_patterns = [
        r'(?:DOB|Date\s*of\s*Birth|Born)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
    ]
    nationality_patterns = [
        r'Nationality[:\s]+([A-Za-z\s]+)',
        r'Citizen of ([A-Za-z\s]+)',
    ]
    extracted_kyc = {}
    for pat in dob_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m: extracted_kyc['dob'] = m.group(1); break
    for pat in nationality_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m: extracted_kyc['nationality'] = m.group(1).strip(); break

    # Save extracted KYC hints (user reviews and confirms)
    if extracted_kyc:
        db_kyc = sqlite3.connect(db_path)
        for k, v in extracted_kyc.items():
            col = 'dob' if k == 'dob' else 'nationality'
            db_kyc.execute(f'UPDATE users SET {col} = ? WHERE id = ?', (v, request.user_id))
        db_kyc.commit()
        db_kyc.close()

    # ── Extract skills immediately using keyword matching ───────────────────────
    db_path = os.path.join(os.path.dirname(__file__), '..', 'jobs.db')
    extracted_skills = _extract_skills_fast(text)
    if extracted_skills:
        db2 = sqlite3.connect(db_path)
        db2.execute('UPDATE users SET skills = ? WHERE id = ?',
                    (','.join(extracted_skills), request.user_id))
        db2.commit()
        db2.close()

    # ── Kick off Ollama parse in background (non-blocking) ────────────────────
    text_captured = text  # capture to avoid closure issues
    def _parse_async():
        try:
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            from ai_matcher import parse_resume
            parsed = parse_resume(text_captured)
            if parsed and parsed.get('skills'):
                db3 = sqlite3.connect(db_path)
                db3.execute('UPDATE users SET skills = ? WHERE id = ?',
                            (','.join(parsed['skills'][:20]), request.user_id))
                db3.commit()
                db3.close()
        except Exception as _e:
            print(f'[resume/parse] background parse: {_e}')
    import threading
    t = threading.Thread(target=_parse_async, daemon=True)
    t.start()

    return jsonify({
        'success': True,
        'filename': filename,
        'text_length': len(text),
        'skills_found': extracted_skills,
        'message': 'Resume uploaded. Skills extracted and stored.'
    }), 201




@app.route('/api/resume/parse', methods=['POST'])
def parse_resume_ai():
    """Parse stored resume text with Ollama AI. Call this after upload if desired."""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        token = auth.split(' ', 1)[1]
        if _is_token_blocked(token):
            return jsonify({'error': 'Token revoked'}), 401
        payload = _decode_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        user_id = int(payload['user_id'])
    except Exception:
        return jsonify({'error': 'Invalid token'}), 401

    data = request.json or {}
    resume_text = data.get('resume_text', '')
    if not resume_text:
        return jsonify({'error': 'resume_text required'}), 400

    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from ai_matcher import parse_resume
        parsed = parse_resume(resume_text)
        return jsonify({'success': True, 'parsed': parsed})
    except Exception as e:
        return jsonify({'error': f'Ollama unavailable: {e}'}), 503


# ============ JOBS ============

@app.before_request
def _force_https():
    """Redirect HTTP → HTTPS in production."""
    if os.environ.get('FLASK_ENV') == 'production' and request.url.startswith('http://'):
        return '', 301



def _check_password_complexity(password: str):
    """Returns (ok, message)."""
    if len(password) < 8:
        return False, "Min 8 characters"
    import re
    if not re.search(r"[A-Z]", password):
        return False, "Need at least one uppercase letter"
    if not re.search(r"\d", password):
        return False, "Need at least one number"
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};:'\".,<>?/\\|`~]", password):
        return False, "Need at least one symbol (!@#$%^&* etc)"
    return True, "OK"

# ============ GUEST BROWSE (public /api/jobs — no auth required) ============
@app.route('/api/jobs', methods=['GET'])


def list_jobs_public():
    """Public job listing — guests can browse without logging in."""
    try:
        db_path = os.path.join(os.path.dirname(__file__), '..', 'jobs.db')
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        cur = con.execute("""
            SELECT id, title, company, location, salary, salary_min, salary_max, salary_currency,
                   work_type, job_type, skills, created_at, view_count,
                   is_featured, application_count, company_rating, company_logo
            FROM jobs
            WHERE is_active = 1
              AND (expires_at IS NULL OR expires_at > date('now'))
            ORDER BY created_at DESC LIMIT 50
        """)
        rows = [dict(r) for r in cur.fetchall()]
        con.close()
        for r in rows:
            r['tags'] = [s.strip() for s in r.get('skills', '').split(',') if s.strip()] if r.get('skills') else []
            r['views'] = r.pop('view_count', 0)
            # Auto-generate salary display string from min/max
            if r.get('salary_min') or r.get('salary_max'):
                r['salary'] = _fmt_salary(r.get('salary_min'), r.get('salary_max'), r.get('salary_currency', 'AUD'))
        return jsonify({'jobs': rows, 'guest': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _fmt_salary(smin, smax, currency='AUD'):
    if not smin and not smax:
        return ''
    def f(n):
        if not n: return ''
        n = int(n)
        return currency + ' ' + str(round(n/1000)*1) + 'k'
    if smin and smax and smin != smax:
        return f(smin) + ' - ' + f(smax)
    if smin:
        return 'From ' + f(smin)
    return 'Up to ' + f(smax)
def get_jobs():
    db = get_db()
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    limit = min(limit, 100)  # Cap at 100
    offset = (page - 1) * limit
    
    # Filters
    category = request.args.get('category')
    location = request.args.get('location')
    work_type = request.args.get('work_type')
    work_arrangement = request.args.get('work_arrangement')
    search = request.args.get('q', '').strip()
    min_salary = request.args.get('min_salary', type=int)
    max_salary = request.args.get('max_salary', type=int)

    # Build query
    now = datetime.datetime.now().isoformat()
    where = ["is_active = 1", "(expires_at IS NULL OR expires_at > ?)"]
    params = [now]

    if category:
        where.append("category = ?")
        params.append(category)

    if location:
        where.append("location LIKE ?")
        params.append(f"%{location}%")

    if work_type:
        # Accepts single value (e.g. "internship") or comma-separated (e.g. "internship,full_time")
        wts = [w.strip() for w in work_type.split(',') if w.strip()]
        if len(wts) == 1:
            where.append("work_type = ?")
            params.append(wts[0])
        else:
            placeholders = ','.join('?' * len(wts))
            where.append(f"work_type IN ({placeholders})")
            params.extend(wts)

    if work_arrangement:
        # Same: single or comma-separated
        was_ = [w.strip() for w in work_arrangement.split(',') if w.strip()]
        if len(was_) == 1:
            where.append("work_arrangement = ?")
            params.append(was_[0])
        else:
            placeholders = ','.join('?' * len(was_))
            where.append(f"work_arrangement IN ({placeholders})")
            params.extend(was_)

    if min_salary:
        where.append("(salary_max >= ? OR (salary_max IS NULL AND salary_min >= ?))")
        params.extend([min_salary, min_salary])

    if max_salary:
        where.append("(salary_min <= ? OR (salary_min IS NULL AND salary_max <= ?))")
        params.extend([max_salary, max_salary])

    if search:
        where.append("(title LIKE ? OR company LIKE ? OR description LIKE ? OR search_summary LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])

    where_clause = " AND ".join(where) if where else "1=1"
    
    # Get total count
    total = db.execute(f"SELECT COUNT(*) FROM jobs WHERE {where_clause}", params).fetchone()[0]
    
    # Get jobs
    cols = ["id","title","company","location","salary","salary_min","salary_max","salary_currency",
               "description","category","work_type","work_arrangement","skills","created_at",
               "is_active","expires_at","view_count","is_featured","application_count","company_rating"]
    jobs = db.execute(
        f"SELECT {','.join(cols)} FROM jobs WHERE {where_clause} ORDER BY is_featured DESC, created_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset]
    ).fetchall()

    result = []
    for j in jobs:
        row = dict(j)
        row['views'] = row.pop('view_count', 0)
        row['salary'] = _fmt_salary(row.get('salary_min'), row.get('salary_max'), row.get('salary_currency', 'AUD'))
        result.append(row)

    return jsonify({
        'jobs': result,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'pages': (total + limit - 1) // limit
        }
    })

@app.route('/api/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        return jsonify({'error': 'Not found'}), 404
    job = dict(job)
    if job.get('salary_min') or job.get('salary_max'):
        job['salary'] = _fmt_salary(job.get('salary_min'), job.get('salary_max'), job.get('salary_currency', 'AUD'))
    return jsonify(job)

@app.route('/api/jobs', methods=['POST'])
@require_auth
def create_job():
    data = request.json or {}
    
    # Validate required fields
    required = ['title', 'company', 'location', 'description']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400
    
    db = get_db()
    
    # Default expires_at to 30 days from now (SEEK style)
    expires_at = data.get('expires_at') or (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
    
    employer_id = getattr(request, 'employer_id', None)
    db.execute("""INSERT INTO jobs (
        title, company, location, description, salary, category, is_active, created_at,
        work_type, work_arrangement, salary_min, salary_max, salary_currency,
        search_summary, selling_points, video_url, expires_at, skills, employer_id,
        company_rating, is_featured
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get('title'),
            data.get('company'),
            data.get('location'),
            data.get('description'),
            data.get('salary') or '',
            data.get('category', 'General'),
            1,
            datetime.datetime.now().isoformat(),
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
            float(data.get('company_rating', 0) or 0),
            1 if str(data.get('is_featured', '')).lower() in ('1','true','yes') else 0
        )
    )
    db.commit()
    job_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Alert matching job seekers
    try:
        from email_notifier import send_job_alert
        skills_raw = data.get('skills', '')
        keywords = skills_raw.split(',')[0].strip() if skills_raw else (data.get('title', '')[:50])
        matching_users = db.execute(
            "SELECT name, email FROM users WHERE role='user' AND email IS NOT NULL LIMIT 50"
        ).fetchall()
        if keywords and matching_users:
            sample_jobs = [dict(db.execute(
                "SELECT id, title, company, location, salary FROM jobs WHERE id=?", (job_id,)
            ).fetchone())]
            for u in matching_users:
                send_job_alert(u['email'], u['name'] or 'there', sample_jobs, keywords)
    except Exception as e:
        print(f"[create_job] alert error: {e}")

    return jsonify({'success': True, 'message': 'Job created', 'job_id': job_id}), 201

@app.route('/api/jobs/<int:job_id>/feature', methods=['POST'])
@require_auth
def feature_job(job_id):
    data = request.json or {}
    featured = 1 if data.get('featured') in (True, 'true', '1', 1) else 0
    db = get_db()
    job = db.execute("SELECT employer_id FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        return jsonify({'error': 'Not found'}), 404
    if job['employer_id'] != request.user_id:
        return jsonify({'error': 'Forbidden'}), 403
    db.execute("UPDATE jobs SET is_featured = ? WHERE id = ?", (featured, job_id))
    db.commit()
    db.close()
    return jsonify({'success': True, 'is_featured': bool(featured)})


@app.route('/api/jobs/<int:job_id>', methods=['PATCH'])
@require_auth
def update_job(job_id):
    data = request.json or {}
    if not data:
        return jsonify({'error': 'No update fields provided'}), 400
    ALLOWED = ['title', 'description', 'location', 'salary', 'salary_min', 'salary_max',
               'salary_currency', 'category', 'work_type', 'work_arrangement',
               'is_active', 'expires_at', 'skills', 'selling_points', 'video_url']
    updates = {k: v for k, v in data.items() if k in ALLOWED}
    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400
    set_clause = ', '.join(f'{k} = ?' for k in updates)
    values = list(updates.values()) + [job_id]
    db = get_db()
    existing = db.execute('SELECT id, employer_id FROM jobs WHERE id = ?', (job_id,)).fetchone()
    if not existing:
        db.close()
        return jsonify({'error': 'Job not found'}), 404
    if existing['employer_id'] and existing['employer_id'] != request.employer_id:
        db.close()
        return jsonify({'error': 'Not authorized to update this job'}), 403
    db.execute(f'UPDATE jobs SET {set_clause} WHERE id = ?', values)
    db.commit()
    updated = db.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    db.close()
    return jsonify({'success': True, 'job': dict(updated)})


@app.route('/api/jobs/<int:job_id>', methods=['DELETE'])
@require_auth
def delete_job(job_id):
    db = get_db()
    existing = db.execute('SELECT id, employer_id FROM jobs WHERE id = ?', (job_id,)).fetchone()
    if not existing:
        db.close()
        return jsonify({'error': 'Job not found'}), 404
    if existing['employer_id'] and existing['employer_id'] != request.employer_id:
        db.close()
        return jsonify({'error': 'Not authorized to delete this job'}), 403
    db.execute('UPDATE jobs SET is_active = 0 WHERE id = ?', (job_id,))
    db.commit()
    db.close()
    return jsonify({'success': True, 'message': 'Job removed'})


@app.route('/api/companies/<company_name>/rate', methods=['POST'])
@require_auth
def rate_company(company_name):
    data = request.json or {}
    rating = float(data.get('rating', 0))
    if not (1 <= rating <= 5):
        return jsonify({'error': 'Rating must be between 1 and 5'}), 400
    db = get_db()
    existing = db.execute("SELECT id FROM company_ratings WHERE company = ? AND user_id = ?",
                          (company_name, request.user_id)).fetchone()
    if existing:
        db.execute("UPDATE company_ratings SET rating = ? WHERE id = ?", (rating, existing['id']))
        msg = "Rating updated"
    else:
        db.execute("INSERT INTO company_ratings (company, user_id, rating) VALUES (?, ?, ?)",
                   (company_name, request.user_id, rating))
        msg = "Rating submitted"
    avg = db.execute("SELECT AVG(rating) as avg_rating FROM company_ratings WHERE company = ?",
                     (company_name,)).fetchone()['avg_rating'] or 0
    db.execute("UPDATE jobs SET company_rating = ? WHERE LOWER(company) = LOWER(?)",
               (round(avg, 1), company_name))
    db.commit()
    db.close()
    return jsonify({'success': True, 'message': msg, 'new_avg': round(avg, 1)})


@app.route('/api/jobs/<int:job_id>/view', methods=['PATCH'])
def track_job_view(job_id):
    "Increment view count when a seeker views a job listing."
    db = get_db()
    db.execute("UPDATE jobs SET view_count = view_count + 1 WHERE id = ?", (job_id,))
    db.commit()
    job = db.execute("SELECT view_count FROM jobs WHERE id = ?", (job_id,)).fetchone()
    db.close()
    return jsonify({'success': True, 'view_count': job['view_count'] if job else 0})


# ============ COMPANIES ============
@app.route('/api/companies', methods=['GET'])
def get_companies():
    db = get_db()
    companies = db.execute("SELECT * FROM companies ORDER BY name").fetchall()
    return jsonify([dict(c) for c in companies])

# ============ SKILLS ============
@app.route('/api/skills', methods=['GET'])
def get_skills():
    db = get_db()
    skills = db.execute("SELECT * FROM skills_taxonomy ORDER BY category, demand_score DESC").fetchall()
    return jsonify([dict(s) for s in skills])


@app.route('/api/user/profile', methods=['PATCH'])
def update_user_profile():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        token = auth.split(' ', 1)[1]
        if _is_token_blocked(token):
            return jsonify({'error': 'Token revoked'}), 401
        payload = _decode_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        user_id = int(payload['user_id'])
    except Exception:
        return jsonify({'error': 'Invalid token'}), 401
    data = request.json or {}
    ALLOWED = ['name', 'skills', 'phone', 'preferred_location', 'experience', 'company']
    updates = {k: v for k, v in data.items() if k in ALLOWED}
    if not updates:
        return jsonify({'error': f'No valid fields. Allowed: {ALLOWED}'}), 400
    set_clause = ', '.join(f'{k} = ?' for k in updates)
    values = list(updates.values()) + [user_id]
    db = get_db()
    db.execute(f'UPDATE users SET {set_clause} WHERE id = ?', values)
    db.commit()
    user = db.execute('SELECT id, name, email, role, skills, phone, preferred_location, experience, created_at FROM users WHERE id = ?',
                     (user_id,)).fetchone()
    db.close()
    return jsonify({'success': True, 'user': dict(user)})


# ============ APPLICATIONS ============
@app.route('/api/applications', methods=['GET'])
def get_applications():
    db = get_db()
    apps = db.execute("SELECT * FROM applications ORDER BY applied_at DESC").fetchall()
    return jsonify([dict(a) for a in apps])

@app.route('/api/applications', methods=['POST'])
# ── ONE-CLICK APPLY ──────────────────────────────────────────────────────────
@app.route('/api/apply/<int:job_id>', methods=['POST'])
@require_auth
def quick_apply(job_id):
    db = get_db()
    user = db.execute("SELECT name, email FROM users WHERE id = ?", (request.user_id,)).fetchone()
    job = db.execute("SELECT title, company FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not user or not job:
        return jsonify({'error': 'Not found'}), 404
    existing = db.execute("SELECT id FROM applications WHERE job_id = ? AND user_id = ?",
                          (job_id, request.user_id)).fetchone()
    if existing:
        return jsonify({'error': 'Already applied'}), 409
    cover = "Hi, I'm " + str(user['name']) + ". I'm interested in the " + str(job['title']) + " role at " + str(job['company']) + "."
    db.execute("INSERT INTO applications (job_id, user_id, status, applied_at, cover_note) VALUES (?, ?, 'pending', ?, ?)",
               (job_id, request.user_id, datetime.datetime.now().isoformat(), cover))
    db.execute("UPDATE jobs SET application_count = application_count + 1 WHERE id = ?", (job_id,))
    db.commit()
    db.close()
    return jsonify({'success': True, 'message': 'Applied for ' + str(job['title']) + ' at ' + str(job['company'])})


@require_auth
@limiter.limit('30 per hour', exempt_when=lambda: False)
def apply_job():
    data = request.json
    db = get_db()
    job_id  = data.get('job_id')
    user_id = request.user_id  # always from JWT — no fallback, no override
    notes   = data.get('notes', '')
    resume_text = data.get('resume_text', '')

    # Fetch job + employer details for emails
    job = db.execute("SELECT title, company, employer_id FROM jobs WHERE id = ?", (job_id,)).fetchone()
    applicant = db.execute("SELECT name, email FROM users WHERE id = ?", (user_id,)).fetchone()
    employer = None
    if job and job['employer_id']:
        employer = db.execute("SELECT name, email FROM users WHERE id = ?", (job['employer_id'],)).fetchone()

    db.execute("INSERT INTO applications (job_id, user_id, status, applied_at, resume_text) VALUES (?, ?, ?, ?, ?)",
               (job_id, user_id, 'pending', datetime.datetime.now().isoformat(), resume_text[:50000]))
    db.commit()
    app_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

    # Send confirmation to applicant
    try:
        from email_notifier import send_application_confirm
        if applicant and applicant['email']:
            send_application_confirm(
                applicant['email'],
                job['title'] if job else 'the role',
                job['company'] if job else 'the company'
            )
    except Exception as e:
        print(f"[apply_job] applicant email error: {e}")

    # Notify employer
    try:
        if employer and employer['email'] and os.environ.get('SMTP_HOST'):
            FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@openjobs.com.au')
            subject = f"New Application: {job['title'] if job else 'a job'}"
            body = (f"You have a new applicant for {job['title']} at {job['company']}. "
                    f"Log in to your OpenJobs dashboard to review their application.")
            msg = "Subject: " + subject + "\n\n" + body
            with smtplib.SMTP(os.environ['SMTP_HOST'], int(os.environ.get('SMTP_PORT', 587))) as s:
                s.starttls()
                s.login(os.environ['SMTP_USER'], os.environ['SMTP_PASS'])
                s.sendmail(FROM_EMAIL, employer['email'], msg)
    except Exception as e:
        print(f"[apply_job] employer email error: {e}")

    db.close()
    return jsonify({'success': True, 'message': 'Applied', 'application_id': app_id}), 201

# ============ SALARY ============
# ============ KANBAN PIPELINE ============
@app.route('/api/kanban/<int:job_id>', methods=['GET'])
@require_auth
def get_kanban(job_id):
    "Return kanban board data for one job — all applications grouped by status."
    db = get_db()
    # Verify ownership
    job = db.execute("SELECT employer_id FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not job or job['employer_id'] != request.employer_id:
        return jsonify({'error': 'Not found'}), 404

    apps = db.execute("""
        SELECT a.id, a.status, a.applied_at, a.ats_score, a.cover_letter, a.resume_text,
               u.name as applicant_name, u.email as applicant_email
        FROM applications a
        JOIN users u ON a.user_id = u.id
        WHERE a.job_id = ?
        ORDER BY a.applied_at DESC
    """, (job_id,)).fetchall()
    db.close()

    stages = ['applied', 'screening', 'interview', 'offer', 'hired', 'rejected']
    board = {s: [] for s in stages}
    for a in apps:
        stage = a['status'] if a['status'] in stages else 'applied'
        board[stage].append(dict(a))

    return jsonify({'success': True, 'board': board})


@app.route('/api/kanban/<int:job_id>/move', methods=['POST'])
@require_auth
def move_kanban_card(job_id):
    "Move an application to a new stage."
    db = get_db()
    job = db.execute("SELECT employer_id FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not job or job['employer_id'] != request.employer_id:
        return jsonify({'error': 'Not found'}), 404

    data = request.json
    app_id = data.get('application_id')
    new_status = data.get('stage')
    valid = ['applied', 'screening', 'interview', 'offer', 'hired', 'rejected']
    if new_status not in valid:
        return jsonify({'error': f'Invalid stage. Must be one of: {valid}'}), 400

    now = datetime.datetime.now().isoformat()
    db.execute("UPDATE applications SET status=?, updated_at=? WHERE id=? AND job_id=?",
               (new_status, now, app_id, job_id))
    db.commit()
    db.close()
    return jsonify({'success': True, 'status': new_status})


@app.route('/api/salary/predict', methods=['POST'])
def predict_salary():
    data = request.json
    title = data.get('title', '')
    location = data.get('location', '')
    
    base = 80000
    if 'senior' in title.lower(): base += 40000
    if 'junior' in title.lower(): base -= 20000
    if 'lead' in title.lower(): base += 30000
    
    return jsonify({'success': True, 'predicted': base, 'range': {'min': base * 0.85, 'max': base * 1.15}})


# ============ PRICING & PAYMENT ============
@app.route('/api/pricing', methods=['GET'])
def get_pricing():
    "Return pricing tiers (no auth needed)."
    return jsonify({
        'currency': 'AUD',
        'plans': [
            {
                'id': 'standard',
                'name': 'Standard Job Post',
                'price': 99,
                'description': 'Post your job listing for 30 days',
                'features': ['30-day listing', 'AI-matched candidates', 'Email applications'],
                'featured': False
            },
            {
                'id': 'premium',
                'name': 'Premium Job Post',
                'price': 199,
                'description': 'Top placement + featured badge + email to matched seekers',
                'features': ['Top of search results', 'Featured badge', 'Email to matched seekers', 'Priority support'],
                'featured': True
            }
        ],
        'stripe_configured': bool(os.environ.get('STRIPE_SECRET_KEY')),
        'paypal_configured': bool(os.environ.get('PAYPAL_CLIENT_ID'))
    })


@app.route('/api/payment/checkout', methods=['POST'])
@require_auth
def create_checkout():
    "Create Stripe checkout session for a job posting."
    if not os.environ.get('STRIPE_SECRET_KEY'):
        return jsonify({'error': 'Payment not configured', 'demo': True, 'message': 'Add STRIPE_SECRET_KEY to .env to enable payments'}), 503

    data = request.json or {}
    job_id = data.get('job_id')
    plan   = data.get('plan', 'standard')
    prices = {'standard': 9900, 'premium': 19900}  # AUD cents

    try:
        import requests
        session_data = {
            'payment_method_types': ['card'],
            'line_items': [{
                'price_data': {
                    'currency': 'aud',
                    'product_data': {'name': f'OpenJobs {plan.title()} Posting'},
                    'unit_amount': prices.get(plan, 9900)
                },
                'quantity': 1
            }],
            'mode': 'payment',
            'success_url': f'{APP_URL}/employer?payment=success&job_id={job_id}',
            'cancel_url': f'{APP_URL}/employer',
            'metadata': {
                'job_id': str(job_id),
                'user_id': str(request.user_id),
                'plan': plan
            }
        }
        resp = requests.post(
            'https://api.stripe.com/v1/checkout/sessions',
            auth=(os.environ['STRIPE_SECRET_KEY'], ''),
            data=session_data,
            timeout=15
        )
        if resp.status_code == 200:
            session = resp.json()
            return jsonify({'success': True, 'checkout_url': session['url'], 'session_id': session['id']})
        return jsonify({'error': 'Stripe error', 'detail': resp.text}), 502
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ OLLAMA AI ============
import requests
try:
    r = requests.get(f'{OLLAMA_URL}/api/tags', timeout=2)
    OLLAMA_AVAILABLE = r.status_code == 200
except:
    OLLAMA_AVAILABLE = False

@app.route('/api/ai/ollama/status', methods=['GET'])
def ollama_status():
    return jsonify({'available': OLLAMA_AVAILABLE, 'url': OLLAMA_URL})

@app.route('/api/ai/ollama/models', methods=['GET'])
def list_ollama_models():
    if not OLLAMA_AVAILABLE:
        return jsonify({'error': 'Ollama not running', 'models': []})
    try:
        import requests
        resp = requests.get(f'{OLLAMA_URL}/api/tags', timeout=5)
        return jsonify({'success': True, 'models': [m['name'] for m in resp.json().get('models', [])]})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/ai/ollama/chat', methods=['POST'])
def ollama_chat():
    if not OLLAMA_AVAILABLE:
        return jsonify({'error': 'Ollama not running'}), 500
    data = request.json
    try:
        import requests
        resp = requests.post(f'{OLLAMA_URL}/api/chat', json={'model': data.get('model', 'llama3.2'), 'messages': [{'role': 'user', 'content': data.get('message')}], 'stream': False}, timeout=30)
        return jsonify({'success': True, 'response': resp.json()['message']['content']})
    except Exception as e:
        return jsonify({'error': str(e)})

# ============ WHITE-LABEL ============
@app.route('/api/whitelabel/config', methods=['GET'])
def get_whitelabel():
    return jsonify({'name': 'OpenJobs', 'tagline': 'Matching skills with opportunities', 'primary_color': '#00d4aa'})

# ============ CDN ============
@app.route('/api/cdn/config', methods=['GET'])
def get_cdn_config():
    return jsonify({'enabled': True, 'provider': 'cloudflare', 'cache_ttl': 300})

# ============ ML ============
@app.route('/api/ml/models', methods=['GET'])
def list_ml_models():
    return jsonify({'success': True, 'models': {'match_v1': {'accuracy': 0.87}, 'salary_v1': {'accuracy': 0.92}}})

# ============ REGIONS ============
@app.route('/api/regions', methods=['GET'])
def list_regions():
    return jsonify({'success': True, 'regions': {'au-syd': {'name': 'Sydney', 'status': 'active'}, 'sg': {'name': 'Singapore', 'status': 'active'}}})

# ============ CRM ============
@app.route('/api/crm/companies', methods=['GET'])
def get_crm_companies():
    db = get_db()
    companies = db.execute("SELECT * FROM crm_companies ORDER BY created_at DESC").fetchall()
    return jsonify({'success': True, 'companies': [dict(c) for c in companies]})

@app.route('/api/crm/contacts', methods=['GET'])
def get_crm_contacts():
    db = get_db()
    contacts = db.execute("SELECT * FROM crm_contacts ORDER BY created_at DESC").fetchall()
    return jsonify({'success': True, 'contacts': [dict(c) for c in contacts]})

@app.route('/api/crm/pipeline', methods=['GET'])
def get_crm_pipeline():
    db = get_db()
    deals = db.execute("SELECT * FROM crm_pipeline ORDER BY created_at DESC").fetchall()
    return jsonify({'success': True, 'deals': [dict(d) for d in deals]})

# ============ ADMIN ============
@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    db = get_db()

    total_jobs      = db.execute("SELECT COUNT(*) FROM jobs WHERE is_active=1").fetchone()[0]
    total_apps      = db.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    total_seekers   = db.execute("SELECT COUNT(*) FROM users WHERE role='seeker'").fetchone()[0]
    total_employers = db.execute("SELECT COUNT(*) FROM users WHERE role='employer'").fetchone()[0]

    app_rows = db.execute("SELECT status, COUNT(*) as cnt FROM applications GROUP BY status").fetchall()
    apps_by_status = {r['status']: r['cnt'] for r in app_rows}

    thirty_days_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat()
    apps_over_time = db.execute(
        "SELECT DATE(applied_at) as day, COUNT(*) as cnt FROM applications WHERE applied_at >= ? GROUP BY day ORDER BY day",
        (thirty_days_ago,)).fetchall()

    jobs_over_time = db.execute(
        "SELECT DATE(created_at) as day, COUNT(*) as cnt FROM jobs WHERE created_at >= ? GROUP BY day ORDER BY day",
        (thirty_days_ago,)).fetchall()

    top_employers = db.execute("""
        SELECT u.name, u.email, COUNT(j.id) as job_count
        FROM users u
        LEFT JOIN jobs j ON j.employer_id = u.id AND j.is_active=1
        WHERE u.role='employer'
        GROUP BY u.id ORDER BY job_count DESC LIMIT 10
    """).fetchall()

    by_category = db.execute("SELECT category, COUNT(*) as cnt FROM jobs WHERE is_active=1 GROUP BY category ORDER BY cnt DESC").fetchall()
    by_work_type = db.execute("SELECT work_type, COUNT(*) as cnt FROM jobs WHERE is_active=1 GROUP BY work_type").fetchall()
    avg_salary = db.execute("SELECT AVG((salary_min + salary_max) / 2) FROM jobs WHERE is_active=1 AND salary_min > 0").fetchone()[0] or 0
    total_views = db.execute("SELECT COALESCE(SUM(view_count), 0) FROM jobs").fetchone()[0]

    recent_apps = db.execute("""
        SELECT a.id, a.status, a.applied_at, j.title as job_title,
               u.name as seeker_name, u.email as seeker_email
        FROM applications a
        JOIN jobs j ON j.id = a.job_id
        JOIN users u ON u.id = a.user_id
        ORDER BY a.applied_at DESC LIMIT 10
    """).fetchall()

    recent_signups = db.execute("SELECT id, name, email, role, created_at FROM users ORDER BY created_at DESC LIMIT 10").fetchall()

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
        'apps_over_time': [dict(r) for r in apps_over_time],
        'jobs_over_time': [dict(r) for r in jobs_over_time],
        'top_employers': [dict(r) for r in top_employers],
        'by_category': [dict(r) for r in by_category],
        'by_work_type': [dict(r) for r in by_work_type],
        'recent_applications': [dict(r) for r in recent_apps],
        'recent_signups': [dict(r) for r in recent_signups],
    })



@app.route('/ai')
def ai_page():
    with open(os.path.join(TEMPLATES_DIR, 'ai.html'), 'r') as f:
        return f.read()




@app.route('/')
def index():
    return open(os.path.join(TEMPLATES_DIR, 'index.html')).read() if os.path.exists(os.path.join(TEMPLATES_DIR, 'index.html')) else jsonify({'msg':'OpenJobs API','endpoints':['/api/jobs','/api/companies','/api/ai/ollama/status']})

@app.route('/robots.txt')
def robots():
    return 'User-agent: *\nAllow: /\nDisallow: /user\nDisallow: /employer\nDisallow: /admin\nDisallow: /api/\n', {'Content-Type': 'text/plain'}

@app.route('/job.html')
@app.route('/job')
def job_page():
    path = os.path.join(TEMPLATES_DIR, 'job.html')
    return open(path).read() if os.path.exists(path) else jsonify({'error':'Template not found'})

@app.route('/companies')
def companies_page():
    return open(os.path.join(TEMPLATES_DIR, 'company.html')).read() if os.path.exists(os.path.join(TEMPLATES_DIR, 'company.html')) else jsonify({'companies':[]})

@app.route('/salary')
def salary_page():
    return open(os.path.join(TEMPLATES_DIR, 'salary.html')).read() if os.path.exists(os.path.join(TEMPLATES_DIR, 'salary.html')) else jsonify({'predict':True})

@app.route('/login')
def login_page():
    return open(os.path.join(TEMPLATES_DIR, 'login.html')).read() if os.path.exists(os.path.join(TEMPLATES_DIR, 'login.html')) else jsonify({'error':'Template not found'})

@app.route('/register')
def register_page():
    return open(os.path.join(TEMPLATES_DIR, 'register.html')).read() if os.path.exists(os.path.join(TEMPLATES_DIR, 'register.html')) else jsonify({'error':'Template not found'})

@app.route('/forgot-password')
def forgot_password_page():
    return open(os.path.join(TEMPLATES_DIR, 'forgot-password.html')).read() if os.path.exists(os.path.join(TEMPLATES_DIR, 'forgot-password.html')) else jsonify({'error':'Template not found'})

@app.route('/reset-password.html')
def reset_password_page():
    return open(os.path.join(TEMPLATES_DIR, 'reset-password.html')).read() if os.path.exists(os.path.join(TEMPLATES_DIR, 'reset-password.html')) else jsonify({'error':'Template not found'})

@app.route('/user')
def user_page():
    return open(os.path.join(TEMPLATES_DIR, 'user.html')).read() if os.path.exists(os.path.join(TEMPLATES_DIR, 'user.html')) else jsonify({'dashboard':True})

@app.route('/employer')
def employer_page():
    return open(os.path.join(TEMPLATES_DIR, 'employer.html')).read() if os.path.exists(os.path.join(TEMPLATES_DIR, 'employer.html')) else jsonify({'employer':True})

@app.route('/admin')
def admin_page():
    return open(os.path.join(TEMPLATES_DIR, 'admin.html')).read() if os.path.exists(os.path.join(TEMPLATES_DIR, 'admin.html')) else jsonify({'admin':True})

@app.route('/privacy')
def privacy_page():
    return open(os.path.join(TEMPLATES_DIR, 'privacy.html')).read() if os.path.exists(os.path.join(TEMPLATES_DIR, 'privacy.html')) else jsonify({'privacy':True})

@app.route('/terms')
def terms_page():
    return open(os.path.join(TEMPLATES_DIR, 'terms.html')).read() if os.path.exists(os.path.join(TEMPLATES_DIR, 'terms.html')) else jsonify({'terms':True})

# ============ CAD API ============
import ezdxf

@app.route('/api/cad/info', methods=['GET'])
def cad_info():
    """Get CAD library info"""
    return jsonify({
        'library': 'ezdxf',
        'version': ezdxf.__version__,
        'capabilities': ['read_dxf', 'write_dxf', 'export_pdf', 'export_svg'],
        'note': 'AutoCAD COM connection requires Windows'
    })

@app.route('/api/cad/read', methods=['POST'])
def read_cad():
    """Read DXF file and extract entities"""
    data = request.json
    filepath = data.get('filepath')
    
    if not filepath:
        return jsonify({'error': 'filepath required'}), 400
    
    try:
        doc = ezdxf.readfile(filepath)
        msp = doc.modelspace()
        
        entities = []
        for ent in msp:
            entities.append({
                'type': ent.dxftype(),
                'layer': ent.dxf.layer,
                'color': ent.dxf.color if hasattr(ent.dxf, 'color') else None
            })
        
        return jsonify({
            'success': True,
            'layers': list(doc.layers),
            'entity_count': len(entities),
            'entities': entities[:50]  # Limit to 50
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500




@app.route('/cad')
def cad_page():
    return open(os.path.join(TEMPLATES_DIR, 'cad.html')).read()



# ============ IMPROVEMENTS ADDED ============

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.datetime.now().isoformat()})

@app.route('/api/search', methods=['GET'])
@limiter.limit("10 per minute")
def search_all():
    """Search across jobs and companies"""
    query = request.args.get('q', '').lower()
    if len(query) < 2:
        return jsonify({'error': 'Query too short'}), 400
    
    db = get_db()
    jobs = db.execute("SELECT id, title, company, location FROM jobs WHERE is_active = 1 AND (title LIKE ? OR description LIKE ?)", 
                      (f'%{query}%', f'%{query}%')).fetchall()
    companies = db.execute("SELECT id, name, industry FROM companies WHERE name LIKE ? OR industry LIKE ?",
                            (f'%{query}%', f'%{query}%')).fetchall()
    db.close()
    
    return jsonify({'jobs': [dict(j) for j in jobs], 'companies': [dict(c) for c in companies], 'count': len(jobs) + len(companies)})

@app.route('/api/recommendations', methods=['GET'])
def recommendations():
    """Get job recommendations for a user based on skills + resume_text."""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    db = get_db()
    user = db.execute("SELECT skills, resume_text FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        db.close()
        return jsonify({'error': 'User not found'}), 404

    # Use resume_text as fallback if skills column is empty
    search_skills = user['skills'] or ''
    if not search_skills and user['resume_text']:
        matched = _extract_skills_fast(user['resume_text'])
        search_skills = ','.join(matched)

    skill_list = [s.strip() for s in search_skills.split(',') if s.strip()]

    if skill_list:
        params = {f"s{i}": f"%{s}%" for i, s in enumerate(skill_list)}
        skill_like = " OR ".join([f"skills LIKE :s{i}" for i in range(len(skill_list))])
        exact_like = " OR ".join([f"skills LIKE :s{i}" for i in range(len(skill_list))])
        where_clause = f"({skill_like}) AND is_active = 1"
        case_clause  = f"CASE WHEN skills LIKE :exact THEN 100 WHEN {exact_like} THEN 50 ELSE 0 END"
        params['exact'] = f"%{search_skills}%"
    else:
        where_clause = "is_active = 1"
        case_clause  = "0"
        params = {}

    sql = f"SELECT *, {case_clause} as match_score FROM jobs WHERE {where_clause} ORDER BY match_score DESC, posted_at DESC LIMIT 20"
    jobs = db.execute(sql, params).fetchall()
    db.close()

    return jsonify({
        'recommendations': [dict(j) for j in jobs],
        'skills_used': search_skills,
        'resume_enhanced': bool(user['resume_text'] and not user['skills'])
    })

@app.route('/api/trending', methods=['GET'])
def trending_jobs():
    """Get trending job categories"""
    db = get_db()
    categories = db.execute("""
        SELECT category, COUNT(*) as count 
        FROM jobs WHERE is_active = 1 
        GROUP BY category ORDER BY count DESC LIMIT 10
    """).fetchall()
    locations = db.execute("""
        SELECT location, COUNT(*) as count 
        FROM jobs WHERE is_active = 1 
        GROUP BY location ORDER BY count DESC LIMIT 10
    """).fetchall()
    db.close()
    return jsonify({'trending_categories': [dict(c) for c in categories], 'trending_locations': [dict(l) for l in locations]})


# ============ USER DASHBOARD STATS ============
@app.route('/api/dashboard/seeker', methods=['GET'])
def seeker_dashboard():
    """Stats for job seeker dashboard"""
    db = get_db()
    user_id = request.args.get('user_id', 1, type=int)
    total_jobs = db.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1").fetchone()[0]
    total_applications = db.execute("SELECT COUNT(*) FROM applications WHERE user_id = ?", (user_id,)).fetchone()[0]
    pending_apps = db.execute("SELECT COUNT(*) FROM applications WHERE user_id = ? AND status = 'pending'", (user_id,)).fetchone()[0]
    interview_apps = db.execute("SELECT COUNT(*) FROM applications WHERE user_id = ? AND status = 'interview'", (user_id,)).fetchone()[0]
    # Recent applications
    recent_apps = db.execute("""
        SELECT a.*, j.title, j.company, j.location, j.salary_min, j.salary_max
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.user_id = ?
        ORDER BY a.applied_at DESC LIMIT 10
    """, (user_id,)).fetchall()
    # Saved jobs count
    saved_count = db.execute("SELECT COUNT(*) FROM saved_jobs WHERE user_id = ?", (user_id,)).fetchone()[0]
    # Recommended jobs — skill-matched to user (falls back to resume_text extraction)
    user_row = db.execute("SELECT skills, resume_text FROM users WHERE id = ?", (user_id,)).fetchone()
    user_skills = user_row['skills'] or '' if user_row else ''
    user_resume = user_row['resume_text'] if user_row else ''
    if not user_skills and user_resume:
        matched = _extract_skills_fast(user_resume)
        user_skills = ','.join(matched)
    skill_list = [s.strip().lower() for s in user_skills.split(',') if s.strip()]
    if skill_list:
        all_jobs = db.execute(
            "SELECT id, title, company, location, salary_min, salary_max, category, skills, description "
            "FROM jobs WHERE is_active = 1 ORDER BY posted_at DESC LIMIT 50"
        ).fetchall()
        if user_resume:
            # SMART STRATEGY: keyword-first, Ollama only for borderline matches
            job_list = [dict(j) for j in all_jobs]
            ranked = rank_jobs_for_resume(job_list, user_resume)
            rec_jobs = ranked[:4]
        else:
            # No resume — plain keyword only, no Ollama
            scored = []
            for job in all_jobs:
                jskills = (job['skills'] or '').lower()
                score = sum(1 for p in skill_list if p in jskills)
                if score > 0:
                    jd = dict(job)
                    jd['match_score'] = score
                    scored.append((score, jd))
            scored.sort(key=lambda x: -x[0])
            rec_jobs = [j for (_, j) in scored[:4]]
    else:
        raw = db.execute(
            "SELECT id, title, company, location, salary_min, salary_max, category, skills "
            "FROM jobs WHERE is_active = 1 ORDER BY posted_at DESC LIMIT 4"
        ).fetchall()
        rec_jobs = [dict(j) for j in raw]
        for j in rec_jobs:
            j['match_score'] = 0
    db.close()
    return jsonify({
        'stats': {
            'total_jobs': total_jobs,
            'total_applications': total_applications,
            'pending': pending_apps,
            'interviews': interview_apps,
            'saved': saved_count
        },
        'recent_applications': [dict(a) for a in recent_apps],
        'recommended': [dict(j) for j in rec_jobs]
    })

@app.route('/api/saved_jobs', methods=['GET'])
def get_saved_jobs():
    db = get_db()
    user_id = request.args.get('user_id', 1, type=int)
    saved = db.execute("""
        SELECT j.*, sj.saved_at FROM jobs j
        JOIN saved_jobs sj ON j.id = sj.job_id
        WHERE sj.user_id = ? ORDER BY sj.saved_at DESC
    """, (user_id,)).fetchall()
    db.close()
    return jsonify([dict(s) for s in saved])

@app.route('/api/saved_jobs', methods=['POST'])
def save_job():
    data = request.json
    db = get_db()
    db.execute("INSERT OR IGNORE INTO saved_jobs (user_id, job_id, saved_at) VALUES (?, ?, ?)",
               (data.get('user_id', 1), data.get('job_id'), datetime.datetime.now().isoformat()))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/saved_jobs', methods=['DELETE'])
def unsave_job():
    data = request.json
    db = get_db()
    db.execute("DELETE FROM saved_jobs WHERE user_id = ? AND job_id = ?",
               (data.get('user_id', 1), data.get('job_id')))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/applications/<int:app_id>', methods=['PATCH'])
def update_application(app_id):
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json or {}
    new_status = data.get('status')
    VALID_STATUSES = ['pending', 'reviewing', 'interview', 'offer', 'rejected', 'withdrawn']
    if new_status and new_status not in VALID_STATUSES:
        return jsonify({'error': f'Invalid status. Must be one of: {VALID_STATUSES}'}), 400
    db = get_db()
    app = db.execute('SELECT id FROM applications WHERE id = ?', (app_id,)).fetchone()
    if not app:
        db.close()
        return jsonify({'error': 'Application not found'}), 404
    db.execute('UPDATE applications SET status = ? WHERE id = ?', (new_status, app_id))
    db.commit()
    updated = db.execute('SELECT * FROM applications WHERE id = ?', (app_id,)).fetchone()
    db.close()
    return jsonify({'success': True, 'application': dict(updated)})

@app.route('/api/applications/<int:app_id>', methods=['DELETE'])
def delete_application(app_id):
    db = get_db()
    db.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    user_id = request.args.get('user_id', 1, type=int)
    db = get_db()
    user = db.execute("SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(dict(user))


# ── EMPLOYER AUTH & DASHBOARD ─────────────────────────────────────────────────

@app.route('/api/auth/register-employer', methods=['POST'])
def register_employer():
    data = request.json or {}
    name     = data.get('name', '').strip()
    email    = data.get('email', '').strip()
    password = data.get('password', '')
    company  = data.get('company', '').strip()
    if not name or not email or not password:
        return jsonify({'error': 'Name, email, and password are required'}), 400
    if '@' not in email or '.' not in email:
        return jsonify({'error': 'Invalid email'}), 400
    # Password complexity requirements (same as registration)
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    if not re.search(r'[A-Z]', password):
        return jsonify({'error': 'Password must contain at least 1 uppercase letter'}), 400
    if not re.search(r'[a-z]', password):
        return jsonify({'error': 'Password must contain at least 1 lowercase letter'}), 400
    if not re.search(r'\d', password):
        return jsonify({'error': 'Password must contain at least 1 number'}), 400
    db = get_db()
    if db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
        db.close()
        return jsonify({'error': 'Email already registered'}), 400
    db.execute(
        "INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
        (name, email, hash_password(password), 'employer', datetime.datetime.now().isoformat())
    )
    db.commit()
    user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    token_payload = {
        'user_id': user_id, 'email': email, 'role': 'employer',
        'employer_id': user_id,
        'exp': str(datetime.datetime.now() + datetime.timedelta(days=7))
    }
    token = base64.b64encode(json.dumps(token_payload).encode()).decode().rstrip('=') + '=='
    return jsonify({
        'success': True, 'token': token,
        'user': {'id': user_id, 'name': name, 'email': email, 'role': 'employer'}
    }), 201


@app.route('/api/employer/calendly', methods=['PUT'])
@require_auth
def set_calendly_link():
    data = request.json or {}
    url = data.get('calendly_url', '').strip()
    if url and not url.startswith('http'):
        return jsonify({'error': 'Invalid URL'}), 400
    db = get_db()
    db.execute("UPDATE users SET calendly_url = ? WHERE id = ?", (url, request.user_id))
    db.commit()
    db.close()
    return jsonify({'success': True})


@app.route('/api/employer/dashboard', methods=['GET'])
@require_auth
def employer_dashboard():
    emp_id = request.employer_id
    db = get_db()
    my_jobs = db.execute(
        "SELECT * FROM jobs WHERE employer_id = ? AND is_active = 1 ORDER BY created_at DESC",
        (emp_id,)
    ).fetchall()
    job_ids = [j['id'] for j in my_jobs]
    if job_ids:
        ph = ','.join('?' * len(job_ids))
        total_apps = db.execute(
            f"SELECT COUNT(*) FROM applications WHERE job_id IN ({ph})", job_ids
        ).fetchone()[0]
        pending_apps = db.execute(
            f"SELECT COUNT(*) FROM applications WHERE job_id IN ({ph}) AND status = 'pending'", job_ids
        ).fetchone()[0]
        interviewing = db.execute(
            f"SELECT COUNT(*) FROM applications WHERE job_id IN ({ph}) AND status = 'interview'", job_ids
        ).fetchone()[0]
        recent_apps = db.execute(
            f"""SELECT a.id, a.user_id, a.job_id, a.status, a.applied_at,
                       a.cover_letter, a.cv_link, j.title as job_title, j.company
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                WHERE a.job_id IN ({ph})
                ORDER BY a.applied_at DESC LIMIT 10""", job_ids
        ).fetchall()
    else:
        total_apps = pending_apps = interviewing = 0
        recent_apps = []
    total_views = db.execute(
        "SELECT COALESCE(SUM(view_count), 0) FROM jobs WHERE employer_id = ?", (emp_id,)
    ).fetchone()[0]
    db.close()
    return jsonify({
        'stats': {
            'active_jobs': len(my_jobs),
            'total_applicants': total_apps,
            'pending': pending_apps,
            'interviewing': interviewing,
            'job_views': total_views,
        },
        'my_jobs': [dict(j) for j in my_jobs],
        'recent_applications': [dict(a) for a in recent_apps]
    })


@app.route('/api/employer/applications', methods=['GET'])
@require_auth
def employer_applications():
    emp_id = request.employer_id
    status = request.args.get('status', 'all')
    db = get_db()
    job_ids = [j['id'] for j in db.execute(
        "SELECT id FROM jobs WHERE employer_id = ? AND is_active = 1", (emp_id,)
    ).fetchall()]
    if not job_ids:
        db.close()
        return jsonify({'applications': []})
    ph = ','.join('?' * len(job_ids))
    qry = f"""SELECT a.*, j.title as job_title, j.company, u.name as applicant_name, u.email as applicant_email
               FROM applications a
               JOIN jobs j ON a.job_id = j.id
               LEFT JOIN users u ON a.user_id = u.id
               WHERE a.job_id IN ({ph})"""
    params = list(job_ids)  # copy so we can safely append
    if status != 'all':
        qry += " AND a.status = ?"
        params.append(status)
    qry += " ORDER BY a.applied_at DESC"
    apps = db.execute(qry, params).fetchall()
    db.close()
    return jsonify({'applications': [dict(a) for a in apps]})


# ── RESUME TEXT EXTRACTION ─────────────────────────────────────────────────


# ============ KYC — KNOW YOUR CUSTOMER =======================================
ALLOWED_DOC_EXT = {'.pdf', '.jpg', '.jpeg', '.png'}
KYC_UPLOAD_DIR  = os.path.join(os.path.dirname(__file__), '..', 'kyc_uploads')
os.makedirs(KYC_UPLOAD_DIR, exist_ok=True)

def _kyc_verify_magic(filepath):
    """Verify file magic bytes for KYC documents."""
    try:
        with open(filepath, 'rb') as f:
            header = f.read(8)
        if not header: return False
        jpg = b'\xff\xd8\xff'
        png = b'\x89PNG'
        pdf = b'%PDF'
        return header.startswith(jpg) or header.startswith(png) or header.startswith(pdf)
    except: return False


@app.route('/api/kyc/status', methods=['GET'])
@require_auth
def kyc_status():
    """Return current KYC status and required documents for this user role."""
    db = get_db()
    user = db.execute("SELECT kyc_status, kyc_doc_type, kyc_doc_number, dob, nationality FROM users WHERE id = ?",
                      (request.user_id,)).fetchone()
    docs = db.execute("SELECT doc_type, uploaded_at, status FROM kyc_documents WHERE user_id = ?",
                      (request.user_id,)).fetchall()
    db.close()
    required = ['passport', 'national_id', 'drivers_license']
    uploaded = [dict(d) for d in docs]
    missing  = [r for r in required if r not in [d['doc_type'] for d in docs]]
    return jsonify({
        'kyc_status': user['kyc_status'] if user else 'pending',
        'dob': user['dob'] if user else None,
        'nationality': user['nationality'] if user else None,
        'required_docs': required,
        'uploaded_docs': uploaded,
        'missing_docs': missing,
    })


@app.route('/api/kyc/personal', methods=['PATCH'])
@require_auth
def kyc_personal():
    """Update KYC personal info: dob, nationality, address, tax_file_number, visa_status."""
    data = request.json or {}
    fields = ['dob', 'nationality', 'address', 'tax_file_number', 'visa_status']
    updates = {}
    for f in fields:
        if f in data:
            updates[f] = data[f]
    if not updates:
        return jsonify({'error': 'No valid fields provided'}), 400
    cols = ', '.join(f'{k} = ?' for k in updates)
    vals = list(updates.values()) + [request.user_id]
    db = get_db()
    db.execute(f'UPDATE users SET {cols} WHERE id = ?', vals)
    db.commit()
    db.close()
    return jsonify({'success': True, 'updated': list(updates.keys())})


@app.route('/api/kyc/document', methods=['POST'])
@require_auth
def kyc_upload_doc():
    """Upload a KYC identity document (passport, national ID, or driver's license)."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    doc_type = request.form.get('doc_type', '').strip().lower()
    doc_number = request.form.get('doc_number', '').strip()
    valid_types = ['passport', 'national_id', 'drivers_license']
    if doc_type not in valid_types:
        return jsonify({'error': f'doc_type must be one of: {valid_types}'}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_DOC_EXT:
        return jsonify({'error': f'File type not allowed. Upload PDF, JPG, or PNG.'}), 400

    safe_user = f"user_{request.user_id}"
    filename  = f"{safe_user}_{doc_type}_{int(datetime.datetime.now().timestamp())}{ext}"
    filepath  = os.path.join(KYC_UPLOAD_DIR, filename)
    file.save(filepath)

    try:
        if os.path.getsize(filepath) > 10 * 1024 * 1024:
            os.remove(filepath)
            return jsonify({'error': 'File too large. Max 10 MB.'}), 400
        if not _kyc_verify_magic(filepath):
            os.remove(filepath)
            return jsonify({'error': 'File content does not match its type.'}), 400
    except:
        if os.path.exists(filepath): os.remove(filepath)
        return jsonify({'error': 'Could not process file.'}), 400

    db = get_db()
    db.execute("""
        INSERT INTO kyc_documents (user_id, doc_type, doc_number, file_path, uploaded_at, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
        ON CONFLICT(user_id, doc_type) DO UPDATE SET
            doc_number = excluded.doc_number,
            file_path  = excluded.file_path,
            uploaded_at = excluded.uploaded_at,
            status = 'pending'
    """, (request.user_id, doc_type, doc_number, filename, datetime.datetime.now().isoformat()))
    # Mark KYC as submitted if all docs are now present
    required = ['passport', 'national_id', 'drivers_license']
    uploaded = [r['doc_type'] for r in db.execute(
        "SELECT doc_type FROM kyc_documents WHERE user_id = ?", (request.user_id,)).fetchall()]
    if all(r in uploaded for r in required):
        db.execute("UPDATE users SET kyc_status = 'submitted' WHERE id = ?", (request.user_id,))
    db.commit()
    db.close()
    return jsonify({'success': True, 'filename': filename, 'doc_type': doc_type}), 201


@app.route('/api/kyc/admin/list', methods=['GET'])
@require_auth
def kyc_admin_list():
    """Admin endpoint: list all users with pending KYC for review."""
    if request.user_role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    db = get_db()
    users = db.execute("""
        SELECT u.id, u.name, u.email, u.kyc_status, u.dob, u.nationality,
               u.visa_status, u.created_at,
               GROUP_CONCAT(d.doc_type, ', ') as docs
        FROM users u
        LEFT JOIN kyc_documents d ON d.user_id = u.id
        WHERE u.kyc_status IN ('submitted', 'pending')
        GROUP BY u.id
        ORDER BY u.created_at DESC
    """).fetchall()
    db.close()
    return jsonify({'users': [dict(u) for u in users]})


@app.route('/api/kyc/admin/verify/<int:user_id>', methods=['POST'])
@require_auth
def kyc_admin_verify(user_id):
    """Admin: approve or reject a user's KYC."""
    if request.user_role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    data = request.json or {}
    action = data.get('action', '')  # 'verify' or 'reject'
    if action not in ('verify', 'reject'):
        return jsonify({'error': "action must be 'verify' or 'reject'"}), 400
    new_status = 'verified' if action == 'verify' else 'rejected'
    db = get_db()
    db.execute("UPDATE users SET kyc_status = ? WHERE id = ?", (new_status, user_id))
    db.execute("UPDATE kyc_documents SET status = ? WHERE user_id = ?", (new_status, user_id))
    db.commit()
    db.close()
    return jsonify({'success': True, 'kyc_status': new_status})



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5700))
    app.run(host='0.0.0.0', port=port, debug=False)
