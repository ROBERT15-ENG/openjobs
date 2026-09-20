# Changelog

All notable changes to the OpenJobs platform are documented in this file.

---

## v2.7.0 — UX audit: High-severity fixes

**Tests:** `pytest tests/ -q` (117 tests; `tests/test_ux_high.py` covers the items below)

| Finding | Fix |
|---------|-----|
| No way to sign out from the seeker or admin dashboards | Sign-out buttons on both; home header shows Dashboard / Sign out to members and clears expired tokens; a 401 on the dashboard sends the user to login instead of a dead-end error |
| One-click "Apply Now" silently submitted empty applications | Home modal shows a confirmation stating exactly what will be sent; without a saved résumé it hands off to the full apply form; the API refuses an auto-generated letter with no résumé behind it (`400 no_resume`). Job page shows "Application sent" state instead of letting you re-apply into a 409 |
| Headline, Bio, Desired Role, Expected Salary, Work Type and Remote Preference were never saved | New `users` columns (`headline`, `bio`, `desired_role`, `expected_salary`, `pref_work_type`, `pref_remote`) added by migration; API and dashboard wired; profile completion is computed from real data; fake default skills removed |
| Employer listings went live before payment; Standard plan never charged | With `STRIPE_SECRET_KEY` set, every employer listing is stored as `pending_payment` (hidden, no alert emails) and published by the Stripe webhook; "Complete payment" button in My Listings; pricing copy reflects whether payments are on; new `jobs.plan` column. Without a key the site is explicitly free. Admin posts always publish |
| Forgot-password claimed "link sent" with no SMTP | Returns an honest, non-enumerating message (with `SUPPORT_EMAIL` if set) and `email_delivery: false` |
| Login tab misrouted seekers to `/employer`; `?redirect=` allowed off-site targets | Routing uses the server-reported role only; redirect must be a same-origin path |
| Unbranded Flask 404; missing job showed the apply form | `templates/error.html` for 404/403/405/429/500 on HTML routes (API stays JSON); `/jobs/<bad id>` is a real 404; `/?q=` deep links now work (company cards, 404 search, `/cad`) |

Also fixed: employer "new application" email was never sent (`sqlite3.Row.get` error swallowed as a warning).

---

## v2.6.0 — Production hardening

**Tests:** `pytest tests/ -q` (104 tests; `tests/test_hardening.py` covers each item below)

### Runtime

| Area | Summary |
|------|---------|
| Process model | `wsgi.py` + `gunicorn.conf.py` + `Procfile`; Railway start command now runs gunicorn (gthread). `api/server.py` is dev-only and refuses `FLASK_ENV=production` |
| SQLite | Every connection (`api/db.py`) enables WAL, `busy_timeout=5000`, `foreign_keys=ON`. Background scripts use the same helper |
| Storage | `UPLOAD_DIR` env var; `init_db.py` honours `DATABASE_PATH`; docs call out the persistent-volume requirement |
| Logout | Tokens carry a `jti`; logout persists it in `revoked_tokens`, so revocation works across workers and restarts |
| Rate limits | `RATELIMIT_STORAGE_URI` env var (warns in production when left on `memory://`) |
| Ollama | Availability re-probed every `OLLAMA_PROBE_TTL` seconds instead of once at import |
| Logging | `logging` everywhere (no `print`), JSON error responses for `/api/*` (404/405/500), HSTS + Permissions-Policy in production, no localhost CORS origins in production |

### Correctness / security

| Area | Summary |
|------|---------|
| Enumeration | `forgot-password` returns the same 200 whether or not the account exists |
| Email case | Normalised to lower-case at every ingress; case-insensitive unique index; legacy rows lower-cased by `schema_migrate` (collisions preserved); duplicate register → 409 |
| Tokens | Reset/confirm tokens stored as SHA-256 hashes |
| Validation | `api/validation.py`; typed/coerced payloads for job create/update, apply, profile, KYC, job alerts, saved jobs, bulk endpoints. `PATCH /api/jobs` with `"salary_min": "banana"` is now a 400 instead of silently corrupting the row |
| Pagination | `page`/`limit` clamped (`limit=-5` previously produced an unbounded query) |
| Moderation | `jobs.moderation_status`; admin deactivation / report takedown sets `removed`, which employers cannot undo via `PATCH is_active`; admin `reactivate` action added |
| Admin bulk | `delete` now actually deletes (with dependents); user delete cascades alerts/conversations/messages/reports and detaches employer jobs |
| Payments | Checkout requires an employer who owns the job and a known plan; webhook sets `is_featured` for `premium` and respects moderation |
| Time | All timestamps UTC ISO-8601 with `Z` (`api/timeutil.py`); no more `utcnow()` deprecation warnings |

### Email

| Area | Summary |
|------|---------|
| Outbox | `send_email` writes to `email_outbox` and drains in a background thread; `scripts/send_outbox.py` (cron) is the durable backstop with retries. Admin: `GET /api/admin/email/outbox`, `POST /api/admin/email/drain`. No SMTP round-trips inside request handlers |
| Alerts | Per-alert commits in `job_alert_matcher` so the outbox writer never waits on the matcher's lock |

### Search

| Area | Summary |
|------|---------|
| Radius | Indexed bounding-box pre-filter (`idx_jobs_geo`) before haversine; candidate cap raised from 500 to 2000 |

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

---

## Quick review — PR #7 (v2.4.1 security hardening)

**Branch:** `cursor/security-hardening-6b92` → `main`  
**Tests:** 47 passing (`pytest tests/ -q`) — includes 7 new security tests  
**CI:** ruff, pytest, pip-audit (now fails on CVEs)

### What to focus on when reviewing

| Area | Files | Reviewer note |
|------|-------|---------------|
| Auth / roles | `api/auth_utils.py`, `api/blueprints/jobs.py`, `employer.py` | Seekers can no longer post jobs; `employer_id` only on employer accounts |
| XSS | `api/seo_util.py`, `templates/user.html` | JSON-LD `<` escaped; skill tags use `escHtml()` |
| Config / deploy | `api/app_factory.py`, `.env.example` | **Breaking in prod:** must set `SECRET_KEY`; optional `CORS_ORIGINS`, `ADMIN_PASSWORD` |
| AI abuse | `api/blueprints/ai.py` | All AI POST routes now require login + rate limits |
| Applications | `api/blueprints/applications.py` | Seekers may only set status → `withdrawn` |
| Payments | `api/blueprints/payments.py` | Webhook checks `user_id` owns job; generic error messages |
| Emails | `email_notifier.py`, `auth.py` | Dynamic HTML content escaped |
| Uploads | `api/blueprints/auth.py` | File size checked **before** disk write |
| CI | `.github/workflows/ci.yml` | `pip-audit` no longer ignored (`\|\| true` removed) |

### Breaking / behavior changes

- `POST /api/jobs` → **403** for seeker tokens (was allowed)
- `POST /api/ai/ollama/*` → **401** without auth (was public)
- `PATCH /api/applications/<id>` → seekers rejected unless status is `withdrawn`
- Production boot → **fails** if `SECRET_KEY` is missing or default
- CORS → no longer `*`; defaults to `BASE_URL` + localhost

### Deploy checklist (production)

```bash
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
export FLASK_ENV=production
export ADMIN_PASSWORD=<strong-password>   # optional; avoids default admin123
export CORS_ORIGINS=https://yourdomain.com
```

### Deferred (not in this PR)

- Redis JWT blocklist / shared rate limits
- HttpOnly cookie sessions (replace `localStorage` JWT)
- OAuth, live Stripe payments, full CSP

---

## [Unreleased]

### Added
- `DEPLOYMENT_CHECKLIST.md` — phased pre/post deploy checklist

### Planned
- Redis-backed JWT blocklist and rate limiting
- Stripe live payments
- LinkedIn OAuth
- PostgreSQL

## [2.5.2] - 2026-07-14 — PR #8 merge strong attrs

### Added (from PR #7 security + ekip)
- **HttpOnly `oj_session` cookie** on login/register; auth accepts cookie or Bearer
- **Email confirmation** when SMTP is configured (auto-confirm in local/dev)
- **Google Sign-In** `POST /api/auth/google` (requires `GOOGLE_CLIENT_ID` + verified email)
- **Country / region filters** `?country=` `?region=` + `GET /api/regions`
- **KYC profile fields** + `GET/PATCH /api/kyc/*`
- **Rejection email** when application status → `rejected`
- Password complexity (8+ chars, upper/lower/digit)
- Railway deploy configs (`railway.toml`, `railway.json`)
- Merged PR #7 security gates onto this branch
- Full `ensure_schema` upgrade path (tables + columns + employer org backfill)

### Fixed (pre-merge audit)
- Restored `ruff` in `requirements.txt` (CI lint)
- Kanban move verifies `application_id` belongs to `job_id` (IDOR)
- Google auth refuses requests without `GOOGLE_CLIENT_ID`
- Schema migrate creates orgs/messages/reports tables and `posted_at`

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

## [2.4.1] - 2026-07-13 — PR #7

> Security audit P0 + P1 fixes. **47 tests passing.**

### Security — Critical / High

| Fix | Detail |
|-----|--------|
| `SECRET_KEY` | Refuses default/missing secret when `FLASK_ENV=production` |
| JSON-LD XSS | `seo_util.py` escapes `<` in structured data |
| `employer_id` | Only set for `role=employer` (fixes seeker impersonation) |
| Job mutations | `POST/PATCH/DELETE /api/jobs` → `@require_employer` |
| Employer APIs | `/api/employer/*` → employer or admin only |
| CORS | Restricted to `BASE_URL` / localhost (`CORS_ORIGINS` override) |
| AI endpoints | Auth + rate limits on all POST routes |
| Stripe webhook | Verifies `metadata.user_id` owns `job_id` |

### Security — Medium

| Fix | Detail |
|-----|--------|
| Application status | Seekers can only set `withdrawn` |
| Resume upload | Size validated before `file.save()` |
| Emails | `html.escape()` on user/job data in HTML emails |
| Skill tags | `escHtml()` on profile skill add (`user.html`) |
| View counter | Rate limited (`30/min`) |
| Admin seed | `ADMIN_PASSWORD` env + warning for default |
| Error responses | Stripe/payment errors no longer leak internals |

### Added

- Response headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`
- Rate limits: `register-employer`, `forgot-password`, `reset-password`
- `tests/test_security.py` — 7 regression tests
- CI: `pip-audit` fails build on vulnerabilities

### Changed files (18)

`api/app_factory.py` · `api/auth_utils.py` · `api/seo_util.py` · `api/blueprints/{jobs,employer,auth,applications,ai,payments}.py` · `email_notifier.py` · `templates/user.html` · `scripts/init_db.py` · `.env.example` · `.github/workflows/ci.yml` · `tests/{test_security,test_jobs,test_sprint16}.py`

## [2.4.0] - 2026-07-13 — PR #6 (merged)

> Sprint 1–6 gap fixes. **39 tests** at release.

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
