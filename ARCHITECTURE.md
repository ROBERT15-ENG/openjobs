# OpenJobs — System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USERS                                           │
│   Candidates                    Employers                  Public            │
│  ┌──────────┐  ┌──────────┐   ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Job Board│  │  User    │   │ Employer │  │Dashboard │  │ Landing  │     │
│  │ (index)  │  │ Portal   │   │  Portal  │  │ (admin)  │  │  Page    │     │
│  │  /       │  │/user    │   │/employer │  │/admin    │  │/about    │     │
│  └────┬─────┘  └────┬─────┘   └────┬─────┘  └────┬─────┘  └──────────┘     │
│       │             │             │             │                          │
│       └─────────────┴──────────────┴─────────────┘                          │
│                              │                                               │
│                    ┌─────────▼─────────┐                                    │
│                    │  Flask Templates   │  static/css, js                    │
│                    │  (jinja2 + vanilla)│                                   │
│                    └─────────┬─────────┘                                    │
└──────────────────────────────┼───────────────────────────────────────────────┘
                               │ HTTP / REST
┌──────────────────────────────▼───────────────────────────────────────────────┐
│                         api/server.py  (Flask, 1120 lines)                    │
│                                                                              │
│  Auth          Jobs          Apps        Resume        Dashboard              │
│  ─────        ────         ─────        ──────        ─────────              │
│  /login       GET /jobs    /apply       /upload       /dashboard/seeker     │
│  /logout      POST /jobs  /apps        /parse        /dashboard/employer    │
│  /register    GET /job     PATCH /app   (skill ext)  /recommendations       │
│  /me          DELETE/job   GET /apps                  /stats               │
│  /profile                                                                  │
│  PATCH /user                                                               │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Middleware: JWT verify → BLOCKED_TOKENS blocklist → require_auth     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Utilities: _decode_token(), _extract_skills_fast() (sqlite3 direct)          │
└──────────────────────────┬───────────────────────────────────────────────────┘
                           │ internal calls
        ┌──────────────────┼──────────────────────────────────┐
        │                  │                                  │
        ▼                  ▼                                  ▼
┌──────────────┐  ┌─────────────────┐              ┌──────────────────┐
│  SQLite      │  │  ai_matcher.py  │              │  ai_filter.py    │
│  jobs.db     │  │  Ollama client  │              │  Ollama client   │
│              │  │                 │              │                  │
│  • jobs      │  │ parse_resume()  │              │ analyze_job()    │
│  • users     │  │ extract_skills()│              │ filter_jobs()    │
│  • apps      │  │ skill_gap()     │              │ save_filtered()  │
│  • companies │  │ semantic_match()│              │                  │
│  • saved     │  │ career_advice() │              │  → /data/*.json  │
│  • skills_   │  │                 │              │                  │
│    taxonomy  │  │  → jobs.resume_ │              │                  │
│  • ai_usage  │  │    text         │              │                  │
│  • job_alerts│  │                 │              │                  │
│  • crm_*     │  └─────────────────┘              └──────────────────┘
│              │
│              │    ┌──────────────────┐  ┌──────────────────────┐
│              │    │  email_notifier  │  │  payment.py          │
│              │    │  (SMTP stub)    │  │  (Stripe/PayPal stub)│
│              │    │                  │  │                      │
│              │    │ send_email()     │  │ create_checkout()    │
│              │    │ notify_applicant │  │ verify_webhook()     │
│              │    │ notify_employer  │  │ get_pricing()       │
│              │    └──────────────────┘  └──────────────────────┘
└──────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  Scrapers  (polling)  │
              │                        │
              │  linkedin_scraper.py   │
              │  indeed_scraper.py    │
              │  remotive.py          │
              │  run_all.py           │
              │  scheduler.py         │
              │                        │
              │  → POST /api/jobs      │
              └────────────────────────┘


┌──────────────────────────────────────────────────────────────────────────────┐
│  Ollama  (localhost:11434)                                                   │
│                                                                              │
│  Models: gemma3:4b (default), llama3.2                                      │
│                                                                              │
│  ai_matcher.py calls:                                                        │
│    • parse_resume()     → structured JSON from resume text                   │
│    • extract_skills()   → keyword fallback                                   │
│    • semantic_job_match() → candidate vs job score + advice                  │
│    • analyze_skill_gap() → matched/missing/extra skills                      │
│    • get_career_advice() → learning path for target role                     │
│                                                                              │
│  ai_filter.py calls:                                                         │
│    • analyze_job()      → is_remote, is_visa, salary, red flags              │
│    • filter_jobs()       → score + filter scams                              │
└──────────────────────────────────────────────────────────────────────────────┘


┌──────────────────────────────────────────────────────────────────────────────┐
│  Telegram Bot  (bot/telegram_bot.py)                                         │
│                                                                              │
│  Polling: BotAPI → python-telegram-bot library                               │
│  Token: from bot_config.py                                                   │
│                                                                              │
│  Commands:                                                                   │
│    /start, /help    → welcome + command list                                 │
│    /search [query]  → GET /api/jobs?q=query                                  │
│    /remote          → GET /api/jobs?remote=true                               │
│    /visa            → GET /api/jobs?visa=true                                │
│    /top             → top rated jobs                                          │
│    /subscribe       → job alerts for user                                     │
│                                                                              │
│  → notifies job seekers when matching jobs posted                             │
│  → notifies employer on new application                                      │
└──────────────────────────────────────────────────────────────────────────────┘


┌──────────────────────────────────────────────────────────────────────────────┐
│  Data Flow Diagrams                                                          │
└──────────────────────────────────────────────────────────────────────────────┘

RESUME → SKILL MATCH → FOR YOU RECOMMENDATIONS
================================================

  Candidate uploads            Flask API                    ai_matcher.py
  resume (PDF/DOCX)             │                              │
        │                        ▼                              │
        ├── POST /api/resume/upload ──────────────────────────────► extract_skills()
        │   file → uploads/                              ◄── 42-skill taxonomy
        │   text extracted (pdfplumber / python-docx)              │
        │   ┌──────────────────────────────────────────────────┐   │
        │   │ _extract_skills_fast() — keyword match           │   │
        │   │ UPDATE users SET skills=? WHERE id=?             │   │
        │   └──────────────────────────────────────────────────┘   │
        │   Background thread: parse_resume() → Ollama           │
        │                                                         │
        ▼                                                         ▼
  For You tab              GET /api/dashboard/seeker      skills stored
  clicked                  ?user_id=ID                      in users.skills
                                  │
                                  ▼
                          ┌──────────────────┐
                          │ SELECT skills FROM│
                          │ users WHERE id=?  │
                          └────────┬─────────┘
                                   │
                                   ▼
                          ┌─────────────────────────────┐
                          │ Score each job:              │
                          │ for each skill in user:     │
                          │   if skill.lower() in       │
                          │      job.skills.lower():     │
                          │     score++                 │
                          └────────────┬───────────────┘
                                       │
                                       ▼
                              Sorted by score ↓
                              Top 4 → dashboard response
                              → frontend For You cards


EMPLOYER POSTS JOB → PAYMENT (stub) → JOB GOES LIVE
================================================

  Employer             Flask API              payment.py        Stripe
  ─────────            ────────              ──────────        ──────
  POST /jobs              │                      │               │
  (with card) ───────────►│                      │               │
                         validate ──────────────►│               │
                         create_stripe_          │               │
                         checkout() ◄────────────┘               │
                         return checkout_url ──────────────────► │
                         (stub — no real call)                   │
                              │                                 │
                         INSERT jobs                            │
                         (status='pending_payment')             │
                              │                                 │
                         Webhook ←────────────────────────────── │
                         (stub — no verification)                │
                              │                                 │
                         UPDATE jobs SET status='active'        │
                              │                                 ▼
                              │                            Stripe Dashboard
                              ▼                                 (manual)


JOB APPLICATION FLOW
====================

  Candidate         Flask API          ai_filter.py        Telegram Bot
  ─────────         ────────          ────────────        ─────────────
  Apply ───────────►│                     │                    │
  POST /apply       │                     │                    │
  (job_id, user_id) │                     │                    │
                    ├── analyze_job() ────►│                    │
                    │◄── is_remote, visa, ─┘                    │
                    │    salary, score, warning                  │
                    ├── INSERT application                      │
                    ├── UPDATE jobs.applications_count++        │
                    ├── send_email() (stub)                     │
                    └── notify_employer() ─────────────────────►│
                                                                notify employer


SCRAPER → DATABASE PIPELINE
============================

  Scheduler (cron)        run_all.py          Flask API           DB
  ───────────────        ─────────           ────────           ───
  every 1hr ─────────────►│                    │                │
                           │                    │                │
                           ├── search_linkedin_jobs()            │
                           ├── search_indeed_jobs()              │
                           ├── search_remotive()                 │
                           │                    │                │
                           └── POST /api/jobs ──►│ INSERT jobs  │
                                                ◄──┘ jobs table


┌──────────────────────────────────────────────────────────────────────────────┐
│  Database Schema (key tables)                                                │
└──────────────────────────────────────────────────────────────────────────────┘

  jobs                    users                   applications
  ──────────              ───────                 ──────────────
  id (PK)                 id (PK)                 id (PK)
  title                   name                    job_id (FK)
  company                 email                   user_id (FK)
  location                phone                   status
  description             skills                  applied_at
  skills (TEXT)           preferred_location      resume_text
  salary                  visa_required           cover_letter
  is_active               experience              match_score
  is_remote               resume_text             notes
  is_visa                 cv_link                 status updated_at
  source                  password_hash
  posted_at               role / plan
  applications_count       created_at
  score (INTEGER DEFAULT 50)

  skills_taxonomy         job_skills               ai_usage
  ───────────────         ──────────               ──────────
  name (PK)               job_id (FK)             endpoint
  aliases                 skill_name              tokens_used
  category                weight                  model
  demand_score                                    created_at

  saved_jobs              job_alerts              notifications
  ───────────             ───────────             ──────────────
  user_id (FK)            user_id (FK)            user_id (FK)
  job_id (FK)             keyword                  message
  saved_at                location                 read
                          remote_only              created_at
                          salary_min
                          active


┌──────────────────────────────────────────────────────────────────────────────┐
│  Missing / TODO Items                                                        │
└──────────────────────────────────────────────────────────────────────────────┘

  CRITICAL (blocking launch)
  ──────────────────────────
  □ SMTP credentials — email_notifier.py has no real credentials
  □ Domain registration — openjobs.com.au not registered
  □ Deployment — runs on localhost:5700, no production host
  □ Payment wiring — Stripe/PayPal stubs never go live
  □ CI/CD pipeline — manual deploys only

  IMPORTANT (full product)
  ─────────────────────────
  □ SEEK scraper — missing (has LinkedIn, Indeed, Remotive)
  □ Mobile nav — hamburger menu not wired
  □ Telegram bot — built but needs token + webhook setup
  □ Resume upload → submitApplication() wiring in job.html
  □ Stripe webhook verification (hmac check)

  NICE TO HAVE
  ─────────────
  □ Redis for session caching
  □ PostgreSQL migration path (dev is SQLite)
  □ Admin dashboard polish
  □ Email templates (HTML)
  □ Job alert SMS (Africa's Talking)
  □ OAuth (Google/GitHub login)
