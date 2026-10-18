# OpenJobs — Security audit (production readiness)

Audit date: 2026-10-16  
Scope: checklist items 4–20 + extended review (secrets, RBAC, injection, headers).

**Quick reel checklist (21 items):** see `notes/SECURITY_CHECKLIST_21.md` and `scripts/security_smoke_untrusted.sh`.

---

## Summary

| Severity | Found | Fixed in repo |
|----------|-------|----------------|
| **Critical** | 6 | 6 |
| **High** | 5 | 2 |
| **Medium** | 8 | 3 |
| **Low** | 6 | 0 (documented) |

---

## Critical (fixed unless noted)

### C1 — Unauthenticated admin analytics (`/api/admin/stats`)
- **Impact:** Anyone could read user emails, application PII, employer stats.
- **File:** `api/server.py` → `admin_stats`
- **Fix:** `@require_auth` + `@require_admin`

### C2 — Unauthenticated CRM APIs
- **Impact:** Leak of CRM companies, contacts, pipeline.
- **File:** `api/server.py` → `/api/crm/*`
- **Fix:** `@require_auth` + `@require_admin`

### C3 — Unauthenticated full application dump (`GET /api/applications`)
- **Impact:** All applicants exposed.
- **Fix:** Auth required; scope by seeker / employer / admin.

### C4 — IDOR on seeker dashboard & saved jobs
- **Impact:** `?user_id=1` (default) exposed any user’s applications/saves.
- **Files:** `seeker_dashboard`, `get_saved_jobs`, `save_job`, `unsave_job`
- **Fix:** `@require_auth`; use `request.user_id` only.

### C5 — Unauthenticated delete application
- **Impact:** Anyone could delete any application by ID.
- **Fix:** `@require_auth` + owner/admin check.

### C6 — Weak application status update
- **Impact:** Bearer header checked but JWT not verified; no ownership check.
- **Fix:** `@require_auth` + employer/owner/admin rules.

---

## High

### H1 — Registration role escalation
- **Impact:** Client could send `role: admin` at signup (if DB accepted it).
- **File:** `api/server.py` → `register`
- **Fix:** `allowed_registration_role()` in `api/security.py` (only `user` / `employer`).

### H2 — Default JWT/secret in production
- **Impact:** Forged tokens if env not set.
- **File:** `api/server.py`
- **Fix:** `enforce_production_secrets()` — **fails fast** when `FLASK_ENV=production` and secret weak/missing.
- **Action:** Set `JWT_SECRET` ≥ 32 chars on Railway.

### H3 — Telegram bot token in git history
- **Impact:** Token was committed in `bot/bot_config.py` (later removed).
- **Action:** **Revoke token in BotFather** and issue new `TELEGRAM_BOT_TOKEN`. Consider `git filter-repo` if repo is public.

### H4 — Open profile by user id (`GET /api/user/profile`)
- **Impact:** Email enumeration for any `user_id`.
- **Fix:** Auth required; admin-only override via query param.

### H5 — Recommendations IDOR (`user_id` query param)
- **Fix:** Auth + only self or admin.

---

## Medium

| # | Topic | Finding | Recommendation |
|---|--------|---------|----------------|
| 7 | Input validation | Chatbot sanitized; job search uses bound params | Extend validation on employer HTML fields |
| 8 | XSS | `escHtml` in templates; CSP on HTML | Remove `'unsafe-inline'` from CSP when JS bundled |
| 9 | SQL injection | Dynamic `UPDATE` uses allowlisted column names only | Keep allowlists; prefer ORM on Postgres migration |
| 10 | DB rules | SQLite file on disk | Encrypt volume; move to managed Postgres + network ACL |
| 11 | Rate limiting | Flask-Limiter on many routes | Add stricter limits on `/api/admin/*`, auth |
| 12 | Spend cap | Not in app | Set Stripe billing alerts + Railway spend cap in dashboard |
| 13 | File uploads | Resume/KYC: ext + magic bytes + size | Serve uploads outside web root; virus scan optional |
| 14 | CSRF | JWT in `Authorization` header (not cookie) for API | Add CSRF tokens if session cookies used on forms |
| 15 | CORS | `ALLOWED_ORIGINS` | Never use `*` in production |

---

## Low / operational

| # | Topic | Status |
|---|--------|--------|
| 16 | HTTPS | `_force_https` when `FLASK_ENV=production`; **HSTS** header added |
| 17 | Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, CSP |
| 18 | Secure cookies | APIs use Bearer JWT — no auth cookies today |
| 19 | Debug mode | `app.run(debug=False)`; set `FLASK_ENV=production` on deploy |
| 20 | Prod settings | Use `gunicorn.conf.py`; run `enforce_production_secrets()` |

---

## Checklist mapping (image items 4–20)

| Item | Status after this pass |
|------|-------------------------|
| 4 protect admin routes | **Fixed** (API); `/admin` HTML still public — protect via edge auth or login gate |
| 5 add auth | **Improved** on sensitive APIs |
| 6 user perms | **Improved** RBAC on applications, admin, CRM |
| 7 sanitize inputs | Partial (chatbot + forms) |
| 8 XSS | Partial (CSP + escaping) |
| 9 SQL injection | Good (parameterized); allowlisted dynamic UPDATE |
| 10 DB rules | **Ops** — migrate to managed DB |
| 11 rate limiting | Present; tune per route |
| 12 spend cap | **Ops** — Stripe/Railway consoles |
| 13 secure uploads | Partial (type/size/magic) |
| 14 CSRF | N/A for Bearer API; needed if cookie sessions |
| 15 CORS | Configured |
| 16 HTTPS | Enforced + HSTS in prod |
| 17 security headers | Added |
| 18 secure cookies | N/A today |
| 19 disable debug | OK |
| 20 prod settings | Documented + production secret guard |

---

## Recommended next steps

1. Rotate **Telegram** token (git history exposure).  
2. Create first **admin** user only via DB/script, never via public register.  
3. Protect **`/admin`** page (redirect to login + verify admin JWT in template or server-side session).  
4. Enable **Cloudflare** WAF + bot fight on `/api/chatbot`.  
5. Add **Stripe webhook** signature verification if not already wired.  
6. **Dependabot** + monthly dependency review (item 108).

---

## Files touched in security fix

- `api/security.py` — production secret guard, `require_admin`, registration roles  
- `api/server.py` — route protections, HSTS  
- `notes/SECURITY_AUDIT.md` — this document  
