# Australian teaching jobs (visa sponsorship) — scraper status

Last checked: 2026-10-16

## Summary

| Source | Status | Notes |
|--------|--------|--------|
| **NSW JobFeed** | NSW | Official weekly NSW public vacancies (**“Current as at”** date) |
| **Per-state search (8 jurisdictions)** | VIC–ACT | Teaching + mobility keywords in each state/territory (market aggregator) |
| **Teaching profile** | **Working** | `teaching_au` → NSW JobFeed first; optional SEEK |
| **Indeed AU** | Not implemented | Bot protection; no stable public API in this repo |
| **LinkedIn** | Not implemented | Requires official API / partnership |
| **SEEK (state DET portals)** | Not implemented | e.g. teach.nsw.edu.au — separate HTML sites; future adapter |
| **jobsearch.gov.au** | Not implemented | Site returned empty responses from this environment; revisit with official API docs |

## What was wrong before

- `api/scraper_routes.py` imported `scrapers.scheduler`, but the **`scrapers/` package did not exist** in the repo.
- The blueprint was **never registered** on the Flask app.
- Default scrape query was **software engineer**, not education or sponsorship.
- **Indeed / LinkedIn** were advertised in the API but had **no implementation**.

## How to check live (no DB write)

```bash
# All states & territories (default)
PYTHONPATH=. python scripts/scan_au_teaching_mobility.py

# NSW government feed only
PYTHONPATH=. python scripts/scan_au_teaching_mobility.py --nsw-only
```

## How to ingest into OpenJobs (admin JWT)

```bash
curl -X POST http://localhost:5700/api/scrape \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"source":"teaching_au","insert_db":true,"max_pages":2}'
```

Requires a populated `jobs` table in `jobs.db`.

## Filtering logic

- **Australia only (default):** location must include an AU state/territory or “Australia”; titles/teasers advertising **England/UK/overseas placement** are removed (recruiter may still list Sydney/Melbourne).
- **Teaching:** title/teaser/classification matches education roles (teacher, ECT, principal, etc.).
- **Sponsorship:** description/teaser mentions visa, sponsorship, 482/186, relocation, etc.
- SEEK queries include **“Australia”** in the keyword set where possible.

Set `australia_only: false` on `POST /api/scrape` only if you intentionally want overseas-placement ads from seek.com.au.

## Compliance

- Rate-limit scrapes (scheduler default 60 min).
- Set `ALLOWED_EGRESS_HOSTS=www.seek.com.au` in production if using egress allowlists.
- Review SEEK terms before high-volume production use; link out to SEEK job URLs (`external_url`).
