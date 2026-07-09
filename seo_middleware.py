#!/usr/bin/env python3
"""
seo_middleware.py — SEO URL normalization patterns.
Patterns are embedded directly in server.py as before_request hooks.
This file documents the logic for reference and can be used as a checklist.

CHECKLIST — URL Canonicalization
================================
For every new Flask route added, verify:

[x] No trailing slash in canonical URLs
    Bad:  /jobs/
    Good: /jobs

[x] Lowercase only
    Bad:  /Jobs/123
    Good: /jobs/123

[x] ID appended to slugs (not just title) for uniqueness
    Bad:  /jobs/senior-python-engineer
    Good: /jobs/senior-python-engineer-1234

[x] No UTM parameters in canonical form
    Bad:  /jobs/python-dev?utm_source=linkedin
    Good: /jobs/python-dev  (utm_source stripped before routing)

[x] Canonical declared in <head> of every page
    <link rel="canonical" href="https://openjobs.com.au/jobs/python-dev-1234">

[x] Self-referential canonical (not a redirect target)
    The canonical <link> tag tells Google which URL is the master.

NOINDEX checklist — pages that should NEVER appear in search results:
========================================================================
[ ] /user        — personal job seeker dashboard
[ ] /employer    — employer dashboard
[ ] /admin       — admin panel
[ ] /login       — login page
[ ] /register    — registration page
[ ] /forgot-password
[ ] /reset-password.html
[ ] /api/*       — all API endpoints

Add this to the <head> of any noindex page:
  <meta name="robots" content="noindex">

JSON-LD structured data checklist:
==================================
[ ] Job listing pages → JobPosting schema (see seo_utils.py)
[ ] Home page          → WebSite schema + SearchAction
[ ] Company pages      → Organization schema
[ ] Breadcrumbs        → BreadcrumbList on all inner pages

Sitemap checklist:
==================
[ ] /sitemap-index.xml    — master index, references sub-maps
[ ] /sitemap-static.xml    — home, about, terms, privacy, login, register
[ ] /sitemap-jobs.xml     — every active job, canonical URL, lastmod, priority
[ ] robots.txt includes:  Sitemap: https://openjobs.com.au/sitemap-index.xml
[ ] robots.txt blocks:     /api/, /user, /employer, /admin, /login, /register

Crawl budget protection:
=======================
[ ] No infinite scroll triggered by Googlebot (use paginated /jobs?page=2)
[ ] No client-side tab switching that loads content after page load
    (all job listings in initial HTML response)
[ ] ?utm_*, ?fbclid, ?gclid params stripped before routing
[ ] Pagination links use full URLs, not JavaScript-only navigation
"""
