# OpenJobs — AI-Powered Job Board for Kenya

> The smarter job board that matches candidates to roles using semantic AI — not just keyword searches. Built with Flask, SQLite, and Ollama.

**Live at:** `http://localhost:5700` | **Docs:** [OpenJobs Code Schematic](./OpenJobs_CodeSchematic.pdf)

---

## ✨ Features

### For Job Seekers
- 🔍 **Smart job search** with filters: work type (Full-time/Part-time/Internship/Contract), arrangement (Remote/Hybrid/On-site), salary, location, category
- 🤖 **AI-powered matching** — resume → ranked job recommendations using semantic similarity (Ollama), with clear skill gap analysis
- 💾 **Save jobs** and track applications from a personal dashboard
- 📄 **One-click apply** with auto-generated cover letter from your profile skills
- 📊 **ATS compatibility score** — know how well your skills match each role before applying

### For Employers
- 📋 **Employer dashboard** — post, edit, and manage job listings with pricing (Standard KSh 5,000 / Premium KSh 12,000 via Stripe; amounts configurable with `PLAN_PRICE_*_CENTS`)
- 📥 **Application pipeline** — kanban board (Applied → Screening → Interview → Offer → Hired / Rejected) with drag-and-drop
- 👀 **View tracking** — see how many times each job has been viewed
- �✉️ **Email notifications** — applicants get confirmation, employers get alerts (SMTP/SendGrid)
- 🔒 **Multi-tenant isolation** — employers only ever see their own data

### AI Engine
- **Keyword-first + Ollama semantic rescoring** — 70% fewer LLM calls vs. pure semantic search; Ollama only fires for borderline 1–3 keyword score cases
- **Confidence tiers:** ELITE (80%+), STRONG (70%+), WATCHLIST (50%+)
- **Skill taxonomy** with 60+ aliases (JS→JavaScript, ML→machine learning, ReactJS→React, etc.)
- **Economic calendar boost** — major news events influence scoring weights

---

## 🏗️ Architecture

```
                    ┌─────────────────────────────────────┐
                    │              Flask API               │
                    │         (api/server.py  port 5700)   │
  Browser ─────────│  Auth  Jobs  Apps  ATS  AI  Email   │
                    │  JWT   SQLite  Ollama  SMTP  Stripe │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │   Semantic Matcher                  │
                    │  (keyword → Ollama fallback)        │
                    │   api/semantic_matcher.py            │
                    └─────────────────────────────────────┘
```

**Key files:**
| File | Purpose |
|------|---------|
| `api/server.py` | Flask app — all routes, auth, database |
| `api/semantic_matcher.py` | AI job-candidate matching engine |
| `templates/employer.html` | Employer dashboard (kanban, post job, settings) |
| `templates/user.html` | Seeker dashboard (applications, saved jobs) |
| `templates/index.html` | Public job search + listings |
| `email_notifier.py` | SMTP email wrapper |

Full API schematic: [OpenJobs_CodeSchematic.pdf](./OpenJobs_CodeSchematic.pdf)

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- [Ollama](https://ollama.com) running locally (`ollama serve`) — optional, for AI matching

### Install & Run

```bash
# 1. Clone / navigate to project
cd jobseek

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and edit environment variables
cp .env.example .env
# Edit .env and set your SMTP credentials, Stripe key, Telegram token

# 4. Start Ollama (optional, for AI features)
ollama serve
ollama pull gemma3:4b   # or your chosen model

# 5. Run the server (creates jobs.db and all tables on first start)
python api/server.py

# 6. (staging only) fill the database with realistic demo ads, companies and reviews
python api/seed_demo.py            # idempotent; --force to reseed
```

Open `http://localhost:5700` in your browser. The seed script creates demo logins
(`seeker@demo.openjobs.local`, `employer.atlassian@demo.openjobs.local`, ... — password `Demo1234!`).
Never run it against a production database.

### Job alert digests

Instant alerts are sent as soon as a matching ad is posted. Daily digests are sent by a
cron job (or Railway/Render scheduled task):

```bash
python api/alerts.py            # add --dry-run to see what would be sent
```

---

## 🔑 Accounts & Roles

The database starts empty. Register a seeker at `/register` and an employer at `/employer`.
Passwords need 8+ characters with an uppercase letter, a lowercase letter and a number.

- If SMTP is **not** configured, new accounts are auto-confirmed (the confirmation link is
  printed to the server log). With SMTP configured, users must click the emailed link first.
- The `admin` role cannot be self-assigned. Promote an existing account with:

```bash
python api/db_schema.py --admin you@example.com
```

Then sign in at `/login` and open `/admin`.

### Admin dashboard (`/admin`)

Everything needed to run the board day to day, backed by `api/admin_routes.py`:

| Tab | What you can do |
|-----|-----------------|
| **Overview** | KPIs (live ads, seekers, employers, applications, alerts, reviews), 30-day trend chart, live ads by classification and county, top employers, recent sign-ups/reviews, and an *attention* list (expired ads still live, unclassified ads, pending KYC, SMTP not configured…) with one-click fixes |
| **Jobs** | Every ad including inactive/expired; search by title/company/employer/#id; activate, deactivate, feature, extend (+7/30/90 days), reclassify, delete; bulk actions on selected rows |
| **Users** | Search/filter seekers, employers and admins; change role, confirm email, set KYC status and posting plan; **suspend** (signs the user out everywhere, blocks login, takes their ads offline) and delete |
| **KYC review** | Approve or reject identity submissions |
| **Reviews** | Moderate company reviews — hide (excluded from public profiles and ratings) or delete |
| **Job alerts** | See all saved searches, pause/resume/delete, trigger the daily digest |
| **System health** | Runtime + DB info, which integrations are configured (SMTP, Stripe, M-Pesa, Google, Redis, Telegram — never the values), a maintenance checklist, and tasks: deactivate expired ads, backfill county/classification, rebuild the FTS index, purge orphans / stale unconfirmed accounts, integrity check, vacuum, seed/remove demo data (non-production only) |
| **Settings** | Runtime switches, no restart: maintenance mode (non-admin writes get 503 + site banner), announcement banner, allow free posting, require KYC to post, default ad lifetime, max live ads per employer |
| **Audit log** | Who did what, to which record, from which IP — every admin mutation is recorded |

Role and suspension are checked against the database on every authenticated request, so
demoting or suspending a user takes effect immediately even if they hold a valid token.
Admin endpoints are exempt from the public per-IP rate limits.

### Creating an Employer Account (UI)
1. Go to `http://localhost:5700/employer`
2. Click **Register** → fill in your details
3. On first login, go to **Settings** → fill in Company Name + Primary Location
4. Next time you **Post a Job**, those fields pre-fill automatically

---

## 📂 Environment Variables

Copy `.env.example` to `.env`:

```bash
# Flask
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Ollama (optional — AI matching fails gracefully if unavailable)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b
JOBSEEK_AI_ENABLED=true

# Email (optional — emails log to console if not set)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASS=your-sendgrid-api-key
FROM_EMAIL=jobs@openjobs.com

# Stripe (optional — checkout returns 503 demo mode if not set)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...

# Telegram Bot (optional)
TELEGRAM_BOT_TOKEN=123456:ABC...
```

---

## 📦 API Overview

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Login → JWT token |
| `POST` | `/api/auth/register` | Register seeker |
| `POST` | `/api/auth/register-employer` | Register employer |
| `POST` | `/api/auth/logout` | Revoke token |
| `GET` | `/api/auth/me` | Current user profile |

### Jobs & search
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/jobs` | Search. Params: `q` (FTS5 relevance-ranked, highlighted `snippet`), `location` (town/estate/county/`Remote`), `state` (county name, e.g. `Nairobi`, `Uasin Gishu`), `classification`, `subclassification`, `work_type` & `work_arrangement` (csv), `salary_min`/`salary_max`, `date_listed` (days), `company`, `sort` (`relevance`\|`date`\|`salary_desc`\|`salary_asc`), `page`, `limit`, `facets=1` |
| `GET` | `/api/jobs/<id>` | Job detail + `similar` jobs + canonical `url` |
| `POST` | `/api/jobs` | Post job (employer/admin). Accepts `classification`/`subclassification`; `state` is derived from `location` |
| `PATCH` | `/api/jobs/<id>` | Update job (owner or admin) |
| `DELETE` | `/api/jobs/<id>` | Soft-delete job (owner or admin) |
| `PATCH` | `/api/jobs/<id>/view` | Increment view count |
| `GET` | `/api/classifications` | Classification taxonomy with live counts, plus market metadata (`country`, `currency`/`currency_symbol`, `salary_period`, `regions` = 47 counties, `salary_bands`) |
| `GET` | `/api/suggest?q=` | Keyword autocomplete (titles, skills, companies) |
| `GET` | `/api/locations/suggest?q=` | Location autocomplete |

Pages: `/jobs` (search results with facets and split-view preview), `/jobs/<title-slug>-<id>`
(canonical job URL; stale slugs 301), `/companies`, `/companies/<slug>`.

### Saved searches / job alerts
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/alerts` | Signed-in user's alerts |
| `POST` | `/api/alerts` | Create (`keywords`, `location`, `classification`, `work_type`, `work_arrangement`, `salary_min`, `frequency` = `daily`\|`instant`) |
| `PATCH` | `/api/alerts/<id>` | Pause/resume (`is_active`), change `frequency`/`name` |
| `DELETE` | `/api/alerts/<id>` | Delete |

### Companies & reviews
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/companies` | Companies with live ads (`q`, `sort` = `jobs`\|`rating`\|`name`) |
| `GET` | `/api/companies/<slug>` | Profile: open jobs, rating distribution, anonymous reviews |
| `POST` | `/api/companies/<slug>/reviews` | Write/update your review (auth; one per company) |

### Applications & ATS
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/applications` | Apply to job |
| `GET` | `/api/applications` | Own applications (seeker) / applicants to own jobs (employer) / all (admin) |
| `PATCH` | `/api/applications/<id>` | Change status (job owner/admin; applicant may only `withdrawn`) |
| `GET` | `/api/saved_jobs` | Saved jobs for the signed-in user (also `POST`/`DELETE` with `job_id`) |
| `GET` | `/api/dashboard/seeker` | Seeker dashboard stats + recommendations |
| `GET` | `/api/employer/applications` | Employer's applicants |
| `GET` | `/api/kanban/<job_id>` | Pipeline stages |
| `POST` | `/api/kanban/<job_id>/move` | Move candidate stage |

### AI & Matching
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/skills` | Full skills taxonomy |
| `GET` | `/api/ai/ollama/status` | Ollama health check |
| `POST` | `/api/resume/upload` | Upload resume → extract skills |

### Payments
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/pricing` | Pricing plans |
| `POST` | `/api/payment/checkout` | Stripe checkout session |

### Admin (role `admin`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/admin/overview` | KPIs, trends, breakdowns, recent activity, attention items |
| `GET` | `/api/admin/users` | `q`, `role`, `status` (active/suspended/unconfirmed/kyc_pending), `sort`, `page` |
| `PATCH` `DELETE` | `/api/admin/users/<id>` | `role`, `is_suspended`, `suspended_reason`, `email_confirmed`, `kyc_status`, `plan` / delete |
| `GET` | `/api/admin/jobs` | `q`, `status` (active/inactive/expired/featured/unclassified), `employer_id`, `sort`, `page` |
| `PATCH` | `/api/admin/jobs/<id>` | `action`: activate, deactivate, feature, unfeature, extend (`days`), reclassify, delete |
| `POST` | `/api/admin/jobs/bulk` | Same actions over `ids[]` |
| `GET` `PATCH` `DELETE` | `/api/admin/reviews[/<id>]` | Moderation queue; `is_hidden` |
| `GET` `PATCH` `DELETE` | `/api/admin/alerts[/<id>]` | All saved searches; `is_active` |
| `GET` | `/api/admin/system` | Runtime, database, integrations, maintenance checks |
| `POST` | `/api/admin/system/tasks` | `task`: expire_jobs, backfill_jobs, rebuild_fts, purge_unconfirmed, run_digests, purge_orphans, vacuum, integrity_check, seed_demo, purge_demo |
| `GET` `PUT` | `/api/admin/settings` | Runtime switches (see Settings tab) |
| `GET` | `/api/admin/audit` | Audit log, `action` / `admin` filters |
| `GET` | `/api/settings/public` | *(no auth)* announcement + maintenance flag for the frontends |

---

## 🗄️ Database

SQLite at `jobs.db` (override with `DATABASE_URL`). The schema lives in `api/db_schema.py`
and is applied automatically at startup: missing tables and columns are added, existing data
is left untouched. Run it by hand with `python api/db_schema.py`. Key tables:

**`users`** — job seekers and employers
**`jobs`** — all job listings (soft delete: `is_active=0`); `classification`, `subclassification`, `state` power the facets
**`jobs_fts`** — SQLite FTS5 index over jobs, kept in sync by triggers (falls back to `LIKE` if FTS5 is unavailable)
**`applications`** — job applications with ATS scores
**`saved_jobs`** — jobs saved by seekers
**`job_alerts`** — saved searches (`instant` or `daily`), matched by `api/alerts.py`
**`company_reviews`** — anonymous employee reviews (one per user per company); `is_hidden` = moderated out
**`skills_taxonomy`** — 42 skills with aliases and demand scores
**`admin_audit_log`** — every admin mutation (admin, action, target, detail, IP)
**`site_settings`** — runtime switches edited from the admin dashboard

The classification taxonomy and location normalisation live in `api/taxonomy.py`; the query
builder and facet counting in `api/search.py`.

### Kenya launch market

The board is Kenya-first. `api/taxonomy.py` is the single place that encodes the market:

- **Locations** — the `jobs.state` column holds the **county** (one of the 47). `derive_state()` maps
  free-text locations to a county (`"Westlands, Nairobi"` → `Nairobi`, `"Eldoret"` → `Uasin Gishu`,
  `"Mombasa Road, Nairobi"` → `Nairobi`), or to `Remote` / `International` / `Other`. Searching by county
  name (or `"Nairobi County"`) in the *where* box therefore also finds ads listed by town or estate.
- **Salaries** — `salary_min` / `salary_max` are **KES per month** (`salary_currency` defaults to `KES`),
  rendered as `KSh 80,000 – 120,000 /month`. Other currencies are kept and shown as-is.
- **Classifications** — Seek-style list adapted for Kenya (NGO, Development & Humanitarian; Agriculture
  incl. tea/coffee/floriculture; Mobile Money & Fintech; Clinical Officers; Security & Protective Services;
  Boda Boda, Riders & Drivers; CBC/TVET teaching...).
- **SEO** — JobPosting JSON-LD emits `addressCountry: KE`, `addressRegion: <county>`, `unitText: MONTH`;
  the sitemap includes a landing URL per county and per classification. Default `APP_URL` is `https://openjobs.co.ke`.

To launch in another market, change the constants and `REGIONS` / `TOWN_TO_REGION` tables in
`api/taxonomy.py`; the API, search page, sitemap and seed script all read from there.

Schema diagram: [OpenJobs_CodeSchematic.pdf](./OpenJobs_CodeSchematic.pdf)

---

## 🧠 AI Matching Logic

```
1. Seeker uploads resume → skills extracted
2. rank_jobs_for_resume(seeker_id) called
3. For each active job:
   a. keyword_score() → exact + fuzzy skill match (0–10 scale)
      - Skills normalised via 60+ alias map
      - Score 0 → skip Ollama (clear mismatch)
      - Score ≥ 4 → skip Ollama (high confidence)
      - Score 1–3 → ollama_rescore() fires (semantic fallback)
   b. Confidence tier assigned:
      ELITE (80%+) → push alert
      STRONG (70%+) → include
      WATCHLIST (50%+) → include
      < 50% → reject
4. Return jobs sorted by match_score descending
```

---

## 📁 Project Structure

```
jobseek/
├── api/
│   ├── server.py            # Flask app — all routes
│   ├── db_schema.py         # Declarative schema + startup migration + --admin
│   ├── admin_routes.py      # Admin API: users, jobs, reviews, alerts, system tasks, settings, audit
│   └── semantic_matcher.py  # AI matching engine
├── templates/               # HTML pages (served manually)
│   ├── index.html           # Public job search
│   ├── job.html             # Job detail + apply
│   ├── user.html            # Seeker dashboard
│   ├── employer.html        # Employer dashboard + ATS
│   └── admin.html           # Admin dashboard
├── bot/
│   ├── telegram_bot.py      # Telegram bot (/search /remote /visa /top)
│   └── bot_config.py        # Reads TELEGRAM_BOT_TOKEN from the environment
├── diagrams/
│   └── architecture.html    # Interactive architecture diagram
├── public/                  # Static assets (logos, salary calc, etc.)
├── email_notifier.py        # SMTP email wrapper
├── config.py                # Feature flags + Ollama config
├── requirements.txt
├── .env.example
├── README.md
├── ARCHITECTURE.md          # Detailed architecture notes
├── PRODUCTION.md            # Deployment guide
└── OpenJobs_CodeSchematic.pdf  # Full page schematic
```

---

## 🧪 Testing

```bash
# Run a quick API smoke test
curl http://localhost:5700/api/jobs?work_type=internship
curl http://localhost:5700/api/pricing

# Register + log in an employer
curl -X POST http://localhost:5700/api/auth/register-employer \
  -H "Content-Type: application/json" \
  -d '{"name":"Jane","email":"jane@corp.com","password":"Passw0rd","company":"Corp"}'
curl -X POST http://localhost:5700/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"jane@corp.com","password":"Passw0rd"}'
```

---

## 🚢 Deploying to Production

See [PRODUCTION.md](./PRODUCTION.md) for full guide. Key steps:

```bash
# Production WSGI server
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5700 "api.server:app"
```

Recommended hosting: **Railway**, **Render**, or any VPS with Python 3.9+ support.
