# Production deployment — OpenJobs

> **Full checklist:** [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) — use before every launch.

## Prerequisites

- Python 3.11+
- Domain + HTTPS (e.g. Railway, Render, Fly.io, or VPS)
- Strong secrets (never use defaults in production)

## Environment variables

```bash
# Required
SECRET_KEY=<64-char hex from: python3 -c "import secrets; print(secrets.token_hex(32))">
FLASK_ENV=production
BASE_URL=https://yourdomain.com
CORS_ORIGINS=https://yourdomain.com

# Persistent storage — REQUIRED on PaaS (container disk is wiped on deploy).
# Mount a volume and point both at it.
DATABASE_PATH=/data/jobs.db
UPLOAD_DIR=/data/uploads

# Rate limiting — default memory:// is per-worker and resets on restart.
# RATELIMIT_STORAGE_URI=redis://:password@host:6379/0   (pip install redis)

# Admin bootstrap (when running init_db)
ADMIN_PASSWORD=<strong-password>

# Email (job alerts, apply confirmations, status updates)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASS=<sendgrid-api-key>
FROM_EMAIL=jobs@yourdomain.com

# Stripe — enable when ready (currently demo mode without these)
# STRIPE_SECRET_KEY=sk_live_...
# STRIPE_PUBLISHABLE_KEY=pk_live_...
# STRIPE_WEBHOOK_SECRET=whsec_...

# Ollama — optional, on your machine or private network
# OLLAMA_URL=http://localhost:11434
```

## Setup

```bash
pip install -r requirements.txt
ADMIN_PASSWORD=... python3 scripts/init_db.py   # first run only (refuses default password when FLASK_ENV=production)
```

Schema upgrades are applied automatically at app start (`api/schema_migrate.py`, idempotent).

### Cron

```cron
*/2 * * * * cd /app && DATABASE_PATH=/data/jobs.db python3 scripts/send_outbox.py
0 * * * *   cd /app && DATABASE_PATH=/data/jobs.db python3 scripts/match_job_alerts.py --since-hours 24
```

Email is queued in the `email_outbox` table and drained opportunistically by the
web process; `send_outbox.py` is the durable backstop (retries up to 5 times,
then marks the row `failed`). Inspect with `GET /api/admin/email/outbox`, force
delivery with `POST /api/admin/email/drain`. Both are surfaced in the admin
console under **Operations**, together with a job-alert dry run.

## Run with Gunicorn

```bash
gunicorn -c gunicorn.conf.py wsgi:app
```

`gunicorn.conf.py` reads `PORT`, `WEB_CONCURRENCY` (default 2), `GUNICORN_THREADS`
(default 4) and `GUNICORN_TIMEOUT`. The `Procfile` and `railway.*` files use the
same command. `api/server.py` is the dev server only and refuses to start with
`FLASK_ENV=production`.

## SQLite notes

Every connection enables WAL, `busy_timeout=5000` and `foreign_keys=ON`
(`api/db.py`). WAL needs a local filesystem (not NFS). Back up with
`sqlite3 /data/jobs.db ".backup /backups/jobs-$(date +%F).db"` so the WAL is
included. Move to PostgreSQL when write volume or multi-host deployment demands it.

## Health check

```bash
curl https://yourdomain.com/api/health
```

## Post-deploy checklist

See **[DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)** for the full phased checklist (smoke tests, security, backups, cron).

Quick gates:

- [ ] `SECRET_KEY` set and not default
- [ ] `ADMIN_PASSWORD` changed from `admin123`
- [ ] `DATABASE_PATH` and `UPLOAD_DIR` on a persistent volume
- [ ] HTTPS enabled; `BASE_URL` matches public URL (HSTS is sent when `FLASK_ENV=production`)
- [ ] SMTP configured; `send_outbox.py` cron scheduled; test email delivered
- [ ] Job alert cron scheduled
- [ ] `RATELIMIT_STORAGE_URI` set to Redis if running more than one worker
- [ ] Stripe keys added when payments go live
- [ ] `pytest tests/ -q` passes in CI

## Notes

- SQLite is fine for early production; migrate to PostgreSQL before high traffic.
- Logout is persisted (`revoked_tokens` table keyed by JWT `jti`), so it works across workers and restarts.
- Payments are off until `STRIPE_SECRET_KEY` is configured: listings publish free and the employer UI says so. Once the key is set, every employer listing is held as `pending_payment` until the Stripe webhook (`STRIPE_WEBHOOK_SECRET`) confirms payment, so the webhook endpoint `/api/payment/webhook` must be reachable from Stripe before you enable the key.
- Set `SUPPORT_EMAIL` if SMTP is not configured; it is shown to users who ask for a password reset.
