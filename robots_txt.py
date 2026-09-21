#!/usr/bin/env python3
"""
robots_txt.py — Generate robots.txt dynamically.
SITE_URL is read at request time (not module load) so it respects env changes.
"""
import os

SITE_URL    = os.environ.get('APP_URL', 'https://openjobs.co.ke').rstrip('/')
SITEMAP_URL = f"{SITE_URL}/sitemap-index.xml"

_ROBOTS_TXT = """\
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# robots.txt — OpenJobs.co.ke
# Generated dynamically — do not edit manually.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User-agent: *
Allow: /

# Block AI training bots
User-agent: GPTBot
User-agent: ChatGPT-User
User-agent: Claude-Web
User-agent: Bytespider
User-agent: Amazonbot
Disallow: /

User-agent: Googlebot
Allow: /

Sitemap: {sitemap}

# ── Staging / dev ─────────────────────────────────────────────────────────────
Disallow: /localhost/
Disallow: /127.0.0.1/
Disallow: /staging/
Disallow: /preview/

# ── Internal flows — never crawl ───────────────────────────────────────────────
Disallow: /api/
Disallow: /login
Disallow: /register
Disallow: /forgot-password
Disallow: /reset-password.html
Disallow: /user
Disallow: /employer
Disallow: /admin

# ── UTM / ad tracking params — stripped server-side, but block at CDN level ───
Disallow: /*utm_*
Disallow: /*fbclid=*
Disallow: /*gclid=*
Disallow: /*sessionid=*
Disallow: /*ref=*

# ── Search/filter query params (canonical is the clean URL) ───────────────────
Disallow: /jobs/*?*sort=*
Disallow: /jobs/*?*filter=*
Disallow: /jobs/*?*page=*

# ── Hash navigation (client-side only) ─────────────────────────────────────────
Disallow: /*#
""".format(sitemap=SITEMAP_URL)


def get_robots_txt():
    """Return Flask response. Must be called within Flask app context."""
    from flask import make_response
    r = make_response(_ROBOTS_TXT)
    r.content_type = 'text/plain; charset=utf-8'
    return r
