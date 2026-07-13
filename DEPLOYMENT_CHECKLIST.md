# OpenJobs — Deployment Checklist

Use this before and after every production deploy. Pair with [PRODUCTION.md](./PRODUCTION.md) for commands and env var reference.

**Target:** first public launch (beta OK). Stripe can stay in demo mode until you are ready to charge.

---

## Phase 0 — Before merge & deploy

### Code & PRs

- [ ] **PR #7** (security hardening) reviewed and merged to `main`
- [ ] **PR #8** (product gaps v2.5.x) reviewed and merged (or deploy from that branch knowingly)
- [ ] CI green on `main`: `pytest tests/ -q` and `ruff check api tests`
- [ ] Tag or note the commit SHA you are deploying

### Decisions (write these down)

- [ ] **Domain** chosen (e.g. `https://jobs.yourdomain.com.au`)
- [ ] **Host** chosen (Railway / Render / Fly.io / VPS)
- [ ] **Persistent disk** for SQLite + uploads (not ephemeral container FS)
- [ ] **Email provider** chosen (SendGrid, Mailgun, SES, etc.)
- [ ] **Stripe** — demo mode OK for launch? (posting stays free without keys)

---

## Phase 1 — Secrets & environment

Copy [.env.example](./.env.example) → `.env` on the server (or set vars in host dashboard).

### Required

- [ ] `SECRET_KEY` — 64-char random hex  
  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```
- [ ] `FLASK_ENV=production`
- [ ] `BASE_URL` — exact public URL with `https://` (no trailing slash)
- [ ] `DATABASE_PATH` — persistent path (e.g. `/data/jobs.db`)

### Strongly recommended

- [ ] `ADMIN_PASSWORD` — set **before** `init_db` (overrides default `admin123`)
- [ ] `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `FROM_EMAIL`
- [ ] `CORS_ORIGINS` — your domain only *(after PR #7; until then CORS may be `*`)*

### Optional

- [ ] `OLLAMA_URL` — only if AI runs on same private network
- [ ] `TELEGRAM_BOT_TOKEN` — if using `bot/telegram_bot.py`
- [ ] `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET` — when payments go live

### Verify secrets are not defaults

- [ ] `SECRET_KEY` is **not** `change-me…` or `dev_secret_key_change_in_production`
- [ ] Admin login is **not** `admin@openjobs.com` / `admin123` in production (or password was changed post-init)

---

## Phase 2 — Server setup

### Install & database

```bash
pip install -r requirements.txt
python3 scripts/init_db.py    # first deploy only
```

- [ ] Python **3.11+** on server
- [ ] `uploads/` directory writable (résumé uploads)
- [ ] `DATABASE_PATH` parent directory exists and is backed up
- [ ] `init_db` run once; **not** re-run on every deploy (wipes data unless you know what you are doing)

### Process manager

```bash
gunicorn -w 4 -b 0.0.0.0:5700 --chdir api "server:app"
```

- [ ] Gunicorn (or host equivalent) runs `api/server:app`
- [ ] **Not** `flask run` / `debug=True` in production
- [ ] Worker count appropriate for CPU (2–4 to start)
- [ ] Restart policy on crash (systemd, Docker restart, PaaS auto-restart)

### HTTPS & reverse proxy

- [ ] TLS certificate active (Let’s Encrypt or host-managed)
- [ ] HTTP → HTTPS redirect
- [ ] Proxy forwards `Host` and `X-Forwarded-Proto` (if behind nginx/Caddy)
- [ ] `BASE_URL` matches what users see in the browser

### Cron — job alert emails

```cron
0 * * * * cd /app && DATABASE_PATH=/data/jobs.db python3 scripts/match_job_alerts.py --since-hours 24
```

- [ ] Cron (or host scheduler) runs **hourly**
- [ ] Same `DATABASE_PATH` as the web app
- [ ] Dry-run once: `python3 scripts/match_job_alerts.py --dry-run`

---

## Phase 3 — Smoke tests (post-deploy)

Run against **production URL**. Check each box.

### Health & pages

- [ ] `GET /api/health` → `{"status":"healthy",...}`
- [ ] Homepage loads (`/`)
- [ ] `GET /robots.txt` and `GET /sitemap.xml` return 200
- [ ] Legal pages: `/terms`, `/privacy`, `/cookies`

### Auth

- [ ] Register seeker → login → JWT works
- [ ] Register employer → redirect to `/employer`
- [ ] Admin login works with **your** password
- [ ] Logout invalidates token (if PR #7 merged)

### Seeker flow

- [ ] Search jobs with filters (visa, sort, distance if using city)
- [ ] Easy apply while signed in (`auto_cover_letter`)
- [ ] Saved jobs persist after refresh
- [ ] Job alert create → cron sends email (or check logs)

### Employer flow

- [ ] Post job → appears on homepage
- [ ] Application received → employer dashboard + email (if SMTP on)
- [ ] Status change → seeker gets email (if SMTP on)
- [ ] Kanban move triggers same email as PATCH status

### Admin

- [ ] `/admin` stats load
- [ ] CSV export downloads
- [ ] Job report queue visible (if test report submitted)

### Email (if SMTP configured)

- [ ] Forgot-password email delivers
- [ ] Application confirmation email delivers
- [ ] Job alert email delivers (run matcher manually once)

### Payments (optional)

- [ ] Without Stripe keys: checkout returns demo / 503 message (expected)
- [ ] With Stripe: test mode checkout → webhook → job featured flag

---

## Phase 4 — Security hardening (launch gate)

- [ ] PR #7 merged **or** you accept known risks documented in security PR
- [ ] Default `SECRET_KEY` not in use
- [ ] Admin account password rotated
- [ ] `.env` not committed to git
- [ ] `uploads/` not world-writable; size limits enforced (5 MB résumé)
- [ ] Rate limits active on auth and apply endpoints
- [ ] `robots.txt` disallows `/admin`, `/api/`, dashboards

---

## Phase 5 — Operations (ongoing)

### Backups

- [ ] Daily backup of `DATABASE_PATH` (SQLite file copy)
- [ ] Backup `uploads/` if storing résumés on disk
- [ ] Restore tested once on staging

### Monitoring

- [ ] Uptime check on `/api/health` (UptimeRobot, Better Stack, etc.)
- [ ] Error/log aggregation (host logs or Sentry)
- [ ] Disk space alert on `/data` volume

### Updates

- [ ] Deploy process documented (git pull → pip install → restart gunicorn)
- [ ] Run `pytest tests/ -q` before promote
- [ ] `pip-audit -r requirements.txt` reviewed periodically

---

## Quick reference — one-liner checks

```bash
# Health
curl -sS https://YOUR_DOMAIN/api/health | python3 -m json.tool

# Jobs API
curl -sS "https://YOUR_DOMAIN/api/jobs?limit=1" | python3 -m json.tool

# Stats
curl -sS https://YOUR_DOMAIN/api/stats

# Dry-run job alerts (on server)
DATABASE_PATH=/data/jobs.db python3 scripts/match_job_alerts.py --dry-run --since-hours 24
```

---

## Launch tiers

| Tier | Minimum to ship |
|------|-----------------|
| **Private beta** | HTTPS + `SECRET_KEY` + persistent DB + 1 test employer/seeker flow |
| **Public beta** | Above + SMTP + cron alerts + PR #7 + legal pages + changed admin password |
| **Paid employers** | Above + Stripe live + webhook URL + `PRODUCTION.md` email domain verified |

---

## Rollback

- [ ] Previous container/image or git tag identified
- [ ] Database backup taken **before** deploy
- [ ] Rollback = restore DB (if schema changed) + redeploy previous SHA + restart gunicorn

---

## Related docs

- [PRODUCTION.md](./PRODUCTION.md) — env vars, gunicorn, cron examples
- [README.md](./README.md) — features and test accounts
- [CHANGELOG.md](./CHANGELOG.md) — what shipped in v2.5.x

*Last updated: 2026-07-13 (v2.5.1)*
