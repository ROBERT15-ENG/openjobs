# OpenJobs — Application flow (page by page)

**Last updated:** October 2026

---

## Public marketing & search

| Route | Page | Primary actions | Auth |
|-------|------|-----------------|------|
| `/` | Home — hero search, job feed, filters, chat widget | Search, open job modal, sign up | Guest |
| `/job`, `/job?id=` | Job detail + apply form | Apply, upload resume, share link | Guest (apply may need login) |
| `/companies` | Company directory | Browse employers | Guest |
| `/salary` | Salary guide / predictor | Use calculator | Guest |
| `/login` | Sign in | Email or Google → JWT in `localStorage` | Guest |
| `/register` | Create seeker account | Register → `/thank-you?type=register` | Guest |
| `/forgot-password` | Password reset request | Email flow | Guest |
| `/reset-password.html` | Set new password | Submit new password | Guest |
| `/privacy` | Privacy policy | Read | Guest |
| `/terms` | Terms of use | Read | Guest |
| `/thank-you` | Post-conversion confirmation | Go to dashboard or home | Any |
| *(unknown)* | **404** branded page | Return home | Any |

**Guest home flow**

```mermaid
flowchart LR
  A[Land on /] --> B[Search / filter]
  B --> C[Job card / modal]
  C --> D{Logged in?}
  D -->|No| E[Register / Login]
  D -->|Yes| F[Apply / Save]
  F --> G[/thank-you]
  E --> H[/user dashboard]
```

## Job seeker

| Route | Page | Primary actions | Auth |
|-------|------|-----------------|------|
| `/user` | Seeker dashboard | Applications, saved jobs, profile, recommendations | JWT `user` |
| `/api/dashboard/seeker` | Data for “For You” | AI-ranked jobs | JWT |

**Seeker apply flow**

1. View job on `/job`  
2. Fill name, email, resume (optional upload)  
3. `POST /api/apply/<job_id>` (+ optional `Idempotency-Key`)  
4. Redirect **`/thank-you?type=application`**  
5. Track status on `/user`

## Employer

| Route | Page | Primary actions | Auth |
|-------|------|-----------------|------|
| `/employer` | Employer portal | Login, post job, kanban, applicants | JWT `employer` |
| `/api/employer/dashboard` | Stats JSON | View metrics | JWT employer |
| `/api/payment/checkout` | Stripe session | Pay for listing tier | JWT employer |

**Employer hire flow**

1. Register employer → login  
2. Post job (`POST /api/jobs`) → optional Stripe  
3. Receive applications (`GET /api/employer/applications`)  
4. Move cards on kanban (`POST /api/kanban/<id>/move`)

## Admin & tools

| Route | Page | Primary actions | Auth |
|-------|------|-----------------|------|
| `/admin` | Admin dashboard | Users, jobs, analytics tabs | JWT `admin` |
| `/ai` | AI tools UI | Ollama chat / utilities | Varies |
| `/cad` | CAD viewer utility | Upload DXF | Varies |

## API-only (no HTML)

| Prefix | Use |
|--------|-----|
| `/api/jobs` | CRUD, search |
| `/api/auth/*` | Login, register, logout, me |
| `/api/chatbot` | Web assistant |
| `/api/scrape` | Admin job ingestion |
| `/api/platform/flags` | Feature toggles for clients |

## Auth & session model

- JWT stored in browser **`localStorage`** (`token`)  
- Logout adds token to server blocklist  
- No cookie-based session for API (CSRF N/A for Bearer)  
- Cookie banner: **essential** always; **analytics** opt-in → may sync to `PATCH /api/user/privacy`

## External channels

| Channel | Entry | Flow |
|---------|-------|------|
| Telegram | `/start`, `/search`, `/visa` | Bot calls same `/api/jobs` and `/api/chatbot` |
| Email | Transactional | Apply confirm, alerts (SMTP) |

## Pages referenced but incomplete

| Route | Status |
|-------|--------|
| `/learning` | Linked in nav; route may 404 — implement or remove link |
| `company.html` | May be missing — `/companies` fallback JSON |
