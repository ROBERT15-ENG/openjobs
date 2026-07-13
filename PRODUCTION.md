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

# Database (optional — defaults to jobs.db in project root)
DATABASE_PATH=/data/jobs.db

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
python3 scripts/init_db.py          # first run only
python3 scripts/match_job_alerts.py # cron: every hour
```

### Cron example (job alert emails)

```cron
0 * * * * cd /app && DATABASE_PATH=/data/jobs.db python3 scripts/match_job_alerts.py --since-hours 24
```

## Run with Gunicorn

```bash
cd api
gunicorn -w 4 -b 0.0.0.0:5700 "server:app"
```

Or from project root:

```bash
gunicorn -w 4 -b 0.0.0.0:5700 --chdir api "server:app"
```

## Health check

```bash
curl https://yourdomain.com/api/health
```

## Post-deploy checklist

See **[DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)** for the full phased checklist (smoke tests, security, backups, cron).

Quick gates:

- [ ] `SECRET_KEY` set and not default
- [ ] `ADMIN_PASSWORD` changed from `admin123`
- [ ] HTTPS enabled; `BASE_URL` matches public URL
- [ ] SMTP configured and test email sent
- [ ] Job alert cron scheduled
- [ ] PR #7 merged before public launch
- [ ] Stripe keys added when payments go live
- [ ] `pytest tests/ -q` passes in CI

## Notes

- SQLite is fine for early production; migrate to PostgreSQL before high traffic.
- PR #7 (security hardening) should be merged before public launch.
- Payments are demo mode until `STRIPE_SECRET_KEY` is configured.
