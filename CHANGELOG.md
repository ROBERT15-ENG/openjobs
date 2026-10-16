# Changelog

All notable changes to OpenJobs follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Project documentation PDF (`docs/OpenJobs_Project_Documentation.pdf`) and generator script
- Job list cache generation header and bump on job writes (`platform_cache.py`, items 49–50)
- Platform P1: SQL migrations, idempotency keys, DB indexes (when tables exist)
- `/api/ready` readiness probe and enhanced `/api/health`
- `/api/platform/flags` feature flag endpoint
- Guest job list `Cache-Control` when `FEATURE_GUEST_JOB_CACHE` is enabled
- `Idempotency-Key` support on job apply (`quick_apply`)
- Security headers (CSP on HTML, `X-Frame-Options`, etc.)
- Docker, Gunicorn config, GitHub Actions CI
- Engineering roadmap notes in `notes/ENGINEERING_ROADMAP.md`

### Security
- SSRF helper `api/http_safety.py` for outbound URL allowlisting
- Lock down admin/CRM/applications APIs; fix IDOR on dashboard/saved jobs; production JWT guard (`api/security.py`) — see `notes/SECURITY_AUDIT.md`
- User data protection: field filtering, admin email masking, data export & account deletion, privacy consents — `notes/DATA_PROTECTION.md`
