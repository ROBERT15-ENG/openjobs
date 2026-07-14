# OpenJobs Web (Next.js)

React frontend for OpenJobs, replacing the vanilla-JS Flask templates page by
page. The Flask app in `../api` stays as the JSON API; this app talks to it
exclusively server-side.

## Architecture

- **Next.js 15, App Router, TypeScript, React Server Components.** Public pages
  (browse, job detail) are server-rendered against the Flask API — good SEO,
  no client data-fetching library needed. Filters and pagination are plain URL
  params.
- **Auth:** the Flask JWT is stored in an `oj_session` httpOnly cookie, set by
  the route handlers under `src/app/api/session/*` which proxy
  `/api/auth/login|register|logout`. The browser never sees the token
  (the legacy templates keep it in localStorage — this is the upgrade).
- **All Flask calls go through the Next server** (`src/lib/api.ts`). The
  browser only ever talks to Next. Authed client actions (e.g. saving a job)
  hit small proxy route handlers that attach the Bearer token from the cookie.
- **Design tokens** from the legacy templates are ported into
  `src/app/globals.css` (same palette, Major Third type scale — defined
  correctly here; the template version had them outside a selector).

## Run (dev)

```bash
# 1. Flask API on :5700
cd ../api && ../.venv/bin/python server.py

# 2. Next dev server on :3000
npm install
npm run dev
```

## Pages migrated so far (milestone 1)

| Route | Replaces | Notes |
|---|---|---|
| `/` | `index.html` | browse + search + filters + pagination, SSR |
| `/jobs/[id]` | `job.html` (partly) | SSR + per-job metadata; Apply still links to legacy |
| `/login`, `/register` | `login.html`, `register.html` | seeker accounts, cookie session |
| `/register/employer` | employer.html auth tab | registers + auto-login (real JWT via re-login) |
| `/saved` | part of `user.html` | saved-jobs list, save/unsave |
| `/employer/*` | `employer.html` (milestone 2) | overview, post/edit job, listings, applications, pipeline kanban, settings |

Client-side mutations go through `/api/proxy/[...path]` — an allowlisted
pass-through that attaches the Bearer token from the httpOnly cookie.

Deferred: apply flow (resume upload), user dashboard/kanban, admin surface
(`/admin` redirects to the legacy Flask page), pipeline drag & drop.
