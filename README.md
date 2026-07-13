# OpenJobs — AI-Powered Australian Job Board

> Smart job matching with keyword + optional Ollama semantic scoring. Built with Flask, SQLite, and vanilla HTML dashboards.

**Local:** `http://localhost:5700` | **Deploy:** [PRODUCTION.md](./PRODUCTION.md)

---

## Features (current)

### Job seekers
- Search with filters: work type, arrangement, salary, location, category, **visa sponsorship**
- **Easy Apply** — one click uses profile résumé + auto cover letter (upload résumé on profile or job page for best ATS score)
- Match scores with **ELITE / STRONG / WATCHLIST** tiers when signed in
- Save jobs, track applications, job alerts (email when SMTP + cron configured)
- AI tools at `/ai` (résumé score, cover letter, interview prep — Ollama optional)

### Employers
- Post, edit, manage listings (demo mode: free posting until Stripe is enabled)
- Kanban pipeline (stage buttons — not drag-and-drop)
- Applicant notifications via email when SMTP is set
- View counts per job

### Platform
- SEO URLs (`/jobs/<id>/<slug>`), sitemap, JSON-LD
- Companies directory (`/companies`), salary insights (`/salary`)
- JWT auth, pytest CI, job alert matcher script

---

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env
python3 scripts/init_db.py
cd api && python3 server.py
```

Optional: `ollama serve` on your PC for semantic AI features.

---

## Test accounts (from `scripts/init_db.py`)

| Role | Email | Password |
|------|-------|----------|
| Seeker | `demo@openjobs.com` | `TestPass123` |
| Employer | `employer@openjobs.com` | `Employer123` |
| Admin | `admin@openjobs.com` | `admin123` (override with `ADMIN_PASSWORD`) |

---

## Environment variables

See [.env.example](./.env.example) and [PRODUCTION.md](./PRODUCTION.md).

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | JWT signing (required in production) |
| `BASE_URL` | Public site URL for emails and SEO |
| `CORS_ORIGINS` | Allowed API origins (comma-separated) |
| `SMTP_*` | Email delivery |
| `OLLAMA_URL` | Local AI (optional) |
| `STRIPE_*` | Payments (**deferred** — demo mode without keys) |

---

## API highlights

| Method | Endpoint | Notes |
|--------|----------|-------|
| `GET` | `/api/jobs?visa=1&sort=featured` | Visa filter + sort |
| `POST` | `/api/applications` | `{ job_id, auto_cover_letter: true }` for easy apply |
| `GET` | `/api/admin/export/applications` | CSV export (admin) |
| `POST` | `/api/admin/job-alerts/run` | Manual alert matching |

Full route list: blueprint modules under `api/blueprints/`.

---

## Job alert cron

```bash
python3 scripts/match_job_alerts.py --since-hours 24
```

Schedule hourly in production (see PRODUCTION.md).

---

## AI matching

1. Keyword overlap scores jobs instantly (`semantic_matcher.py`)
2. Ollama rescoring for borderline matches when `OLLAMA_URL` is reachable
3. UI tiers: **ELITE** 80%+, **STRONG** 70%+, **WATCHLIST** 50%+

---

## Project structure

```
api/
  app_factory.py, server.py
  blueprints/     # auth, jobs, applications, seeker, employer, admin, ai, pages
  semantic_matcher.py, job_alert_matcher.py
templates/        # index, job, user, employer, admin, …
scripts/          # init_db.py, match_job_alerts.py
tests/            # pytest suite
```

---

## Testing

```bash
pytest tests/ -q
```

---

## Roadmap (not yet live)

- Stripe payments (posting fees, featured listings)
- OAuth (Google / LinkedIn)
- Job scrapers / external inventory
- Interview scheduling, employer messaging
- PostgreSQL, Redis sessions

See [CHANGELOG.md](./CHANGELOG.md) for release history.
