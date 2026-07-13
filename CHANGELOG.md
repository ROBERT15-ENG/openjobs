# Changelog

All notable changes to the OpenJobs platform are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses semantic versioning for release tags.

## [Unreleased]

### Planned
- Per-job SEO URLs and JSON-LD
- Job alerts API and UI
- Password reset email flow

## [2.2.0] - 2026-07-13

### Phase 3 — Frontend wiring & UX

#### Added
- Admin user list via `GET /api/admin/users`
- Employer **Pipeline (kanban)** tab wired to `/api/kanban/<job_id>` with stage columns and move actions
- Candidate detail modal for employers (resume, cover letter, status actions)
- Public platform stats via `GET /api/stats` (job count, companies, new today)
- Missing page templates: `privacy.html`, `terms.html`, `forgot-password.html`, `reset-password.html`
- Homepage `?job=` deep-link support to open job modal from dashboard links
- Duplicate-application handling (`409`) when applying to the same job twice
- Tests for `/api/stats`, duplicate apply `409`, and cover letter storage

#### Fixed
- **index.html**: navigation links, modal save job API, removed fake match badges for guests, live stats bar
- **job.html**: login redirect for unauthenticated apply, save job API, cover letter stored, resume upload field alignment
- **user.html**: removed silent mock-data fallback, profile save calls `PATCH /api/user/profile`, recommendation links
- **employer.html**: company name prefill from profile, payment flow creates job before Stripe checkout, candidate modal JS, kanban pipeline tab
- **login.html**: demo employer password aligned with seed data (`Employer123`), removed offline demo bypass
- **admin.html**: applications table uses real applicant data, users tab loads from admin API
- **applications API**: stores `cover_letter` and `notes` on apply; admin list includes applicant/job joins
- **register-employer**: saves `company` to user profile
- **resume upload**: returns `resume_text` for apply flow
- **email_notifier**: uses `BASE_URL` env var, rebranded to OpenJobs, fixed welcome email template

#### Changed
- Application status buttons use canonical values (`screening` not `reviewing`/`shortlisted`)
- Hero copy and stats load from API instead of hardcoded values

---

## [2.1.0] - 2026-07-13

### Phase 2 — Architecture, tests & CI

#### Added
- Flask blueprint refactor (`auth`, `jobs`, `applications`, `seeker`, `employer`, `admin`, `payments`, `ai`, `pages`)
- Application status normalization (`applied`, `screening`, `interview`, `offer`, `hired`, `rejected`, `withdrawn`)
- `scripts/migrate_status.py` for legacy status values
- Stripe webhook at `POST /api/payment/webhook`
- Pytest suite (19 tests) and GitHub Actions CI (ruff, pytest, pip-audit)
- `pyproject.toml` with ruff and pytest configuration

#### Removed
- Dead stub routes (CRM, CDN, ML, regions, CAD API)
- Unused root `payment.py` module

---

## [2.0.0] - 2026-07-13

### Phase 1 — Security & portability

#### Added
- Signed JWT authentication (PyJWT) replacing forgeable base64 tokens
- `schema.sql` and `scripts/init_db.py` for database bootstrap
- Complete `requirements.txt` with pinned dependencies
- Admin, dashboard, and application endpoint authorization
- Seed accounts (seeker, employer, admin)

#### Fixed
- Hardcoded macOS paths replaced with project-relative paths
- SQL injection in employer applications filter
- Frontend auth token storage and `Authorization` headers
- Missing `smtplib` import for employer notification emails
- CAD read endpoint restricted to admin + uploads directory

#### Security
- Registration no longer accepts client-supplied `role`
- User-scoped endpoints derive `user_id` from JWT only

---

## [1.0.0] - 2026-06-01

### Initial release

- Flask REST API with SQLite
- Job search, applications, employer dashboard
- AI semantic matching via Ollama (`semantic_matcher.py`)
- HTML dashboards (seeker, employer, admin)
- Telegram bot scaffold (`bot/telegram_bot.py`)
