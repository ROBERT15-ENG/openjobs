# Security checklist (21 items)

Mapped to the common “ship your app” reel checklist.  
**Legend:** ✅ Done in repo · ⚠️ Partial / ops · ❌ Gap · N/A

| # | Item | Status | OpenJobs notes |
|---|------|--------|----------------|
| 1 | Secure API keys | ✅ | Stripe, JWT, SMTP, Google, Sentry via env only |
| 2 | Hide `.env` files | ✅ | `.gitignore` includes `.env`, `*.env` |
| 3 | Never hardcode secrets | ⚠️ | Dev JWT fallback if unset; **production fails fast** (`enforce_production_secrets`) |
| 4 | Add authentication | ✅ | JWT Bearer on sensitive APIs |
| 5 | Verify permissions server-side | ✅ | `require_auth`, `require_admin`, employer/owner checks |
| 6 | Don’t trust frontend user IDs | ✅ | `request.user_id` from JWT; saved jobs/dashboard fixed |
| 7 | Isolate user data | ✅ | `data_protection.public_user` / `public_application` |
| 8 | Lock down database | ⚠️ | SQLite file on disk — use encrypted volume or managed Postgres in prod |
| 9 | Secure Firebase / Supabase | N/A | Not used |
| 10 | Protect admin routes | ⚠️ | APIs admin-only; `/admin` UI JWT gate (see `notes/ADMIN_OPS.md`) |
| 11 | Disable production debug | ✅ | `debug=False`; `FLASK_ENV=production` behaviors |
| 12 | Hide detailed errors | ✅ | API 500/uncaught: generic message in production (`server.py` handlers) |
| 13 | Validate inputs server-side | ⚠️ | Auth/password rules; allowlisted PATCH; extend employer HTML fields |
| 14 | Sanitize user content | ⚠️ | `escHtml` in templates; CSP; chatbot sanitization |
| 15 | Secure file uploads | ✅ | Ext, size, magic bytes; `uploads/` not in git |
| 16 | Prevent SQL injection | ✅ | Parameterized queries; allowlisted dynamic UPDATE columns |
| 17 | Rate-limit login and signup | ✅ | Register 5/hr, login 10/min, forgot-password limits |
| 18 | Check Git history for secrets | ⚠️ | Telegram token was committed historically — **rotate**; scan with `gitleaks` |
| 19 | Security headers; restrict CORS | ✅ | CSP, HSTS, frame deny; `ALLOWED_ORIGINS` |
| 20 | Test as untrusted user | ✅ | `scripts/security_smoke_untrusted.sh` |
| 21 | Ask your AI agent | ✅ | You’re here |

## Admin / sensitive route limits (this pass)

| Route group | Limit |
|-------------|--------|
| `/api/admin/*` (read) | 120 / hour |
| `/api/admin/users` PATCH | 60 / hour |
| `/api/crm/*` | 120 / hour |
| `/api/scrape` POST | 20 / hour |
| `/api/scrape/scheduled/start` | 10 / hour |

## Run untrusted-user smoke test

```bash
# Server must be running (default http://localhost:5700)
./scripts/security_smoke_untrusted.sh
BASE_URL=https://your-app.example ./scripts/security_smoke_untrusted.sh
```

## Related docs

- `notes/SECURITY_AUDIT.md` — deeper audit (2026-10-16)
- `notes/ADMIN_OPS.md` — promote admin, ops tab
