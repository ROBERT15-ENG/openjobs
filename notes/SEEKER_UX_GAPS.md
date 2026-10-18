# Seeker UX gaps — fixes (cursor/seeker-gaps-fix-ed65)

## Wired in this branch

- **Visa filter:** Onboarding sets `openjobs_visa_filter`; home feed chip + `visa=1` on `/api/jobs` (both fetch paths).
- **Profile save:** `/user` PATCHes `/api/user/profile` (name, location, phone, skills, experience).
- **Saved jobs:** Uses auth headers on `/api/saved_jobs` (no `user_id` query).
- **Settings tab:** `data-tab` switching includes Settings; job alerts + change password + resume upload.
- **Nav:** `/companies`, `/salary`, `/learning`, `/premium` pages; mobile menu on dashboard.
- **Google:** `GOOGLE_CLIENT_ID` in `.env.example` and Jinja `google_client_id` on login/register.
- **Demo login:** No redirect without a real JWT when the API is down.
- **Job alerts:** `migrations/003_user_job_alerts.sql` + `/api/user/job-alerts`; onboarding syncs visa preference.

## Still product / ops

- Run `python scripts/apply_migrations.py` (or your deploy step) for `user_job_alerts`.
- Stripe checkout for Visa Premium remains optional (`STRIPE_*`); `/premium` explains rollout.
- Email delivery for job alerts needs a background worker (prefs are stored only).
