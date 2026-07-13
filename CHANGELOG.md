# Changelog

All notable changes to the OpenJobs platform are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses semantic versioning for release tags.

## [Unreleased]

### Planned
- OAuth (Google, LinkedIn)
- Interview scheduling UI
- Background job-alert email cron

## [2.3.0] - 2026-07-13

### Phase 4 — SEO, growth & matching

#### Added
- SEO-friendly job URLs: `/jobs/<id>/<slug>` with canonical redirects from `/job.html?id=`
- `JobPosting` JSON-LD structured data on job pages
- Dynamic `/sitemap.xml` and sitemap reference in `robots.txt`
- **Companies** page (`/companies`) with `GET /api/companies/directory`
- **Salary insights** page (`/salary`) with `GET /api/salary/insights`
- Job alerts CRUD: `GET/POST /api/job_alerts`, `PATCH/DELETE /api/job_alerts/<id>`
- Job alerts UI on seeker dashboard
- Personalized match scores on `GET /api/jobs` when authenticated (`optional_auth`)
- ATS fit score (`ats_score`) computed on application submit
- `api/seo_util.py`, `api/ats_util.py`, `optional_auth` decorator

#### Fixed
- **forgot-password.html** and **reset-password.html** wired to auth API
- Homepage sends auth token to jobs API for logged-in match badges
- Recommendation and modal links use SEO job URLs

#### Tests
- Phase 4 test suite: sitemap, companies directory, salary insights, job alerts, match scores, ATS score

## [2.2.1] - 2026-07-13

### UX polish

#### Improved
- **Homepage**: saved-job stars (★) persist on list load for signed-in users; toggle save/unsave from cards and modal
- **Homepage modal**: sticky Apply/Save bar on mobile, focus trap, ARIA dialog labels, keyboard-friendly job cards
- **Job page**: guests see sign-in CTA instead of a misleading apply form; logged-in users see the full form
- **Login**: `?redirect=` param returns users to the job or page they came from after sign-in
- **Seeker dashboard**: applications and overview tabs refresh live data from the API on each visit
- **Employer modals**: focus trap, Escape to close, and ARIA labels on candidate and edit-job dialogs

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
