# User & client data protection — OpenJobs

## What we store

| Data | Where | Who can access |
|------|--------|----------------|
| Account (name, email, password hash) | `users` | Self; admin (masked email in prod) |
| Resume text / skills | `users`, `applications` | Self; employer for **their** job applicants only |
| KYC documents | `kyc_uploads/` + `kyc_documents` | Self; admin verify endpoints |
| Applications | `applications` | Seeker (own); employer (own jobs); admin |
| JWT sessions | Client `localStorage` | Not stored server-side except blocklist |

## Technical controls (code)

- **`api/data_protection.py`** — strips secrets from JSON; masks admin list emails when `ADMIN_MASK_PII` / production.
- **`api/chatbot_security.py`** — PII redaction before LLM; no chat logs persisted by default.
- **Uploads** — type/size/magic-byte checks; files removed after resume text extraction where possible.
- **Auth** — bcrypt password hashes; JWT for API; logout blocklist (Redis optional).

## User rights (API)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/user/data-export` | Download JSON of **your** account data (auth required) |
| `POST /api/user/delete-account` | Anonymize account & clear PII (auth required) |
| `GET /api/user/privacy` | Read marketing/analytics consent flags |
| `PATCH /api/user/privacy` | Update consent flags |

## Environment

```bash
# Mask emails in admin dashboards (default true in production)
ADMIN_MASK_PII=true

# Do not log raw user content in application prints (use safe_log_message)
```

## Operational requirements

1. **Encryption in transit** — HTTPS + HSTS in production.  
2. **Encryption at rest** — encrypted volume for DB and `uploads/` / `kyc_uploads/` on host.  
3. **Backups** — treat backups as sensitive; restrict access; define retention.  
4. **Subprocessors** — document SMTP, Stripe, Ollama (if used), hosting provider in privacy policy.  
5. **Breach response** — notify affected users per applicable law (e.g. NDB scheme in Australia).  

## Retention (recommended policy)

| Data | Suggested retention |
|------|---------------------|
| Active accounts | Until deletion request |
| Anonymized accounts | Keep application rows for employer records; user row scrubbed |
| Server logs | 30–90 days, no resume bodies |
| Idempotency keys | 24h–7d (operational) |

## Related

- `notes/SECURITY_AUDIT.md` — access control & vulnerabilities  
- `/privacy` — user-facing policy page (template)
