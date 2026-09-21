#!/usr/bin/env python3
"""
Admin API — everything an operator needs to run the board day to day.

Registered from server.py via `init_admin(app, ...)` so it can reuse the app's
request-scoped DB connection and auth decorators without a circular import.

Endpoints (all require an admin JWT):
  GET    /api/admin/overview            KPIs, 30-day trends, breakdowns, recent activity, attention items
  GET    /api/admin/users               search / filter / paginate users with activity counts
  PATCH  /api/admin/users/<id>          role, suspend/unsuspend, confirm email, KYC status
  DELETE /api/admin/users/<id>          remove a user and their data
  GET    /api/admin/jobs                all ads incl. inactive/expired, with employer
  PATCH  /api/admin/jobs/<id>           activate/deactivate, feature, extend, reclassify
  POST   /api/admin/jobs/bulk           same actions on many ids
  GET    /api/admin/reviews             moderation queue
  PATCH  /api/admin/reviews/<id>        hide / unhide
  DELETE /api/admin/reviews/<id>
  GET    /api/admin/alerts              all saved searches
  PATCH  /api/admin/alerts/<id>         pause / resume
  DELETE /api/admin/alerts/<id>
  GET    /api/admin/system              health, config flags, table sizes, maintenance checklist
  POST   /api/admin/system/tasks        run a maintenance task (rebuild FTS, expire ads, digests, vacuum...)
  GET    /api/admin/settings            runtime switches
  PUT    /api/admin/settings            update switches (maintenance mode, announcement, posting rules)
  GET    /api/admin/audit               who did what
  GET    /api/settings/public           (no auth) announcement + maintenance flag for the frontends
"""
import datetime
import json
import os
import platform
import shutil
import sqlite3
import sys
import time

from flask import jsonify, request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_schema import fts_available  # noqa: E402
from taxonomy import derive_state, normalize_classification, normalize_subclassification, CLASSIFICATIONS  # noqa: E402

STARTED_AT = time.time()

SETTING_DEFAULTS = {
    'maintenance_mode': 'off',          # 'on' blocks non-admin writes with 503
    'announcement': '',                 # banner text shown on public pages
    'allow_free_posting': 'on',         # employers can publish without paying
    'require_kyc_to_post': 'off',       # employers must be KYC-verified to post
    'default_expiry_days': '30',
    'max_active_jobs_per_employer': '50',
}
PAGE_MAX = 100


def _now():
    return datetime.datetime.now().isoformat()


def _page_args():
    try:
        page = max(1, int(request.args.get('page', 1)))
        limit = min(PAGE_MAX, max(1, int(request.args.get('limit', 25))))
    except ValueError:
        page, limit = 1, 25
    return page, limit, (page - 1) * limit


def get_setting(db, key):
    row = db.execute("SELECT value FROM site_settings WHERE key = ?", (key,)).fetchone()
    return row['value'] if row else SETTING_DEFAULTS.get(key)


def all_settings(db):
    out = dict(SETTING_DEFAULTS)
    for r in db.execute("SELECT key, value FROM site_settings"):
        out[r['key']] = r['value']
    return out


def init_admin(app, *, get_db, require_auth, require_role, decode_token, db_path, is_production, limiter=None):

    def audit(db, action, target_type=None, target_id=None, detail=None):
        db.execute(
            "INSERT INTO admin_audit_log (admin_id, admin_email, action, target_type, target_id, detail, ip, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (getattr(request, 'user_id', None), getattr(request, 'user_email', None), action, target_type,
             str(target_id) if target_id is not None else None,
             json.dumps(detail, default=str) if isinstance(detail, (dict, list)) else detail,
             request.headers.get('X-Forwarded-For', request.remote_addr), _now()))

    def admin_only(f):
        # Admin sessions page through tables quickly; the public per-IP limits would throttle them.
        wrapped = require_auth(require_role('admin')(f))
        return limiter.exempt(wrapped) if limiter else wrapped

    # ── Maintenance mode: block writes from non-admins ────────────────────────
    @app.before_request
    def _maintenance_gate():
        if request.method in ('GET', 'HEAD', 'OPTIONS') or not request.path.startswith('/api/'):
            return None
        if request.path.startswith('/api/auth/') or request.path.startswith('/api/admin/'):
            return None
        db = get_db()
        if get_setting(db, 'maintenance_mode') != 'on':
            return None
        auth = request.headers.get('Authorization', '')
        payload = decode_token(auth.split(' ', 1)[1]) if auth.startswith('Bearer ') else None
        if payload and payload.get('role') == 'admin':
            return None
        return jsonify({'error': 'OpenJobs is in maintenance mode. Please try again shortly.', 'maintenance': True}), 503

    # ── Public settings ───────────────────────────────────────────────────────
    @app.route('/api/settings/public', methods=['GET'])
    def public_settings():
        db = get_db()
        return jsonify({
            'maintenance_mode': get_setting(db, 'maintenance_mode') == 'on',
            'announcement': get_setting(db, 'announcement') or '',
            'allow_free_posting': get_setting(db, 'allow_free_posting') == 'on',
        })

    # ── Overview ──────────────────────────────────────────────────────────────
    @app.route('/api/admin/overview', methods=['GET'])
    @admin_only
    def admin_overview():
        db = get_db()
        now = datetime.datetime.now()
        d7 = (now - datetime.timedelta(days=7)).isoformat()
        d30 = (now - datetime.timedelta(days=30)).isoformat()
        today = now.date().isoformat()
        one = lambda sql, *p: db.execute(sql, p).fetchone()[0]  # noqa: E731

        kpis = {
            'jobs_active': one("SELECT COUNT(*) FROM jobs WHERE is_active = 1"),
            'jobs_live': one("SELECT COUNT(*) FROM jobs WHERE is_active = 1 AND (expires_at IS NULL OR expires_at > ?)", now.isoformat()),
            'jobs_featured': one("SELECT COUNT(*) FROM jobs WHERE is_active = 1 AND is_featured = 1"),
            'jobs_posted_7d': one("SELECT COUNT(*) FROM jobs WHERE created_at >= ?", d7),
            'jobs_expired_still_active': one("SELECT COUNT(*) FROM jobs WHERE is_active = 1 AND expires_at IS NOT NULL AND expires_at <= ?", now.isoformat()),
            'seekers': one("SELECT COUNT(*) FROM users WHERE role = 'user'"),
            'employers': one("SELECT COUNT(*) FROM users WHERE role = 'employer'"),
            'admins': one("SELECT COUNT(*) FROM users WHERE role = 'admin'"),
            'signups_7d': one("SELECT COUNT(*) FROM users WHERE created_at >= ?", d7),
            'suspended': one("SELECT COUNT(*) FROM users WHERE is_suspended = 1"),
            'unconfirmed': one("SELECT COUNT(*) FROM users WHERE email_confirmed = 0"),
            'applications': one("SELECT COUNT(*) FROM applications"),
            'applications_7d': one("SELECT COUNT(*) FROM applications WHERE applied_at >= ?", d7),
            'applications_today': one("SELECT COUNT(*) FROM applications WHERE DATE(applied_at) = ?", today),
            'reviews': one("SELECT COUNT(*) FROM company_reviews WHERE is_hidden = 0"),
            'reviews_hidden': one("SELECT COUNT(*) FROM company_reviews WHERE is_hidden = 1"),
            'reviews_low_rating_7d': one("SELECT COUNT(*) FROM company_reviews WHERE rating <= 2 AND created_at >= ?", d7),
            'alerts_active': one("SELECT COUNT(*) FROM job_alerts WHERE is_active = 1"),
            'alerts_instant': one("SELECT COUNT(*) FROM job_alerts WHERE is_active = 1 AND frequency = 'instant'"),
            'kyc_pending': one("SELECT COUNT(*) FROM users WHERE kyc_status = 'submitted'"),
            'views_total': one("SELECT COALESCE(SUM(view_count), 0) FROM jobs"),
            'companies_live': one("SELECT COUNT(DISTINCT LOWER(company)) FROM jobs WHERE is_active = 1"),
        }
        series = lambda sql: [dict(r) for r in db.execute(sql, (d30,)).fetchall()]  # noqa: E731
        trends = {
            'jobs': series("SELECT DATE(created_at) AS day, COUNT(*) AS n FROM jobs WHERE created_at >= ? GROUP BY day ORDER BY day"),
            'applications': series("SELECT DATE(applied_at) AS day, COUNT(*) AS n FROM applications WHERE applied_at >= ? GROUP BY day ORDER BY day"),
            'signups': series("SELECT DATE(created_at) AS day, COUNT(*) AS n FROM users WHERE created_at >= ? GROUP BY day ORDER BY day"),
        }
        rows = lambda sql, *p: [dict(r) for r in db.execute(sql, p).fetchall()]  # noqa: E731
        breakdowns = {
            'classification': rows("SELECT COALESCE(classification, 'Unclassified') AS label, COUNT(*) AS n FROM jobs WHERE is_active = 1 GROUP BY label ORDER BY n DESC LIMIT 12"),
            'county': rows("SELECT COALESCE(state, 'Unknown') AS label, COUNT(*) AS n FROM jobs WHERE is_active = 1 GROUP BY label ORDER BY n DESC LIMIT 12"),
            'work_type': rows("SELECT COALESCE(work_type, 'unknown') AS label, COUNT(*) AS n FROM jobs WHERE is_active = 1 GROUP BY label ORDER BY n DESC"),
            'application_status': rows("SELECT status AS label, COUNT(*) AS n FROM applications GROUP BY status ORDER BY n DESC"),
        }
        top_employers = rows("""
            SELECT u.id, u.name, u.email, u.company, COUNT(j.id) AS jobs,
                   COALESCE(SUM(j.application_count), 0) AS applications
            FROM users u JOIN jobs j ON j.employer_id = u.id AND j.is_active = 1
            WHERE u.role = 'employer' GROUP BY u.id ORDER BY jobs DESC LIMIT 8""")
        recent = {
            'signups': rows("SELECT id, name, email, role, created_at, email_confirmed FROM users ORDER BY created_at DESC LIMIT 8"),
            'jobs': rows("SELECT id, title, company, location, created_at, is_active, is_featured FROM jobs ORDER BY created_at DESC LIMIT 8"),
            'reviews': rows("""SELECT r.id, r.company, r.rating, r.title, r.created_at, r.is_hidden, u.email AS user_email
                               FROM company_reviews r LEFT JOIN users u ON u.id = r.user_id ORDER BY r.created_at DESC LIMIT 8"""),
            'audit': rows("SELECT id, admin_email, action, target_type, target_id, created_at FROM admin_audit_log ORDER BY id DESC LIMIT 8"),
        }
        attention = []
        if kpis['jobs_expired_still_active']:
            attention.append({'level': 'warn', 'text': f"{kpis['jobs_expired_still_active']} expired ads are still marked active", 'task': 'expire_jobs'})
        if kpis['kyc_pending']:
            attention.append({'level': 'info', 'text': f"{kpis['kyc_pending']} KYC submissions awaiting review", 'tab': 'kyc'})
        if kpis['reviews_low_rating_7d']:
            attention.append({'level': 'info', 'text': f"{kpis['reviews_low_rating_7d']} one/two-star reviews posted this week", 'tab': 'reviews'})
        missing = one("SELECT COUNT(*) FROM jobs WHERE is_active = 1 AND (state IS NULL OR classification IS NULL)")
        if missing:
            attention.append({'level': 'warn', 'text': f"{missing} active ads have no county or classification (hurts facets/SEO)", 'task': 'backfill_jobs'})
        if get_setting(db, 'maintenance_mode') == 'on':
            attention.append({'level': 'error', 'text': 'Maintenance mode is ON — non-admin writes are blocked', 'tab': 'settings'})
        if not os.environ.get('SMTP_HOST'):
            attention.append({'level': 'warn', 'text': 'SMTP is not configured — confirmation emails and job alerts are not being delivered', 'tab': 'system'})
        return jsonify({'kpis': kpis, 'trends': trends, 'breakdowns': breakdowns, 'top_employers': top_employers,
                        'recent': recent, 'attention': attention, 'generated_at': _now()})

    # ── Users ─────────────────────────────────────────────────────────────────
    USER_COLS = """u.id, u.name, u.email, u.role, u.company, u.phone, u.county, u.created_at, u.last_login_at,
                   u.email_confirmed, u.is_suspended, u.suspended_reason, u.kyc_status, u.plan"""

    @app.route('/api/admin/users', methods=['GET'])
    @admin_only
    def admin_users():
        db = get_db()
        page, limit, offset = _page_args()
        where, params = [], []
        q = (request.args.get('q') or '').strip()
        if q:
            where.append("(u.name LIKE ? OR u.email LIKE ? OR u.company LIKE ? OR u.phone LIKE ?)")
            params += [f'%{q}%'] * 4
        role = request.args.get('role')
        if role in ('user', 'employer', 'admin'):
            where.append("u.role = ?"); params.append(role)
        status = request.args.get('status')
        if status == 'suspended':
            where.append("u.is_suspended = 1")
        elif status == 'unconfirmed':
            where.append("u.email_confirmed = 0")
        elif status == 'kyc_pending':
            where.append("u.kyc_status = 'submitted'")
        elif status == 'active':
            where.append("u.is_suspended = 0 AND u.email_confirmed = 1")
        sort = {'newest': 'u.created_at DESC', 'oldest': 'u.created_at ASC', 'name': 'u.name COLLATE NOCASE ASC',
                'last_login': 'u.last_login_at DESC'}.get(request.args.get('sort'), 'u.created_at DESC')
        w = ('WHERE ' + ' AND '.join(where)) if where else ''
        total = db.execute(f"SELECT COUNT(*) FROM users u {w}", params).fetchone()[0]
        rows = db.execute(f"""
            SELECT {USER_COLS},
                   (SELECT COUNT(*) FROM jobs j WHERE j.employer_id = u.id AND j.is_active = 1) AS job_count,
                   (SELECT COUNT(*) FROM applications a WHERE a.user_id = u.id) AS application_count,
                   (SELECT COUNT(*) FROM job_alerts al WHERE al.user_id = u.id AND al.is_active = 1) AS alert_count
            FROM users u {w} ORDER BY {sort} LIMIT ? OFFSET ?""", params + [limit, offset]).fetchall()
        return jsonify({'users': [dict(r) for r in rows],
                        'pagination': {'page': page, 'limit': limit, 'total': total, 'pages': max(1, -(-total // limit))}})

    @app.route('/api/admin/users/<int:user_id>', methods=['PATCH'])
    @admin_only
    def admin_update_user(user_id):
        db = get_db()
        user = db.execute("SELECT id, role, email FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        data = request.json or {}
        changes, params = [], []
        is_self = user_id == request.user_id

        if 'role' in data:
            role = data['role']
            if role not in ('user', 'employer', 'admin'):
                return jsonify({'error': 'role must be user, employer or admin'}), 400
            if is_self and role != 'admin':
                return jsonify({'error': 'You cannot remove your own admin role'}), 400
            if user['role'] == 'admin' and role != 'admin' and \
               db.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0] <= 1:
                return jsonify({'error': 'Cannot demote the last admin'}), 400
            changes.append("role = ?"); params.append(role)
        if 'is_suspended' in data:
            suspended = 1 if data['is_suspended'] else 0
            if is_self and suspended:
                return jsonify({'error': 'You cannot suspend yourself'}), 400
            changes.append("is_suspended = ?"); params.append(suspended)
            changes.append("suspended_reason = ?"); params.append((data.get('suspended_reason') or '')[:300] if suspended else None)
            if suspended:
                # Suspended employers' ads come down immediately
                db.execute("UPDATE jobs SET is_active = 0 WHERE employer_id = ?", (user_id,))
        if 'email_confirmed' in data:
            changes.append("email_confirmed = ?"); params.append(1 if data['email_confirmed'] else 0)
        if 'plan' in data:
            if data['plan'] not in ('free', 'standard', 'premium'):
                return jsonify({'error': 'plan must be free, standard or premium'}), 400
            changes.append("plan = ?"); params.append(data['plan'])
        if 'kyc_status' in data:
            if data['kyc_status'] not in ('pending', 'submitted', 'verified', 'rejected'):
                return jsonify({'error': 'invalid kyc_status'}), 400
            changes.append("kyc_status = ?"); params.append(data['kyc_status'])
            db.execute("UPDATE kyc_documents SET status = ? WHERE user_id = ?", (data['kyc_status'], user_id))
        if not changes:
            return jsonify({'error': 'Nothing to update'}), 400
        db.execute(f"UPDATE users SET {', '.join(changes)} WHERE id = ?", params + [user_id])
        audit(db, 'user.update', 'user', user_id, {'email': user['email'], **{k: data[k] for k in data if k in ('role', 'is_suspended', 'suspended_reason', 'email_confirmed', 'kyc_status', 'plan')}})
        db.commit()
        row = db.execute(f"SELECT {USER_COLS} FROM users u WHERE u.id = ?", (user_id,)).fetchone()
        return jsonify({'success': True, 'user': dict(row)})

    @app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
    @admin_only
    def admin_delete_user(user_id):
        db = get_db()
        user = db.execute("SELECT id, role, email FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        if user_id == request.user_id:
            return jsonify({'error': 'You cannot delete your own account from here'}), 400
        if user['role'] == 'admin':
            return jsonify({'error': 'Demote the admin before deleting the account'}), 400
        jobs = db.execute("SELECT COUNT(*) FROM jobs WHERE employer_id = ?", (user_id,)).fetchone()[0]
        for sql in ("DELETE FROM applications WHERE user_id = ?",
                    "DELETE FROM applications WHERE job_id IN (SELECT id FROM jobs WHERE employer_id = ?)",
                    "DELETE FROM saved_jobs WHERE user_id = ?",
                    "DELETE FROM saved_jobs WHERE job_id IN (SELECT id FROM jobs WHERE employer_id = ?)",
                    "DELETE FROM job_alerts WHERE user_id = ?",
                    "DELETE FROM company_reviews WHERE user_id = ?",
                    "DELETE FROM company_ratings WHERE user_id = ?",
                    "DELETE FROM kyc_documents WHERE user_id = ?",
                    "DELETE FROM jobs WHERE employer_id = ?",
                    "DELETE FROM users WHERE id = ?"):
            db.execute(sql, (user_id,))
        audit(db, 'user.delete', 'user', user_id, {'email': user['email'], 'role': user['role'], 'jobs_removed': jobs})
        db.commit()
        return jsonify({'success': True, 'jobs_removed': jobs})

    # ── Jobs ──────────────────────────────────────────────────────────────────
    @app.route('/api/admin/jobs', methods=['GET'])
    @admin_only
    def admin_jobs():
        db = get_db()
        page, limit, offset = _page_args()
        now = _now()
        where, params = [], []
        q = (request.args.get('q') or '').strip()
        if q:
            if q.isdigit():
                where.append("(j.id = ? OR j.title LIKE ? OR j.company LIKE ?)"); params += [int(q), f'%{q}%', f'%{q}%']
            else:
                where.append("(j.title LIKE ? OR j.company LIKE ? OR j.location LIKE ? OR u.email LIKE ?)"); params += [f'%{q}%'] * 4
        status = request.args.get('status', 'all')
        if status == 'active':
            where.append("j.is_active = 1 AND (j.expires_at IS NULL OR j.expires_at > ?)"); params.append(now)
        elif status == 'inactive':
            where.append("j.is_active = 0")
        elif status == 'expired':
            where.append("j.expires_at IS NOT NULL AND j.expires_at <= ?"); params.append(now)
        elif status == 'featured':
            where.append("j.is_featured = 1")
        elif status == 'unclassified':
            where.append("(j.classification IS NULL OR j.state IS NULL)")
        if request.args.get('employer_id'):
            where.append("j.employer_id = ?"); params.append(int(request.args['employer_id']))
        if request.args.get('classification'):
            where.append("j.classification = ?"); params.append(request.args['classification'])
        sort = {'newest': 'j.created_at DESC', 'oldest': 'j.created_at ASC', 'views': 'j.view_count DESC',
                'applications': 'j.application_count DESC', 'expiring': 'j.expires_at ASC'}.get(request.args.get('sort'), 'j.created_at DESC')
        w = ('WHERE ' + ' AND '.join(where)) if where else ''
        base = f"FROM jobs j LEFT JOIN users u ON u.id = j.employer_id {w}"
        total = db.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
        rows = db.execute(f"""
            SELECT j.id, j.title, j.company, j.location, j.state, j.classification, j.subclassification, j.work_type,
                   j.work_arrangement, j.salary_min, j.salary_max, j.salary_currency, j.is_active, j.is_featured,
                   j.view_count, j.application_count, j.created_at, j.expires_at, j.employer_id,
                   u.email AS employer_email, u.is_suspended AS employer_suspended,
                   CASE WHEN j.expires_at IS NOT NULL AND j.expires_at <= ? THEN 1 ELSE 0 END AS is_expired
            {base} ORDER BY {sort} LIMIT ? OFFSET ?""", [now] + params + [limit, offset]).fetchall()
        return jsonify({'jobs': [dict(r) for r in rows],
                        'pagination': {'page': page, 'limit': limit, 'total': total, 'pages': max(1, -(-total // limit))}})

    def _apply_job_action(db, job_id, action, data):
        job = db.execute("SELECT id, title, company, expires_at, location FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            return None
        if action == 'activate':
            db.execute("UPDATE jobs SET is_active = 1 WHERE id = ?", (job_id,))
        elif action == 'deactivate':
            db.execute("UPDATE jobs SET is_active = 0 WHERE id = ?", (job_id,))
        elif action == 'feature':
            db.execute("UPDATE jobs SET is_featured = 1 WHERE id = ?", (job_id,))
        elif action == 'unfeature':
            db.execute("UPDATE jobs SET is_featured = 0 WHERE id = ?", (job_id,))
        elif action == 'extend':
            days = int(data.get('days', 30))
            base = max(datetime.datetime.now(), datetime.datetime.fromisoformat(job['expires_at'])) if job['expires_at'] else datetime.datetime.now()
            db.execute("UPDATE jobs SET expires_at = ?, is_active = 1 WHERE id = ?", ((base + datetime.timedelta(days=days)).isoformat(), job_id))
        elif action == 'reclassify':
            cls = normalize_classification(data.get('classification'))
            sub = normalize_subclassification(cls, data.get('subclassification'))
            db.execute("UPDATE jobs SET classification = ?, subclassification = ?, state = COALESCE(state, ?) WHERE id = ?",
                       (cls, sub, derive_state(job['location']), job_id))
        elif action == 'delete':
            for sql in ("DELETE FROM applications WHERE job_id = ?", "DELETE FROM saved_jobs WHERE job_id = ?", "DELETE FROM jobs WHERE id = ?"):
                db.execute(sql, (job_id,))
        else:
            raise ValueError('unknown action')
        return dict(job)

    JOB_ACTIONS = ('activate', 'deactivate', 'feature', 'unfeature', 'extend', 'reclassify', 'delete')

    @app.route('/api/admin/jobs/<int:job_id>', methods=['PATCH'])
    @admin_only
    def admin_update_job(job_id):
        db = get_db()
        data = request.json or {}
        action = data.get('action')
        if action not in JOB_ACTIONS:
            return jsonify({'error': f"action must be one of {', '.join(JOB_ACTIONS)}"}), 400
        job = _apply_job_action(db, job_id, action, data)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        audit(db, f'job.{action}', 'job', job_id, {'title': job['title'], 'company': job['company'], **{k: v for k, v in data.items() if k != 'action'}})
        db.commit()
        return jsonify({'success': True})

    @app.route('/api/admin/jobs/bulk', methods=['POST'])
    @admin_only
    def admin_bulk_jobs():
        db = get_db()
        data = request.json or {}
        action = data.get('action')
        ids = [int(i) for i in (data.get('ids') or []) if str(i).isdigit()][:500]
        if action not in JOB_ACTIONS or not ids:
            return jsonify({'error': 'action and ids are required'}), 400
        done = sum(1 for i in ids if _apply_job_action(db, i, action, data))
        audit(db, f'job.bulk_{action}', 'job', ','.join(map(str, ids[:50])), {'count': done})
        db.commit()
        return jsonify({'success': True, 'updated': done})

    # ── Reviews ───────────────────────────────────────────────────────────────
    def _recompute_company_rating(db, company):
        avg = db.execute("SELECT AVG(rating) FROM company_reviews WHERE LOWER(company) = LOWER(?) AND is_hidden = 0", (company,)).fetchone()[0]
        db.execute("UPDATE jobs SET company_rating = ? WHERE LOWER(company) = LOWER(?)", (round(avg, 1) if avg else 0, company))

    @app.route('/api/admin/reviews', methods=['GET'])
    @admin_only
    def admin_reviews():
        db = get_db()
        page, limit, offset = _page_args()
        where, params = [], []
        status = request.args.get('status', 'all')
        if status == 'visible':
            where.append("r.is_hidden = 0")
        elif status == 'hidden':
            where.append("r.is_hidden = 1")
        elif status == 'low':
            where.append("r.rating <= 2")
        q = (request.args.get('q') or '').strip()
        if q:
            where.append("(r.company LIKE ? OR r.title LIKE ? OR r.pros LIKE ? OR r.cons LIKE ? OR u.email LIKE ?)"); params += [f'%{q}%'] * 5
        w = ('WHERE ' + ' AND '.join(where)) if where else ''
        base = f"FROM company_reviews r LEFT JOIN users u ON u.id = r.user_id {w}"
        total = db.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
        rows = db.execute(f"""SELECT r.id, r.company, r.rating, r.title, r.pros, r.cons, r.role, r.is_current, r.is_hidden, r.created_at,
                                     u.id AS user_id, u.email AS user_email, u.name AS user_name
                              {base} ORDER BY r.created_at DESC LIMIT ? OFFSET ?""", params + [limit, offset]).fetchall()
        return jsonify({'reviews': [dict(r) for r in rows],
                        'pagination': {'page': page, 'limit': limit, 'total': total, 'pages': max(1, -(-total // limit))}})

    @app.route('/api/admin/reviews/<int:review_id>', methods=['PATCH'])
    @admin_only
    def admin_update_review(review_id):
        db = get_db()
        row = db.execute("SELECT id, company FROM company_reviews WHERE id = ?", (review_id,)).fetchone()
        if not row:
            return jsonify({'error': 'Review not found'}), 404
        data = request.json or {}
        if 'is_hidden' not in data:
            return jsonify({'error': 'is_hidden is required'}), 400
        hidden = 1 if data['is_hidden'] else 0
        db.execute("UPDATE company_reviews SET is_hidden = ? WHERE id = ?", (hidden, review_id))
        _recompute_company_rating(db, row['company'])
        audit(db, 'review.hide' if hidden else 'review.unhide', 'review', review_id, {'company': row['company'], 'reason': data.get('reason')})
        db.commit()
        return jsonify({'success': True, 'is_hidden': hidden})

    @app.route('/api/admin/reviews/<int:review_id>', methods=['DELETE'])
    @admin_only
    def admin_delete_review(review_id):
        db = get_db()
        row = db.execute("SELECT id, company FROM company_reviews WHERE id = ?", (review_id,)).fetchone()
        if not row:
            return jsonify({'error': 'Review not found'}), 404
        db.execute("DELETE FROM company_reviews WHERE id = ?", (review_id,))
        _recompute_company_rating(db, row['company'])
        audit(db, 'review.delete', 'review', review_id, {'company': row['company']})
        db.commit()
        return jsonify({'success': True})

    # ── Alerts ────────────────────────────────────────────────────────────────
    @app.route('/api/admin/alerts', methods=['GET'])
    @admin_only
    def admin_alerts():
        db = get_db()
        page, limit, offset = _page_args()
        where, params = [], []
        if request.args.get('status') == 'active':
            where.append("a.is_active = 1")
        elif request.args.get('status') == 'paused':
            where.append("a.is_active = 0")
        if request.args.get('frequency') in ('instant', 'daily'):
            where.append("a.frequency = ?"); params.append(request.args['frequency'])
        q = (request.args.get('q') or '').strip()
        if q:
            where.append("(a.name LIKE ? OR a.keywords LIKE ? OR a.location LIKE ? OR u.email LIKE ?)"); params += [f'%{q}%'] * 4
        w = ('WHERE ' + ' AND '.join(where)) if where else ''
        base = f"FROM job_alerts a LEFT JOIN users u ON u.id = a.user_id {w}"
        total = db.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
        rows = db.execute(f"""SELECT a.*, u.email AS user_email, u.name AS user_name {base}
                              ORDER BY a.created_at DESC LIMIT ? OFFSET ?""", params + [limit, offset]).fetchall()
        return jsonify({'alerts': [dict(r) for r in rows],
                        'pagination': {'page': page, 'limit': limit, 'total': total, 'pages': max(1, -(-total // limit))}})

    @app.route('/api/admin/alerts/<int:alert_id>', methods=['PATCH', 'DELETE'])
    @admin_only
    def admin_modify_alert(alert_id):
        db = get_db()
        row = db.execute("SELECT id, user_id, name FROM job_alerts WHERE id = ?", (alert_id,)).fetchone()
        if not row:
            return jsonify({'error': 'Alert not found'}), 404
        if request.method == 'DELETE':
            db.execute("DELETE FROM job_alerts WHERE id = ?", (alert_id,))
            audit(db, 'alert.delete', 'alert', alert_id, {'user_id': row['user_id']})
        else:
            data = request.json or {}
            active = 1 if data.get('is_active', True) else 0
            db.execute("UPDATE job_alerts SET is_active = ? WHERE id = ?", (active, alert_id))
            audit(db, 'alert.resume' if active else 'alert.pause', 'alert', alert_id, {'user_id': row['user_id']})
        db.commit()
        return jsonify({'success': True})

    # ── System health & maintenance ───────────────────────────────────────────
    @app.route('/api/admin/system', methods=['GET'])
    @admin_only
    def admin_system():
        db = get_db()
        now = _now()
        tables = {}
        for t in ('users', 'jobs', 'applications', 'saved_jobs', 'job_alerts', 'company_reviews', 'kyc_documents', 'admin_audit_log'):
            tables[t] = db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        fts_ok = fts_available(db)
        fts_rows = db.execute("SELECT COUNT(*) FROM jobs_fts").fetchone()[0] if fts_ok else None
        try:
            disk = shutil.disk_usage(os.path.dirname(os.path.abspath(db_path)) or '.')
            disk_free_mb = round(disk.free / 1024 / 1024)
        except OSError:
            disk_free_mb = None
        checks = [
            {'id': 'expired_active', 'label': 'Expired ads still active',
             'value': db.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1 AND expires_at IS NOT NULL AND expires_at <= ?", (now,)).fetchone()[0],
             'fix': 'expire_jobs'},
            {'id': 'missing_derived', 'label': 'Ads missing county / classification',
             'value': db.execute("SELECT COUNT(*) FROM jobs WHERE state IS NULL OR classification IS NULL").fetchone()[0], 'fix': 'backfill_jobs'},
            {'id': 'fts_drift', 'label': 'FTS index rows out of sync with jobs',
             'value': (abs(fts_rows - tables['jobs']) if fts_ok else None), 'fix': 'rebuild_fts'},
            {'id': 'stale_unconfirmed', 'label': 'Unconfirmed accounts older than 30 days',
             'value': db.execute("SELECT COUNT(*) FROM users WHERE email_confirmed = 0 AND created_at < ?",
                                 ((datetime.datetime.now() - datetime.timedelta(days=30)).isoformat(),)).fetchone()[0], 'fix': 'purge_unconfirmed'},
            {'id': 'digests_due', 'label': 'Daily alerts due for a digest',
             'value': db.execute("SELECT COUNT(*) FROM job_alerts WHERE is_active = 1 AND frequency = 'daily' AND (last_sent_at IS NULL OR last_sent_at < ?)",
                                 ((datetime.datetime.now() - datetime.timedelta(hours=23)).isoformat(),)).fetchone()[0], 'fix': 'run_digests'},
            {'id': 'orphan_apps', 'label': 'Applications pointing at deleted jobs',
             'value': db.execute("SELECT COUNT(*) FROM applications a WHERE NOT EXISTS (SELECT 1 FROM jobs j WHERE j.id = a.job_id)").fetchone()[0], 'fix': 'purge_orphans'},
        ]
        env = lambda k: bool(os.environ.get(k))  # noqa: E731
        integrations = {
            'smtp': env('SMTP_HOST') and env('SMTP_USER'),
            'stripe': env('STRIPE_SECRET_KEY'),
            'mpesa': env('MPESA_CONSUMER_KEY'),
            'google_signin': env('GOOGLE_CLIENT_ID'),
            'redis': env('REDIS_URL'),
            'telegram': env('TELEGRAM_BOT_TOKEN'),
            'ollama_url': os.environ.get('OLLAMA_URL', 'http://localhost:11434'),
            'app_url': os.environ.get('APP_URL', ''),
        }
        return jsonify({
            'runtime': {
                'python': platform.python_version(), 'sqlite': sqlite3.sqlite_version,
                'uptime_seconds': int(time.time() - STARTED_AT), 'production': is_production,
                'started_at': datetime.datetime.fromtimestamp(STARTED_AT).isoformat(),
            },
            'database': {
                'path': os.path.abspath(db_path), 'size_mb': round(os.path.getsize(db_path) / 1024 / 1024, 2) if os.path.exists(db_path) else 0,
                'disk_free_mb': disk_free_mb, 'tables': tables, 'fts_available': fts_ok, 'fts_rows': fts_rows,
                'journal_mode': db.execute("PRAGMA journal_mode").fetchone()[0],
            },
            'integrations': integrations,
            'checks': checks,
            'settings': all_settings(db),
        })

    TASKS = ('expire_jobs', 'backfill_jobs', 'rebuild_fts', 'purge_unconfirmed', 'run_digests', 'purge_orphans',
             'vacuum', 'integrity_check', 'seed_demo', 'purge_demo')

    @app.route('/api/admin/system/tasks', methods=['POST'])
    @admin_only
    def admin_run_task():
        data = request.json or {}
        task = data.get('task')
        if task not in TASKS:
            return jsonify({'error': f"task must be one of {', '.join(TASKS)}"}), 400
        db = get_db()
        result = {}
        now = _now()
        if task == 'expire_jobs':
            cur = db.execute("UPDATE jobs SET is_active = 0 WHERE is_active = 1 AND expires_at IS NOT NULL AND expires_at <= ?", (now,))
            result['deactivated'] = cur.rowcount
        elif task == 'backfill_jobs':
            n = 0
            for r in db.execute("SELECT id, location, category, classification, state FROM jobs WHERE state IS NULL OR classification IS NULL").fetchall():
                db.execute("UPDATE jobs SET state = COALESCE(state, ?), classification = COALESCE(classification, ?) WHERE id = ?",
                           (derive_state(r['location']), normalize_classification(r['category']), r['id']))
                n += 1
            result['updated'] = n
        elif task == 'rebuild_fts':
            if not fts_available(db):
                return jsonify({'error': 'FTS5 is not available in this SQLite build'}), 409
            db.execute("INSERT INTO jobs_fts(jobs_fts) VALUES ('rebuild')")
            result['fts_rows'] = db.execute("SELECT COUNT(*) FROM jobs_fts").fetchone()[0]
        elif task == 'purge_unconfirmed':
            days = int(data.get('days', 30))
            cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
            ids = [r[0] for r in db.execute("SELECT id FROM users WHERE email_confirmed = 0 AND role != 'admin' AND created_at < ?", (cutoff,))]
            for uid in ids:
                for sql in ("DELETE FROM job_alerts WHERE user_id = ?", "DELETE FROM saved_jobs WHERE user_id = ?",
                            "DELETE FROM applications WHERE user_id = ?", "DELETE FROM kyc_documents WHERE user_id = ?",
                            "DELETE FROM jobs WHERE employer_id = ?", "DELETE FROM users WHERE id = ?"):
                    db.execute(sql, (uid,))
            result['removed'] = len(ids)
        elif task == 'purge_orphans':
            a = db.execute("DELETE FROM applications WHERE NOT EXISTS (SELECT 1 FROM jobs j WHERE j.id = applications.job_id)").rowcount
            s = db.execute("DELETE FROM saved_jobs WHERE NOT EXISTS (SELECT 1 FROM jobs j WHERE j.id = saved_jobs.job_id)").rowcount
            result.update({'applications': a, 'saved_jobs': s})
        elif task == 'run_digests':
            db.commit()   # release our write lock before the digest runner opens its own connection
            from alerts import run_digests
            result['emails_sent'] = run_digests(db_path, dry_run=bool(data.get('dry_run')))
        elif task == 'integrity_check':
            result['result'] = db.execute("PRAGMA quick_check").fetchone()[0]
        elif task == 'vacuum':
            db.commit()
            before = os.path.getsize(db_path)
            db.execute("VACUUM")
            result.update({'before_mb': round(before / 1e6, 2), 'after_mb': round(os.path.getsize(db_path) / 1e6, 2)})
        elif task in ('seed_demo', 'purge_demo'):
            if is_production:
                return jsonify({'error': 'Demo data tasks are disabled in production'}), 403
            db.commit()
            import seed_demo
            con = seed_demo._connect(db_path)
            try:
                if seed_demo.already_seeded(con):
                    seed_demo.remove_demo(con)
                    result['removed_previous'] = True
            finally:
                con.close()
            if task == 'seed_demo':
                result['created'] = seed_demo.seed(db_path, int(data.get('jobs', 240)))
        audit(db, f'system.{task}', 'system', None, result)
        db.commit()
        return jsonify({'success': True, 'task': task, 'result': result})

    # ── Settings ──────────────────────────────────────────────────────────────
    @app.route('/api/admin/settings', methods=['GET'])
    @admin_only
    def admin_get_settings():
        return jsonify({'settings': all_settings(get_db()), 'defaults': SETTING_DEFAULTS})

    @app.route('/api/admin/settings', methods=['PUT'])
    @admin_only
    def admin_put_settings():
        db = get_db()
        data = request.json or {}
        changed = {}
        for key, value in data.items():
            if key not in SETTING_DEFAULTS:
                return jsonify({'error': f'Unknown setting {key!r}'}), 400
            if key in ('maintenance_mode', 'allow_free_posting', 'require_kyc_to_post'):
                value = 'on' if value in (True, 'on', 1, '1', 'true') else 'off'
            elif key in ('default_expiry_days', 'max_active_jobs_per_employer'):
                try:
                    value = str(max(1, int(value)))
                except (TypeError, ValueError):
                    return jsonify({'error': f'{key} must be a positive integer'}), 400
            else:
                value = str(value or '')[:500]
            db.execute("INSERT INTO site_settings (key, value, updated_at, updated_by) VALUES (?,?,?,?) "
                       "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at, updated_by = excluded.updated_by",
                       (key, value, _now(), request.user_email))
            changed[key] = value
        if changed:
            audit(db, 'settings.update', 'settings', None, changed)
            db.commit()
        return jsonify({'success': True, 'settings': all_settings(db)})

    # ── Audit log ─────────────────────────────────────────────────────────────
    @app.route('/api/admin/audit', methods=['GET'])
    @admin_only
    def admin_audit():
        db = get_db()
        page, limit, offset = _page_args()
        where, params = [], []
        if request.args.get('action'):
            where.append("action LIKE ?"); params.append(request.args['action'] + '%')
        if request.args.get('admin'):
            where.append("admin_email LIKE ?"); params.append(f"%{request.args['admin']}%")
        w = ('WHERE ' + ' AND '.join(where)) if where else ''
        total = db.execute(f"SELECT COUNT(*) FROM admin_audit_log {w}", params).fetchone()[0]
        rows = db.execute(f"SELECT * FROM admin_audit_log {w} ORDER BY id DESC LIMIT ? OFFSET ?", params + [limit, offset]).fetchall()
        return jsonify({'entries': [dict(r) for r in rows],
                        'pagination': {'page': page, 'limit': limit, 'total': total, 'pages': max(1, -(-total // limit))}})

    # ── Reference data for the dashboard ──────────────────────────────────────
    @app.route('/api/admin/meta', methods=['GET'])
    @admin_only
    def admin_meta():
        return jsonify({'classifications': CLASSIFICATIONS, 'tasks': TASKS, 'job_actions': JOB_ACTIONS})
