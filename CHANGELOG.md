# Changelog

All notable changes to the OpenJobs platform are documented in this file.

---

## Quick review — PR #8 (v2.5.0–2.5.1 product gaps)

**Branch:** `cursor/product-gaps-6b92` → `main`  
**Stripe:** still demo mode (deferred)  
**Tests:** run `pytest tests/ -q` (53 tests)

### What changed (latest)

| Area | Summary |
|------|---------|
| Date posted | `date_posted` on API; `posted_at` set on job create; sort uses `COALESCE(posted_at, created_at)` |
| Distance | `?near=Sydney&radius_km=50` + homepage radius filter; city-centre geocoding |
| Report job | `POST /api/jobs/<id>/report`; admin reports queue |
| Status updates | Kanban moves send emails; seeker withdraw UI; full `/api/applications` list |
| Messaging | Application-scoped threads: `POST/GET /api/conversations` |
| Team accounts | Org created on employer signup; `GET/POST /api/employer/team` |
| Bulk actions | Admin bulk reject; user delete; employer bulk status API |
| Legal | `/cookies` page, footer links, cookie consent banner |

### Prior v2.5.0 items

| Area | Summary |
|------|---------|
| Easy Apply | Homepage + job apply use profile résumé + auto cover letter (`auto_cover_letter: true`) |
| Visa filter | `GET /api/jobs?visa=1` + homepage checkbox |
| Match tiers | ELITE / STRONG / WATCHLIST on job cards when authenticated |
| Emails | Employer notified on apply; seeker notified on status change |
| Admin | `GET /api/admin/export/applications` CSV download |
| Telegram | Fixed job list parsing; `/visa` and `/remote` work |
| Docs | README truth-sync, new PRODUCTION.md |
| Profile | `resume_text` editable via `PATCH /api/user/profile` |

### Breaking / behavior

- Applications without résumé now pull from user profile when available
- Seekers can only set application status to `withdrawn` (employer/admin otherwise)

---

## [Unreleased]

### Added
- `DEPLOYMENT_CHECKLIST.md` — phased pre/post deploy checklist

### Planned
- Stripe live payments
- OAuth (Google, LinkedIn)
- Redis sessions, PostgreSQL

## [2.5.1] - 2026-07-13 — PR #8 follow-up

### Added
- **Date posted**: `date_posted` field; jobs set `posted_at` on create
- **Distance filter**: `?near=&radius_km=` with city geocoding; homepage radius dropdown
- **Report job**: `POST /api/jobs/<id>/report`; admin reports tab
- **Employer–seeker messaging**: conversations + messages API (application-scoped)
- **Team accounts**: organizations + members; employer team invite API
- **Bulk actions**: admin application bulk status, job bulk deactivate, user delete
- **Legal**: `/cookies` page, site footer links, cookie consent banner
- `api/geo_util.py`, `api/job_util.py`, `api/org_util.py`, `api/application_status.py`
- `tests/test_features.py`

### Fixed
- Kanban status moves now trigger seeker status emails
- Seeker dashboard: full applications list, withdraw button, message employer
- Employer register creates organization for team access

## [2.5.0] - 2026-07-13 — PR #8 product gaps

### Added
- **Easy Apply**: `POST /api/applications` with `auto_cover_letter` uses profile résumé + template cover letter
- **Visa sponsorship filter**: `?visa=1` on jobs API + homepage filter
- **Match tiers**: `match_tier` field (ELITE/STRONG/WATCHLIST) on authenticated job listings
- **Featured sort**: `?sort=featured` (uses `is_featured` column for future Stripe premium)
- **NEW badge** on job cards posted within 7 days
- **Employer email** on new application (`send_employer_new_application`)
- **Seeker email** on application status change (`send_application_status_update`)
- **Admin CSV export**: `GET /api/admin/export/applications`
- **PRODUCTION.md** deployment guide
- `api/apply_util.py`, `api/match_util.py`
- `tests/test_gaps.py`

### Fixed
- Homepage quick-apply only sent `job_id` (no résumé/cover letter)
- Telegram bot parsed `/api/jobs` response incorrectly
- README test accounts and oversold features (drag-drop kanban, economic calendar, etc.)
- `PATCH /api/user/profile` now accepts `resume_text`

### Changed
- README rewritten to match implemented features
- Company cards show salary range when available
- Job list sort handled server-side (`newest`, `featured`, `salary_high`, `salary_low`)

### Deferred
- Stripe checkout (demo posting remains free)
- OAuth social login buttons (still show setup message)

## [2.4.0] - 2026-07-13 — PR #6 (merged)

### Sprint 1–6 — Gap fixes

#### Fixed
- **register.html**: employer sign-up uses `POST /api/auth/register-employer` with company field; redirects to `/employer`
- Removed misleading demo-account fallback on registration errors

#### Added
- Job alert matcher (`api/job_alert_matcher.py`) with deduplication via `job_alert_sends`
- Cron script: `python3 scripts/match_job_alerts.py` (`--since-hours`, `--dry-run`)
- `POST /api/admin/job-alerts/run` for manual alert matching
- New job posts notify matching alerts (replaces blast-to-all-seekers)
- AI endpoints: `POST /api/ai/ollama/score/resume`, `.../generate/cover-letter`, `.../interview-prep`
- Ollama optional — keyword/template fallbacks when not running locally
- `/cad` redirects to `/?q=autocad` (legacy CAD page retired)

#### Removed
- Unused `api/scraper_routes.py` (no `scrapers/` package registered)

#### Docs
- `tasks.json` and `ARCHITECTURE.md` synced to actual implementation status

#### Tests
- Sprint 1–6 suite: employer registration, alert matching, AI fallbacks, cad redirect, admin trigger

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
