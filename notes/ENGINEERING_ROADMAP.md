# OpenJobs — Engineering roadmap (P1 / P2 / P3)

Living notes for the 111-item backend/SRE checklist.  
**Status:** `done` · `started` · `planned` · `n/a` (defer)

Last updated: 2026-10-16 (items 45–53 corrected per @nataindata screenshot)

---

## Canonical checklist slice (items 45–53)

| # | Topic | OpenJobs plan | Status |
|---|--------|---------------|--------|
| **45** | Autoscaling | Railway/replica count or K8s HPA on CPU + p95 latency; min 1 instance to avoid cold starts | planned |
| **46** | Horizontal scaling | Stateless Flask + shared Postgres/Redis; multiple Gunicorn workers per instance | started (`WEB_CONCURRENCY`, Docker) |
| **47** | Vertical scaling | Larger Railway plan / more RAM for AI workers before adding regions | planned |
| **48** | CDN | Cloudflare in front of `openjobs.com.au`; cache static + anonymous API at edge | planned |
| **49** | Edge caching | Cache `GET /api/jobs` at CDN with short TTL; respect `Vary: Authorization` | started (`Cache-Control` + gen header) |
| **50** | Cache invalidation | Bump `X-OpenJobs-Jobs-Gen` on job create/update/delete; CDN purge by surrogate key later | started (`api/platform_cache.py`) |
| **51** | Feature flags | `FEATURE_*` env + `/api/platform/flags` | started |
| **52** | Blue-green deployment | Two Railway services; switch router after `/api/ready` green | planned |
| **53** | Canary releases | Route 5% traffic to new revision; compare 5xx vs stable | planned |

*Graceful shutdown* is not item 45 on this list; keep using Gunicorn `graceful_timeout` as a general deploy practice (pairs with **54** rolling deployments).

---

## What we shipped in this pass

| Area | Item # | Status | Where |
|------|--------|--------|--------|
| Rate limiting | 1 | started | Flask-Limiter on API routes |
| Caching | 2 | started | `Cache-Control` on guest `GET /api/jobs` |
| CI/CD | 6 | started | `.github/workflows/ci.yml` |
| Docker | 7 | started | `Dockerfile`, `docker-compose.yml` |
| Timeouts | 11 | started | `gunicorn.conf.py` timeout / graceful |
| Idempotency | 14 | done | `Idempotency-Key` on `quick_apply` |
| DB indexes | 25–27 | started | `migrations/`, `platform_db._apply_optional_indexes` |
| Race / dup apply | 39 | started | unique index `applications(job_id,user_id)` |
| Backpressure | 44 | started | rate limits + gunicorn workers |
| Edge cache + invalidation | 49–50 | started | `Cache-Control`, `X-OpenJobs-Jobs-Gen`, `platform_cache.py` |
| Health / readiness | 56–57 | done | `/api/health`, `/api/ready` |
| Secrets | 67 | started | `.env` only; rotate tokens in prod |
| TLS | 71 | started | `_force_https` when `FLASK_ENV=production` |
| CORS | 76 | done | `ALLOWED_ORIGINS` |
| SQL injection | 78 | started | parameterized queries + chatbot LIKE escape |
| XSS / CSP | 79 | started | `escHtml` in UI + CSP on HTML responses |
| SSRF | 80 | started | `api/http_safety.py` + `ALLOWED_EGRESS_HOSTS` |
| Migrations | 81–82 | started | SQL migrations + `schema_migrations` table |
| Semantic versioning | 103 | started | `CHANGELOG.md` |
| Build caching | 107 | started | Docker layer cache in CI |
| Dependencies | 108 | started | pinned `requirements.txt` |
| Feature flags | 51 | started | `api/platform_flags.py`, `GET /api/platform/flags` |
| Postmortems / incidents | 109, 111 | planned | templates in this doc (below) |

Run migrations: `python scripts/apply_migrations.py`  
Prod server: `gunicorn -c gunicorn.conf.py api.server:app`

---

## P1 — Do first (reliability + security MVP)

| # | Topic | Status | Next action |
|---|--------|--------|-------------|
| 1 | Rate limiting | started | Per-user limits when JWT present; stricter on auth |
| 11 | Timeouts | started | Audit all `requests.*` calls for explicit timeout |
| 14 | Idempotency | done | Extend to Stripe checkout + `POST /api/jobs` |
| 25–27 | Indexes / queries | started | Run app against real `jobs.db`; EXPLAIN slow paths |
| 39 | Race conditions | started | Verify unique index applied after seed |
| 44 | Backpressure | started | 503 when DB pool saturated (Postgres phase) |
| 56–57 | Health / readiness | done | Wire Railway health check to `/api/ready` |
| 67 | Secrets | started | Document rotation; remove any committed secrets |
| 69 | OAuth | started | Set `GOOGLE_CLIENT_ID` in prod |
| 71–73 | TLS / encryption | started | TLS at edge; encrypted DB volume in prod |
| 76–80 | Web security | started | CSRF tokens on HTML forms; SSRF on scrapers |
| 81–82 | Migrations | started | Add Alembic when Postgres lands |
| 84 | Backups | planned | Daily `jobs.db` / Postgres snapshot + restore test |
| 97 | DNS | planned | Document `openjobs.com.au` records |
| 103 | Semver | started | Tag releases; maintain `CHANGELOG.md` |
| 107–108 | Build / deps | started | Dependabot; pin minor versions |

### P1 ops notes

- **Backups:** nightly DB dump to object storage; monthly restore drill.
- **Incidents (109):** Sev1 = site down / payments broken; Sev2 = apply flow broken; Sev3 = degraded AI.
- **Postmortem (111):** timeline, root cause, action items with owners.

---

## P2 — Scale & operability

| # | Topic | Status | Next action |
|---|--------|--------|-------------|
| 2 | Caching | started | Redis cache for job list keys |
| 45–47 | Autoscaling / H+V scale | planned | Railway autoscale rules; document worker vs web tiers |
| 48–50 | CDN / edge / invalidation | started | Cloudflare proxy; purge on `Jobs-Gen` change |
| 3–5 | LB / proxy / gateway | planned | Nginx or Cloudflare in front of Railway |
| 6 | CI/CD | started | Add lint (ruff), migration gate, staging deploy |
| 7 | Docker | started | Push image to registry; use in Railway |
| 10 | Circuit breakers | planned | `pybreaker` on Ollama / SMTP |
| 12–13 | Retries / backoff | planned | Shared helper for workers |
| 15–21 | Queues / cron | planned | Redis RQ for email + resume parse |
| 28 | Connection pooling | planned | SQLAlchemy + pgbouncer with Postgres |
| 51 | Feature flags | started | Use flags in UI for ads / chatbot |
| 52–53 | Blue-green / canary | planned | Document in deploy runbook after staging exists |
| 54–55 | Rolling / rollback | planned | Railway rollback procedure in runbook |
| 58–62 | Monitoring / alerts | planned | OTEL or Datadog; alert on 5xx |
| 70 | JWT rotation | planned | Dual signing keys |
| 74–75 | WAF / DDoS | planned | Cloudflare proxy |
| 88 | Cost | started | Keep Ollama off hot path (keyword-first matcher) |
| 91–94 | Latency SLOs | planned | k6 load test; track p95 on `/api/jobs` |
| 101 | Webhooks | started | Verify Stripe webhook signatures |
| 102 | API versioning | planned | `/api/v1/*` prefix |
| 104–105 | IaC / Terraform | planned | DNS + DB + Redis modules |

### P2 env flags (`FEATURE_*`)

| Flag | Default | Purpose |
|------|---------|---------|
| `FEATURE_ADS` | on | Guest ad slots |
| `FEATURE_CHATBOT` | on | Chat assistant |
| `FEATURE_CHATBOT_AI` | off | Ollama enrichment (needs secret) |
| `FEATURE_GUEST_JOB_CACHE` | on | CDN/browser cache on job list |
| `FEATURE_OLLAMA_MATCHING` | on | Semantic rescoring |

---

## P3 — Enterprise / multi-region

| # | Topic | Notes |
|---|--------|--------|
| 8–9 | K8s / service discovery | Only if Railway limits exceeded |
| 18–20 | Distributed tx / sagas | Payment + job post compensation |
| 29–33 | Replicas / sharding / leader election | Postgres at scale |
| 83–87 | DR / multi-region / chaos | Game days, failover runbooks |
| 95–96 | Partitions / clock skew | JWT skew tolerance; queue offline writes |
| 100 | gRPC | Internal matcher service only |
| 106 | Helm | If on K8s |
| 110 | On-call | Pager rotation when alerts exist |

---

## Commands cheat sheet

```bash
# Local
python scripts/apply_migrations.py
python api/server.py
# or
gunicorn -c gunicorn.conf.py api.server:app

# Docker
docker compose up --build

# Checks
curl -s http://localhost:5700/api/health | jq
curl -s http://localhost:5700/api/ready | jq
curl -s http://localhost:5700/api/platform/flags | jq
```

---

## Related docs

- `ARCHITECTURE.md` — system diagram  
- `README.md` — setup & API overview  
- `CHANGELOG.md` — release history (semver)
