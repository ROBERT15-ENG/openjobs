# Admin operations

## First admin user

Registration cannot create `admin` roles. Promote an existing account:

```bash
python scripts/promote_admin.py you@example.com
```

Uses `jobs.db` in the repo root, or set `DATABASE_URL` to your SQLite path.

## Admin UI

- URL: `/admin` — requires a JWT for a user with `role = admin` (redirects to login otherwise).
- **Ops** tab: trigger scrapers, view scheduler status, KYC approve/reject.

## APIs (Bearer token, admin role)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/admin/stats` | Dashboard metrics |
| `GET /api/admin/users` | User list (`?q=` search) |
| `PATCH /api/admin/users/:id` | `{ "role": "user\|employer\|admin" }` |
| `GET /api/admin/jobs` | All jobs including inactive |
| `POST /api/scrape` | Run scraper (see `notes/VISA_OCCUPATION_SCRAPER.md`) |
| `GET /api/kyc/admin/list` | Pending KYC |

Set `ADMIN_MASK_PII=true` in production to mask emails in admin stats.
