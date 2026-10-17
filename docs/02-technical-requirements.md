# OpenJobs — Technical requirements

**Stack owner:** Engineering  
**Last updated:** October 2026

---

## 1. Runtime & languages

| Requirement | Standard |
|-------------|----------|
| Language | Python **3.12+** (3.9+ minimum per README) |
| Web framework | **Flask 3.x** (`api/server.py` monolith) |
| Frontend | Server-rendered HTML + vanilla JS (no SPA framework) |
| Database (current) | **SQLite** (`jobs.db` or `DATABASE_URL` path) |
| Database (target) | PostgreSQL + connection pooling (roadmap) |
| Cache / limits | **Redis** optional (`REDIS_URL`); Flask-Limiter fallback memory |
| AI | **Ollama** HTTP API (optional); graceful degrade if down |

## 2. Deployment

| Requirement | Standard |
|-------------|----------|
| WSGI | **Gunicorn** (`gunicorn.conf.py`) |
| Container | **Docker** + `docker-compose.yml` (web + redis volume) |
| CI | GitHub Actions (`.github/workflows/ci.yml`) |
| Port | **5700** default (`PORT` env) |
| TLS | Edge TLS (Cloudflare/Railway); HSTS in production `FLASK_ENV` |
| Migrations | SQL files in `migrations/` + `scripts/apply_migrations.py` |

## 3. Security (mandatory)

| Area | Requirement |
|------|-------------|
| Auth | JWT (PyJWT); `JWT_SECRET` ≥ 32 chars in production |
| Passwords | bcrypt via Werkzeug |
| RBAC | `user`, `employer`, `admin`; registration allowlist |
| API access | Bearer token; admin routes protected |
| Headers | CSP, `X-Frame-Options`, `nosniff` on HTML |
| CORS | `ALLOWED_ORIGINS` allowlist |
| SSRF | `api/http_safety.py` + `ALLOWED_EGRESS_HOSTS` for scrapers |
| Chatbot | `api/chatbot_security.py` — injection, PII redaction, no public LLM without secret |
| Secrets | `.env` only; never commit tokens (rotate Telegram if leaked) |
| Uploads | 5 MB max; PDF/DOCX magic bytes |

## 4. Integrations

| Service | Env vars | Behavior if missing |
|---------|----------|---------------------|
| SMTP / SendGrid | `SMTP_*`, `FROM_EMAIL` | Log to console |
| Stripe | `STRIPE_*` | Checkout 503 demo mode |
| Ollama | `OLLAMA_URL`, `OLLAMA_MODEL` | Keyword-only matching |
| Telegram | `TELEGRAM_BOT_TOKEN` | Bot not started |
| Google OAuth | `GOOGLE_CLIENT_ID` | Email login only |
| Analytics | `GA_MEASUREMENT_ID` | No script until cookie consent |

## 5. Site & SEO

| Requirement | Implementation |
|-------------|----------------|
| Canonical base | `APP_URL` |
| Templates | Jinja via `api/template_utils.py` for key pages |
| Static assets | `/static/*` (favicon, OG image, `site.js`) |
| Sitemaps | `sitemap_generator.py` |
| Robots | `robots_txt.py` |

## 6. Observability (target)

| Item | Status |
|------|--------|
| `/api/health` | Done |
| `/api/ready` | Done (DB check) |
| Structured logging | Partial (stdout) |
| OTEL / APM | Planned (roadmap) |
| Error tracking (Sentry) | Planned |

## 7. Performance targets (recommended SLOs)

| Endpoint | Target p95 |
|----------|------------|
| `GET /api/jobs` (guest, cached) | < 300 ms |
| `GET /api/jobs` (uncached) | < 800 ms |
| `POST /api/apply` | < 2 s |
| HTML `/` | < 1 s TTFB |

## 8. Browser support

- Last two versions of Chrome, Firefox, Safari, Edge  
- Responsive breakpoints: **768px**, **480px** (primary templates)  
- `prefers-reduced-motion` respected on home

## 9. Compliance & data

- Australian Privacy Act / APPs-oriented practices (see `notes/DATA_PROTECTION.md`)  
- User export and erasure APIs  
- `ADMIN_MASK_PII` for admin list views  
- Cookie banner before non-essential analytics

## 10. Repository conventions

- `PYTHONPATH=.` for `api` imports  
- Branch prefix: `cursor/<name>-ed65`  
- PRs via GitHub; semver notes in `CHANGELOG.md`
