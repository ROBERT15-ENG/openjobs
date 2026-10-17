#!/usr/bin/env python3
"""
Generate OpenJobs project documentation PDF (professional layout).
Output: docs/OpenJobs_Project_Documentation.pdf
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs"
OUT_FILE = OUT_DIR / "OpenJobs_Project_Documentation.pdf"

# Brand colors (RGB)
BRAND_PRIMARY = (15, 76, 129)
BRAND_ACCENT = (0, 150, 136)
TEXT_MUTED = (90, 90, 90)


def _ascii(text: str) -> str:
    """FPDF 1.x pages are latin-1; normalize common Unicode punctuation."""
    return (
        text.replace("\u2014", " - ")
        .replace("\u2013", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )


class OpenJobsPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=20)
        self._section_title = ""
        self._toc: list[tuple[str, int, int]] = []

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*TEXT_MUTED)
        self.cell(0, 8, "OpenJobs Project Documentation", align="L")
        if self._section_title:
            self.cell(0, 8, self._section_title, align="R", ln=True)
        else:
            self.ln(8)
        self.set_draw_color(220, 220, 220)
        self.line(10, 14, 200, 14)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*TEXT_MUTED)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def register_toc(self, title: str):
        self._toc.append((title, self.page_no(), self.get_y()))

    def cover_page(self):
        self.add_page()
        self.set_fill_color(*BRAND_PRIMARY)
        self.rect(0, 0, 210, 90, style="F")
        self.set_y(28)
        self.set_font("Helvetica", "B", 32)
        self.set_text_color(255, 255, 255)
        self.cell(0, 14, "OpenJobs", align="C", ln=True)
        self.set_font("Helvetica", "", 16)
        self.cell(0, 10, "AI-Powered Australian Job Board", align="C", ln=True)
        self.ln(50)
        self.set_text_color(30, 30, 30)
        self.set_font("Helvetica", "B", 20)
        self.cell(0, 12, "Project Documentation", align="C", ln=True)
        self.ln(8)
        self.set_font("Helvetica", "", 11)
        self.set_text_color(*TEXT_MUTED)
        meta = [
            f"Document version: 1.0",
            f"Generated: {date.today().isoformat()}",
            "Repository: ROBERT15-ENG/openjobs",
            "Stack: Flask, SQLite, Ollama, Stripe, Telegram",
        ]
        for line in meta:
            self.cell(0, 7, line, align="C", ln=True)
        self.ln(20)
        self.set_font("Helvetica", "I", 9)
        self.multi_cell(
            0,
            5,
            "This document consolidates product scope, architecture, APIs, security, "
            "data protection, deployment, and engineering roadmap notes for the OpenJobs platform.",
            align="C",
        )

    def chapter(self, num: int, title: str):
        self.add_page()
        self._section_title = title
        self.set_fill_color(*BRAND_ACCENT)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, f"  {num}. {title}", ln=True, fill=True)
        self.ln(4)
        self.set_text_color(30, 30, 30)
        self.register_toc(f"{num}. {title}")

    def subheading(self, title: str):
        self.ln(2)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*BRAND_PRIMARY)
        self.multi_cell(0, 7, _ascii(title))
        self.set_text_color(30, 30, 30)
        self.ln(1)

    def body(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5.5, _ascii(text))
        self.ln(2)

    def bullet_list(self, items: list[str]):
        self.set_font("Helvetica", "", 10)
        for item in items:
            self.multi_cell(0, 5.5, _ascii(f"  - {item}"))
        self.ln(2)

    def table(self, headers: list[str], rows: list[list[str]], col_widths: list[float] | None = None):
        if not rows:
            return
        n = len(headers)
        if col_widths is None:
            w = (190 - 10) / n
            col_widths = [w] * n
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(240, 244, 248)
        for i, h in enumerate(headers):
                self.cell(col_widths[i], 7, _ascii(h[:40]), border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", "", 8)
        fill = False
        for row in rows:
            if self.get_y() > 265:
                self.add_page()
            for i, cell in enumerate(row):
                txt = _ascii((cell or "")[:80])
                self.cell(col_widths[i], 6, txt, border=1, fill=fill)
            self.ln()
            fill = not fill
        self.ln(3)


def build_pdf() -> Path:
    pdf = OpenJobsPDF()
    pdf.cover_page()

    # --- 1 Executive summary ---
    pdf.chapter(1, "Executive Summary")
    pdf.body(
        "OpenJobs is a full-stack job board focused on the Australian market. It connects job seekers "
        "with employers through searchable listings, AI-assisted resume matching, application tracking, "
        "and employer hiring pipelines. The platform includes a public web application, REST API, "
        "optional Telegram bot, guest advertising slots, and a privacy-hardened chatbot for job discovery."
    )
    pdf.subheading("Primary audiences")
    pdf.bullet_list(
        [
            "Job seekers: search, save jobs, apply, resume upload, ATS-style match scores, dashboards.",
            "Employers: post jobs (Standard/Premium pricing), kanban ATS, applicant notifications.",
            "Operators: health probes, feature flags, admin analytics (authenticated), CRM (admin).",
            "Integrations: Stripe payments, SMTP email, Ollama LLM, Redis (optional), scrapers.",
        ]
    )
    pdf.subheading("Repository layout (high level)")
    pdf.bullet_list(
        [
            "api/ - Flask application (server.py) and platform modules.",
            "templates/ - Server-rendered HTML (index, job, user, employer, admin).",
            "bot/ - Telegram bot polling against the REST API.",
            "migrations/ - SQL schema migrations for platform hardening.",
            "notes/ - Engineering roadmap, security audit, data protection.",
            "scripts/ - Migration runner and this PDF generator.",
        ]
    )

    # --- 2 Features ---
    pdf.chapter(2, "Product Features")
    pdf.subheading("Job seekers")
    pdf.bullet_list(
        [
            "Filtered job search: work type, remote/hybrid, salary, location, category.",
            "Semantic AI matching via keyword-first scoring with Ollama fallback (semantic_matcher.py).",
            "Saved jobs, application history, seeker dashboard (/user).",
            "Quick apply with idempotency (Idempotency-Key header) to prevent duplicate submissions.",
            "Resume upload (PDF/DOCX) with skill extraction and optional AI parse.",
            "Data export, account deletion, and privacy consent APIs.",
        ]
    )
    pdf.subheading("Employers")
    pdf.bullet_list(
        [
            "Employer registration and multi-tenant isolation (own jobs and applicants only).",
            "Job CRUD, featured listings, view tracking, company ratings.",
            "Kanban pipeline: Applied, Screening, Interview, Offer, Hired, Rejected.",
            "Stripe checkout for job posting tiers (demo mode when keys unset).",
            "KYC document upload flow for verification workflows.",
        ]
    )
    pdf.subheading("Public and guest experience")
    pdf.bullet_list(
        [
            "Landing and job detail pages with SEO sitemaps and robots.txt.",
            "Guest-only promoted ad cards (FEATURE_ADS) sized like job posts before login.",
            "Floating web chatbot (rule-based search; AI gated by server secret).",
            "Salary tools, company pages, CAD viewer utility routes (specialized).",
        ]
    )

    # --- 3 Architecture ---
    pdf.chapter(3, "System Architecture")
    pdf.body(
        "The system follows a monolithic Flask application pattern: HTTP requests hit api/server.py, "
        "which serves both JSON APIs and static HTML templates. SQLite (jobs.db) is the default datastore; "
        "Docker Compose mounts a volume for persistent DB and optional Redis for rate limiting or sessions."
    )
    pdf.subheading("Request flow")
    pdf.bullet_list(
        [
            "Browser or bot calls REST endpoints or loads HTML routes (/ , /job, /employer, etc.).",
            "JWT in Authorization header for authenticated APIs; token blocklist on logout.",
            "Middleware: CORS (ALLOWED_ORIGINS), rate limits (Flask-Limiter), security headers on HTML.",
            "Production: enforce strong JWT_SECRET; optional HTTPS redirect when FLASK_ENV=production.",
        ]
    )
    pdf.subheading("AI and matching")
    pdf.body(
        "rank_jobs_for_resume and semantic_matcher implement keyword scoring (0-10) with alias normalization. "
        "Scores 0 or >=4 skip Ollama; borderline 1-3 trigger semantic rescoring. Confidence tiers: "
        "ELITE (80%+), STRONG (70%+), WATCHLIST (50%+). ai_matcher.py and ai_filter.py provide additional "
        "Ollama integrations for resume parse and job quality signals."
    )
    pdf.subheading("Supporting services")
    pdf.table(
        ["Component", "Role"],
        [
            ["email_notifier.py", "SMTP/SendGrid applicant and employer emails"],
            ["payment.py", "Stripe checkout and pricing"],
            ["sitemap_generator.py / seo_*", "SEO URLs and middleware"],
            ["Scrapers (linkedin, indeed, remotive)", "Ingest jobs via POST /api/jobs"],
            ["openjobs_chatbot.py", "Intent routing for chat and Telegram"],
            ["chatbot_security.py", "Injection patterns, PII redaction, LIKE escape"],
        ],
        [55, 135],
    )

    # --- 4 API ---
    pdf.chapter(4, "API Reference (Summary)")
    pdf.body("Full schematic: OpenJobs_CodeSchematic.pdf in repository root. Key route groups:")
    api_rows = [
        ["POST", "/api/auth/login, register, logout", "Authentication and JWT"],
        ["GET", "/api/auth/me", "Current user profile"],
        ["GET/POST", "/api/jobs", "List (filter) and create jobs"],
        ["GET/PATCH/DELETE", "/api/jobs/<id>", "Job detail and owner updates"],
        ["POST", "/api/apply/<id>, /api/applications", "Applications"],
        ["GET/POST", "/api/kanban/<job_id>", "ATS pipeline"],
        ["POST", "/api/resume/upload", "Resume storage and skill extract"],
        ["GET", "/api/dashboard/seeker", "Seeker dashboard data"],
        ["GET/POST/DELETE", "/api/saved_jobs", "Saved jobs (auth)"],
        ["GET", "/api/recommendations", "AI-ranked jobs (auth)"],
        ["POST", "/api/chatbot", "Public chatbot (use_ai false by default)"],
        ["GET", "/api/ads", "Guest ad catalog (empty when logged in)"],
        ["GET", "/api/health, /api/ready", "Liveness and readiness"],
        ["GET", "/api/platform/flags", "FEATURE_* flags for clients"],
        ["GET", "/api/user/data-export", "GDPR-style export"],
        ["POST", "/api/user/delete-account", "Account erasure"],
        ["GET/PATCH", "/api/user/privacy", "Consent flags"],
        ["GET", "/api/admin/stats", "Admin only"],
        ["GET", "/api/crm/*", "Admin CRM (companies, contacts, pipeline)"],
    ]
    pdf.table(["Method", "Endpoint", "Description"], api_rows, [22, 75, 93])

    # --- 5 Database ---
    pdf.chapter(5, "Data Model")
    pdf.body("Primary SQLite database: jobs.db (path configurable via DATABASE_URL in Docker).")
    pdf.table(
        ["Table", "Purpose"],
        [
            ["users", "Seekers and employers; skills, resume text, roles"],
            ["jobs", "Listings; soft delete via is_active"],
            ["applications", "Applications with status and match_score"],
            ["saved_jobs", "Seeker bookmarks"],
            ["skills_taxonomy", "Skills with aliases and demand"],
            ["job_alerts", "Email alert preferences"],
            ["schema_migrations", "Applied SQL migrations (001, 002)"],
        ],
        [50, 140],
    )
    pdf.subheading("Migrations")
    pdf.bullet_list(
        [
            "migrations/001_p1_core.sql - indexes, idempotency, platform tables.",
            "migrations/002_privacy_consents.sql - privacy consent columns.",
            "Run: python scripts/apply_migrations.py",
        ]
    )

    # --- 6 Security ---
    pdf.chapter(6, "Security and Privacy")
    pdf.body(
        "A security audit (notes/SECURITY_AUDIT.md) addressed critical issues: admin stats and CRM "
        "now require admin role; applications and dashboards are scoped to authenticated users; "
        "IDOR fixes on seeker dashboard and saved jobs; production JWT secret enforcement."
    )
    pdf.subheading("Chatbot hardening")
    pdf.bullet_list(
        [
            "Pattern-based prompt injection detection and message length limits.",
            "PII redaction before any optional LLM call.",
            "Public web UI uses rule-based intents only unless CHATBOT_AI_ENABLED and CHATBOT_INTERNAL_SECRET.",
            "SQL LIKE parameters escaped for search intents.",
        ]
    )
    pdf.subheading("HTTP security")
    pdf.bullet_list(
        [
            "CSP and security headers on HTML responses.",
            "HSTS when running in production mode.",
            "SSRF controls in api/http_safety.py for outbound fetches.",
            "Registration role allowlist (user/employer only).",
        ]
    )
    pdf.subheading("Data protection")
    pdf.bullet_list(
        [
            "api/data_protection.py filters sensitive fields in JSON responses.",
            "ADMIN_MASK_PII masks emails in admin list views in production.",
            "User rights: export, delete-account, privacy consent endpoints.",
            "See notes/DATA_PROTECTION.md for retention and subprocessors.",
        ]
    )

    # --- 7 Deployment ---
    pdf.chapter(7, "Deployment and Operations")
    pdf.subheading("Local development")
    pdf.bullet_list(
        [
            "pip install -r requirements.txt",
            "cp .env.example .env and configure secrets",
            "PYTHONPATH=. python api/server.py (default port 5700)",
            "Optional: ollama serve && ollama pull gemma3:4b",
        ]
    )
    pdf.subheading("Docker")
    pdf.bullet_list(
        [
            "docker compose up - web on 5700, Redis on 6379, volume openjobs_data.",
            "Image runs gunicorn -c gunicorn.conf.py api.server:app",
            "Migrations applied at build (best-effort).",
        ]
    )
    pdf.subheading("Production checklist")
    pdf.bullet_list(
        [
            "Set JWT_SECRET (32+ chars), STRIPE keys, SMTP, rotate Telegram token if exposed.",
            "Point health checks to GET /api/ready",
            "TLS at edge (Cloudflare/Railway); ALLOWED_ORIGINS restricted",
            "Daily DB backups and restore drills (planned in roadmap)",
            "Enable ADMIN_MASK_PII; disable CHATBOT_AI for anonymous users unless required",
        ]
    )
    pdf.subheading("CI/CD")
    pdf.body("GitHub Actions workflow .github/workflows/ci.yml runs tests/install on push.")

    # --- 8 Environment ---
    pdf.chapter(8, "Configuration")
    env_rows = [
        ["SECRET_KEY / JWT", "Flask and JWT signing"],
        ["FLASK_ENV", "development vs production behaviors"],
        ["OLLAMA_URL, OLLAMA_MODEL", "Local LLM for matching"],
        ["JOBSEEK_AI_ENABLED", "Master AI toggle"],
        ["SMTP_* , FROM_EMAIL", "Transactional email"],
        ["STRIPE_*", "Payments"],
        ["TELEGRAM_BOT_TOKEN", "Telegram bot"],
        ["FEATURE_ADS, FEATURE_CHATBOT*", "Feature flags"],
        ["FEATURE_GUEST_JOB_CACHE", "CDN-friendly job list caching"],
        ["CHATBOT_AI_ENABLED, CHATBOT_INTERNAL_SECRET", "LLM gate for chatbot"],
        ["ADMIN_MASK_PII", "Mask emails in admin APIs"],
        ["ALLOWED_ORIGINS", "CORS allowlist"],
        ["ALLOWED_EGRESS_HOSTS", "Scraper outbound allowlist"],
        ["DATABASE_URL, REDIS_URL", "Docker paths"],
    ]
    pdf.table(["Variable", "Purpose"], env_rows, [70, 120])

    # --- 9 Bot & integrations ---
    pdf.chapter(9, "Integrations")
    pdf.subheading("Telegram (bot/telegram_bot.py)")
    pdf.bullet_list(
        [
            "Commands: /start, /help, /search, /remote, /visa, /top, /subscribe",
            "Uses TELEGRAM_BOT_TOKEN from environment (bot_config.py)",
            "Free text routed through /api/chatbot",
        ]
    )
    pdf.subheading("Payments and email")
    pdf.body(
        "Stripe checkout via /api/payment/checkout; returns 503 demo mode without keys. "
        "email_notifier sends applicant confirmations and employer alerts when SMTP is configured."
    )

    # --- 10 Roadmap ---
    pdf.chapter(10, "Engineering Roadmap")
    pdf.body(
        "notes/ENGINEERING_ROADMAP.md tracks a 111-item backend/SRE checklist. Recent work (P1/P2) includes "
        "rate limiting, Docker, Gunicorn timeouts, idempotency on apply, health/readiness, feature flags, "
        "cache generation headers, SQL migrations, and CI."
    )
    pdf.subheading("Planned highlights")
    pdf.bullet_list(
        [
            "Autoscaling, CDN (Cloudflare), blue-green and canary deploys",
            "Postgres migration with Alembic; Redis caching for hot paths",
            "Stripe webhook signature verification; API versioning /api/v1",
            "OTEL monitoring; WAF; encrypted resume/KYC at rest",
        ]
    )

    # --- 11 Related documents ---
    pdf.chapter(11, "Related Artifacts")
    pdf.table(
        ["Artifact", "Location"],
        [
            ["README", "README.md"],
            ["Architecture notes", "ARCHITECTURE.md"],
            ["API schematic PDF", "OpenJobs_CodeSchematic.pdf"],
            ["Changelog", "CHANGELOG.md"],
            ["Security audit", "notes/SECURITY_AUDIT.md"],
            ["Data protection", "notes/DATA_PROTECTION.md"],
            ["Engineering roadmap", "notes/ENGINEERING_ROADMAP.md"],
            ["This document", "docs/OpenJobs_Project_Documentation.pdf"],
        ],
        [60, 130],
    )

    pdf.subheading("Test accounts (development)")
    pdf.body(
        "See README.md for demo seeker and employer credentials. Do not use default passwords in production."
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT_FILE))
    return OUT_FILE


def main():
    path = build_pdf()
    size_kb = path.stat().st_size / 1024
    print(f"Wrote {path} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
