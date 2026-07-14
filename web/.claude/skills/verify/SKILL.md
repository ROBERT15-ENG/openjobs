---
name: verify
description: Build, run, and drive the OpenJobs Next.js frontend (web/) against the Flask API
---

# Verify: OpenJobs web/ (Next.js frontend)

## Launch

1. Flask API (needs repo-root `jobs.db` + `.env`):
   `cd api && ../.venv/bin/python server.py` → http://127.0.0.1:5700 (health: `/api/health`)
2. Web: `cd web && npm run build && npm start` → http://localhost:3000 (`npm run dev` for dev mode)

## Drive

- Browse SSR: `curl -s localhost:3000/ | grep -oE '<h3><a href="/jobs/[0-9]+">[^<]+'`
- Filters are URL params: `/?q=flask`, `/?type=internship,contract`, `/?mode=remote,hybrid`,
  `/?location=Sydney`, `/?page=2`
- Auth (cookie jar): `curl -c jar -X POST localhost:3000/api/session/login -d '{"email":...,"password":...}'`
  → sets httpOnly `oj_session`. Demo creds: tonny@email.com / demo1234 (seeker),
  employer@openjobs.com / employer123 (employer).
- Saved jobs: with jar, `POST /api/saved {"job_id":N,"save":true|false}`;
  cross-check Flask directly: `curl 127.0.0.1:5700/api/saved_jobs?user_id=1`
- Logout: `POST /api/session/logout` → 303 + cookie cleared + token blocklisted
  (old Bearer against Flask `/api/auth/me` → 401 "Token revoked").
- Client-side interactions (filter chips, save bookmark, login form) only exist in the
  browser — drive them with claude-in-chrome, not curl.

## Gotchas

- Next renders HTML as one line — `grep -c` counts lines, use `grep -o | wc -l`.
- The session cookie is `Secure` in production builds: fine on localhost, needs HTTPS on a real host.
- Every page is dynamic (ƒ): `cookies()` in the Header opts the whole tree out of static rendering.
- Browser screenshots via CDP sometimes time out right after a navigation — retry once, it recovers.
