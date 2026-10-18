# OpenJobs — Product requirements (feature by feature)

**Product:** OpenJobs — AI-powered Australian job board  
**Audience:** Job seekers, employers, platform operators  
**Last updated:** October 2026

---

## 1. Job discovery (public)

| ID | Feature | Description | Acceptance criteria |
|----|---------|-------------|---------------------|
| P-1.1 | Job search & filters | Search by keyword, location, work type, arrangement, salary | `GET /api/jobs` returns paginated list; filters combine with AND logic |
| P-1.2 | Job detail | Title, company, location, salary, description, apply CTA | `/job?id=` or slug; SEO meta per listing |
| P-1.3 | Guest ads | Promoted cards in feed for logged-out users only | `GET /api/ads` empty when JWT present; `FEATURE_ADS` |
| P-1.4 | Company browse | Company list / ratings (where implemented) | `/companies` route |
| P-1.5 | Salary tools | Salary prediction / guide pages | `/salary` |
| P-1.6 | SEO | Sitemaps, robots, canonical URLs, JSON-LD on jobs | `/robots.txt`, `/sitemap-*.xml` |

## 2. Job seeker

| ID | Feature | Description | Acceptance criteria |
|----|---------|-------------|---------------------|
| P-2.1 | Registration & login | Email/password; optional Google | JWT returned; roles `user` / `employer` only at signup |
| P-2.2 | Profile & skills | Update profile; skills from resume | `PATCH /api/user/profile`; resume upload extracts skills |
| P-2.3 | Resume upload | PDF/DOCX; magic-byte validation | `POST /api/resume/upload`; text stored on user |
| P-2.4 | AI job matching | Keyword-first + optional Ollama rescoring | Recommendations on dashboard; confidence tiers |
| P-2.5 | Save jobs | Bookmark listings | `GET/POST/DELETE /api/saved_jobs` scoped to auth user |
| P-2.6 | Apply | Quick apply + cover letter; idempotency | `POST /api/apply/<id>` with `Idempotency-Key` |
| P-2.7 | Applications dashboard | Status history | `/user` + `GET /api/applications` |
| P-2.8 | Data rights | Export, delete account, privacy prefs | `/api/user/data-export`, `delete-account`, `privacy` |
| P-2.9 | KYC (optional flow) | Document upload for verification | `/api/kyc/*` |

## 3. Employer

| ID | Feature | Description | Acceptance criteria |
|----|---------|-------------|---------------------|
| P-3.1 | Employer registration | Separate signup path | `POST /api/auth/register-employer` |
| P-3.2 | Post / edit / delete jobs | CRUD on own listings | Auth + `employer_id` isolation |
| P-3.3 | Featured jobs | Paid highlight flag | `POST /api/jobs/<id>/feature` + Stripe checkout |
| P-3.4 | Applicant pipeline | Kanban stages | `GET/POST /api/kanban/<job_id>` |
| P-3.5 | Applicant view | List applications for employer’s jobs | `GET /api/employer/applications` |
| P-3.6 | View analytics | Job view counts | `PATCH /api/jobs/<id>/view` |
| P-3.7 | Pricing | Standard / Premium tiers | `GET /api/pricing`, Stripe checkout |

## 4. Conversational & channels

| ID | Feature | Description | Acceptance criteria |
|----|---------|-------------|---------------------|
| P-4.1 | Web chatbot | Rule-based job search; optional AI gated | `POST /api/chatbot`; injection/PII guards |
| P-4.2 | Telegram bot | Commands: search, remote, visa, etc. | `bot/telegram_bot.py`; env token |
| P-4.3 | Email notifications | Apply confirm, alerts | SMTP when configured |

## 5. Platform & admin

| ID | Feature | Description | Acceptance criteria |
|----|---------|-------------|---------------------|
| P-5.1 | Health / readiness | Deploy probes | `/api/health`, `/api/ready` |
| P-5.2 | Feature flags | Env-driven toggles | `GET /api/platform/flags` |
| P-5.3 | Admin stats | Aggregated metrics | `/api/admin/stats` — admin only |
| P-5.4 | CRM (internal) | Companies, contacts, pipeline | `/api/crm/*` — admin only |
| P-5.5 | Job ingestion | Scrapers (NSW JobFeed, per-state teaching) | Admin `POST /api/scrape` |

## 6. Trust, legal & marketing site

| ID | Feature | Description | Acceptance criteria |
|----|---------|-------------|---------------------|
| P-6.1 | Privacy & terms | Legal pages | `/privacy`, `/terms` |
| P-6.2 | Cookie consent | Analytics opt-in | Banner + `user_privacy` API |
| P-6.3 | 404 & thank-you | Branded errors and post-conversion pages | `/404`, `/thank-you` |
| P-6.4 | Contact in footer | Address + support email | `CONTACT_*` env vars |

## 7. Out of scope / future (documented)

- Full SEEK/state DET ingestion as sole source of truth for all AU teaching jobs  
- Mobile native apps  
- Real-time chat between seeker and employer  
- Guaranteed visa sponsorship verification (listings are employer-declared)

## 8. Success metrics (recommended)

- Apply completion rate (start → thank-you)  
- Time-to-first-match on dashboard  
- Employer job publish → first application latency  
- 5xx rate and p95 on `GET /api/jobs`
