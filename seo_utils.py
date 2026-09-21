#!/usr/bin/env python3
"""
seo_utils.py — Slug generation, canonical URL helpers, structured data helpers.
"""
import os
import re
from urllib.parse import urljoin

# ── Canonical base domain: APP_URL in .env, falls back to the production domain ──
SITE_URL = (os.environ.get('APP_URL') or "https://openjobs.co.ke").rstrip('/') + '/'


def make_slug(*parts) -> str:
    """Generic URL slug: make_slug('Atlassian Pty Ltd') -> 'atlassian-pty-ltd'."""
    text = ' '.join(str(p) for p in parts if p)
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-') or 'item'


# ─────────────────────────────────────────────────────────────────────────────
# 1. SLUG GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def make_job_slug(title: str, job_id: int) -> str:
    """
    Canonical slug for a job posting.
    Format: {lowercase-hyphenated-title}-{id}
    e.g. "Senior Python Engineer-1234"

    Rules:
    - lowercase only
    - spaces → hyphens
    - strip characters not alphanumeric or hyphen
    - append ID at end to guarantee uniqueness
    """
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    return f"{slug}-{job_id}"


def parse_job_slug(slug: str):
    """
    Inverse of make_job_slug.
    Returns (title_slug, job_id) or (None, None) if invalid.
    'senior-python-engineer-1234' → ('senior-python-engineer', 1234)
    """
    parts = slug.rsplit('-', 1)
    if len(parts) != 2:
        return None, None
    title_slug, id_part = parts
    try:
        return title_slug, int(id_part)
    except ValueError:
        return None, None


# ─────────────────────────────────────────────────────────────────────────────
# 2. CANONICAL URL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def canonical_url(path: str) -> str:
    """Return fully-qualified canonical URL for a given path."""
    return urljoin(SITE_URL, path.lstrip('/'))


def job_canonical_url(job_id: int, title: str) -> str:
    """Canonical URL for a job listing page."""
    slug = make_job_slug(title, job_id)
    return canonical_url(f"/jobs/{slug}")


# ─────────────────────────────────────────────────────────────────────────────
# 3. STRUCTURED DATA HELPERS (JSON-LD for Google)
# ─────────────────────────────────────────────────────────────────────────────

def job_listing_jsonld(job: dict, canonical: str) -> str:
    """
    Return a <script type="application/ld+json"> string for a single JobPosting.
    Include in <head> of job.html template.
    """
    import json
    schema = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": job.get("title", ""),
        "identifier": {
            "@type": "PropertyValue",
            "name": job.get("company", ""),
            "value": str(job.get("id", ""))
        },
        "datePosted": (job.get("created_at") or "")[:10],
        "validThrough": job.get("expires_at", "")[:10] if job.get("expires_at") else None,
        "employmentType": (job.get("work_type") or job.get("job_type") or "FULL_TIME").upper(),
        "hiringOrganization": {
            "@type": "Organization",
            "name": job.get("company", ""),
            "logo": job.get("company_logo", "")
        },
        "jobLocation": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": job.get("location", ""),
                "addressRegion": job.get("state") if job.get("state") not in (None, "", "Remote", "International", "Other") else None,
                "addressCountry": "KE" if job.get("state") != "International" else None,
            }
        },
        "jobLocationType": "TELECOMMUTE" if job.get("work_arrangement") == "remote" or job.get("state") == "Remote" else None,
        "description": job.get("description", "")[:5000],
        "baseSalary": {
            "@type": "MonetaryAmount",
            "currency": job.get("salary_currency") or "KES",
            "value": {
                "@type": "QuantitativeValue",
                "minValue": job.get("salary_min", 0),
                "maxValue": job.get("salary_max", 0),
                # Kenyan salaries are quoted monthly; anything else stored in the system is annual
                "unitText": "MONTH" if (job.get("salary_currency") or "KES") == "KES" else "YEAR"
            }
        } if job.get("salary_min") else None,
        "url": canonical,
    }
    # Remove None values (top level and inside the address) before dumping
    schema["jobLocation"]["address"] = {k: v for k, v in schema["jobLocation"]["address"].items() if v is not None}
    schema = {k: v for k, v in schema.items() if v is not None}
    return f'<script type="application/ld+json">{_jsonld_dumps(schema)}</script>'


def _jsonld_dumps(obj) -> str:
    """json.dumps that is safe to embed inside a <script> tag: a job description
    containing '</script>' must not be able to terminate the block."""
    import json
    return json.dumps(obj, ensure_ascii=False).replace('</', '<\\/')


def breadcrumbs_jsonld(items: list[dict]) -> str:
    """
    items = list of {"name": "Jobs", "url": "/jobs"}, ...
    Returns JSON-LD BreadcrumbList script tag.
    """
    import json
    schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "name": item["name"],
                "item": canonical_url(item["url"])
            }
            for i, item in enumerate(items)
        ]
    }
    return f'<script type="application/ld+json">{_jsonld_dumps(schema)}</script>'


# ─────────────────────────────────────────────────────────────────────────────
# 4. NOINDEX HELPERS (for internal/personalized pages)
# ─────────────────────────────────────────────────────────────────────────────

# Routes that should NEVER be indexed — add to templates via meta tag
NOINDEX_ROUTES = {
    '/user', '/employer', '/admin',
    '/login', '/register', '/forgot-password',
    '/reset-password.html',
    '/api/',   # API endpoints have no business in search results
}

def should_noindex(path: str) -> bool:
    """Return True if this route should get <meta name="robots" content="noindex">."""
    path = path.rstrip('/')
    for noindex_path in NOINDEX_ROUTES:
        if path == noindex_path.rstrip('/') or path.startswith(noindex_path.rstrip('/')):
            return True
    return False
