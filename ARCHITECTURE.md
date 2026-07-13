# OpenJobs — System Architecture

> Last updated: 2026-07-13 (v2.4 sprint)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USERS                                           │
│   Candidates                    Employers                  Public            │
│  ┌──────────┐  ┌──────────┐   ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Job Board│  │  User    │   │ Employer │  │Dashboard │  │ AI Tools │     │
│  │  /       │  │/user    │   │/employer │  │/admin    │  │/ai       │     │
│  └────┬─────┘  └────┬─────┘   └────┬─────┘  └────┬─────┘  └──────────┘     │
│       └─────────────┴──────────────┴─────────────┘                          │
│                              │ HTTP / REST                                   │
│                    ┌─────────▼─────────┐                                    │
│                    │  Flask (app_factory)│  templates/ + static/              │
│                    └─────────┬─────────┘                                    │
└──────────────────────────────┼───────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────────────┐
│  api/blueprints/                                                              │
│  auth · jobs · applications · seeker · employer · admin · payments · ai · pages │
│                                                                              │
│  Middleware: JWT (require_auth) · rate limiting · optional_auth for match %  │
│  Utilities: seo_util · ats_util · semantic_matcher · job_alert_matcher       │
└──────────────────────────┬───────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────────────────────┐
        ▼                  ▼                                  ▼
┌──────────────┐  ┌─────────────────┐              ┌──────────────────┐
│  SQLite      │  │  Ollama (local) │              │  email_notifier  │
│  jobs.db     │  │  optional       │              │  SMTP when set   │
│              │  │  OLLAMA_URL     │              │                  │
│  jobs        │  │  AI routes fall │              │  job alerts      │
│  users       │  │  back to keyword│              │  welcome, apply  │
│  applications│  │  / templates    │              │                  │
│  job_alerts  │  └─────────────────┘              └──────────────────┘
│  job_alert_  │
│    sends     │    scripts/match_job_alerts.py  (cron-friendly)
└──────────────┘
```

## Key API routes

| Area | Endpoints |
|------|-----------|
| Auth | `POST /api/auth/register`, `register-employer`, `login`, `forgot-password` |
| Jobs | `GET/POST /api/jobs`, SEO pages `/jobs/<id>/<slug>`, `GET /sitemap.xml` |
| Seeker | `GET /api/dashboard/seeker`, `GET/POST /api/job_alerts` |
| AI | `GET /api/ai/ollama/status`, `POST .../score/resume`, `.../cover-letter`, `.../interview-prep` |
| Admin | `GET /api/admin/stats`, `POST /api/admin/job-alerts/run` |

## Job alert pipeline

1. Seeker creates alert via dashboard (`job_alerts` table).
2. On new job post, `notify_alerts_for_job()` matches keyword/location/remote/salary.
3. Cron runs `python3 scripts/match_job_alerts.py` for batched catch-up.
4. `job_alert_sends` prevents duplicate emails per alert+job.
5. Email delivery requires `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS` env vars.

## Ollama (local, optional)

- Set `OLLAMA_URL` (default `http://localhost:11434`) on the machine running Ollama.
- When unavailable, AI endpoints return keyword/template fallbacks — the app works without it.
- Semantic ranking in `semantic_matcher.py` uses hybrid keyword + optional Ollama rescoring.

## Deferred / not implemented

- Stripe live payments (webhook stub exists; demo mode)
- OAuth social login
- Job scrapers (removed unused `scraper_routes.py`; no `scrapers/` package)
- `/cad` redirects to `/?q=autocad` (legacy CAD page removed)

## Run locally

```bash
pip install -r requirements.txt
python3 scripts/init_db.py
cd api && python3 server.py
# Optional: OLLAMA_URL=http://localhost:11434 ollama serve
# Optional cron: python3 scripts/match_job_alerts.py --since-hours 24
```

## Tests

```bash
pytest tests/ -q
```

CI runs the same suite on push (see `.github/workflows/ci.yml`).
