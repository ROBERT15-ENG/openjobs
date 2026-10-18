# Production readiness (19 items)

| # | Item | Status |
|---|------|--------|
| 1 | Real login & logout | JWT login; token stored on login; `/api/auth/logout` + seeker/employer sign out |
| 2 | Password reset | `/forgot-password`, `/reset-password`, APIs wired |
| 3 | Email verification | Confirm link + resend; auto-confirm when SMTP not configured (dev) |
| 4 | Loading states | Job skeletons, dashboard placeholders |
| 5 | Empty states | Home, employer, user dashboards |
| 6 | Clear error messages | API messages + UI alerts / inline login errors |
| 7 | Form validation | Client + server password rules; login field errors |
| 8 | Rate limiting | Flask-Limiter on auth and sensitive routes |
| 9 | Database backups | `scripts/backup_database.sh` (cron on host) |
| 10 | Row-level security | SQLite: enforced in app (`employer_id`, `require_auth`, `data_protection`) — not DB RLS |
| 11 | API keys off frontend | No Stripe/JWT secrets in templates; checkout server-side only |
| 12 | Mobile layout | Responsive grids; user nav collapses; mobile CTA on home |
| 13 | Custom 404 | `templates/404.html` |
| 14 | Analytics | GA4 via `site.js` after cookie consent |
| 15 | Error tracking | Optional `SENTRY_DSN` → `api/monitoring.py` |
| 16 | Privacy policy | `/privacy` |
| 17 | Terms | `/terms` |
| 18 | Delete account | `/api/user/delete-account` + Settings tab on `/user` |
| 19 | Onboarding | `/onboarding` wizard after register/login |
