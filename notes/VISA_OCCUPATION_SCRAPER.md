# Visa sponsorship scraper (all occupations + skilled list)

## What it does

| Step | Behaviour |
|------|-----------|
| **Sources** | SEEK Australia (`seek_au`), all states/territories + national passes |
| **Sponsorship** | Ad must mention visa/sponsorship/relocation (see `scrapers/mobility_language.py`, `teaching_filters.mentions_sponsorship`) |
| **Occupation list** | Title/description matched to `data/au_skilled_occupations.json` (ANZSCO titles, MLTSSL/STSOL-style lists) |
| **Teaching** | Still available via `source=teaching_au` (NSW JobFeed + teaching SEEK profile) |

This is **not** legal advice or a guarantee of nomination eligibility — it filters ads to roles that **look like** in-demand skilled occupations **and** mention mobility language.

## Activate

1. **Fix is automatic** — `require_auth` lives in `api/security.py`; `/api/scrape` loads with the app.
2. **One-off ingest** (admin JWT):

```bash
curl -X POST "$APP_URL/api/scrape" \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "visa_sponsorship_au",
    "insert_db": true,
    "max_pages": 2,
    "require_occupation_on_demand": true
  }'
```

3. **Scheduled** (in-process, until restart):

```bash
curl -X POST "$APP_URL/api/scrape/scheduled/start" \
  -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{"source":"visa_sponsorship_au","interval_minutes":360}'
```

4. **Auto on deploy** — set in Railway/host env:

- `SCRAPER_AUTO_START=true`
- `SCRAPER_AUTO_SOURCE=visa_sponsorship_au` (default)
- `SCRAPER_AUTO_INTERVAL_MINUTES=360`
- `SCRAPER_REQUIRE_OCCUPATION_LIST=true`
- `ALLOWED_EGRESS_HOSTS=www.seek.com.au`

## Dry run (no DB)

```bash
PYTHONPATH=. python scripts/scan_au_visa_occupations.py
```

## Refresh occupation data

Edit `data/au_skilled_occupations.json` (bump `version`) from official Home Affairs skilled occupation publications and state lists. Keywords drive matching; add aliases employers use in ads.

## API fields on ingested jobs

`search_summary` includes `anzsco:… lists:MLTSSL,…` when matched. Category defaults to matched occupation title.
