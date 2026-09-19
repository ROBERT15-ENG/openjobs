# OpenJobs — AI-Powered Australian Job Board

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
- 📋 **Employer dashboard** — post, edit, and manage job listings with pricing (Standard $99 / Premium $199 AUD via Stripe)
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
```

Open `http://localhost:5700` in your browser.

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

### Jobs
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/jobs` | Search/filter jobs |
| `POST` | `/api/jobs` | Post job (auth required) |
| `GET` | `/api/jobs/<id>` | Job detail |
| `PATCH` | `/api/jobs/<id>` | Update job (owner or admin) |
| `DELETE` | `/api/jobs/<id>` | Soft-delete job (owner or admin) |
| `PATCH` | `/api/jobs/<id>/view` | Increment view count |

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

---

## 🗄️ Database

SQLite at `jobs.db` (override with `DATABASE_URL`). The schema lives in `api/db_schema.py`
and is applied automatically at startup: missing tables and columns are added, existing data
is left untouched. Run it by hand with `python api/db_schema.py`. Key tables:

**`users`** — job seekers and employers
**`jobs`** — all job listings (soft delete: `is_active=0`)
**`applications`** — job applications with ATS scores
**`saved_jobs`** — jobs saved by seekers
**`job_alerts`** — email alert preferences
**`skills_taxonomy`** — 42 skills with aliases and demand scores

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
│   └── semantic_matcher.py  # AI matching engine
├── templates/               # HTML pages (served manually)
│   ├── index.html           # Public job search
│   ├── job.html             # Job detail + apply
│   ├── user.html            # Seeker dashboard
│   └── employer.html        # Employer dashboard + ATS
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
