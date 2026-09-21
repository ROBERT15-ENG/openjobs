#!/usr/bin/env python3
"""
sitemap_generator.py — Generate XML sitemaps dynamically from the database.
Flask route handlers (get_sitemap_*) must be called within app context.
"""
import os
import sqlite3
from datetime import datetime

SITE_URL = os.environ.get('APP_URL', 'https://openjobs.co.ke').rstrip('/')
DB_PATH  = os.environ.get('DATABASE_URL',
           os.path.join(os.path.dirname(__file__), 'jobs.db'))

# ── XML helpers ────────────────────────────────────────────────────────────────

def xml_escape(s):
    if not isinstance(s, str):
        return ''
    return (s.replace('&', '&amp;')
              .replace('<', '&lt;')
              .replace('>', '&gt;')
              .replace('"', '&quot;')
              .replace("'", '&apos;'))

def lastmod(date_str):
    if not date_str:
        return datetime.now().strftime('%Y-%m-%d')
    return date_str[:10]

# ── Static pages sitemap ───────────────────────────────────────────────────────

STATIC_PAGES = [
    {'loc': '/',          'priority': '1.0', 'changefreq': 'daily'},
    {'loc': '/jobs',      'priority': '0.9', 'changefreq': 'daily'},
    {'loc': '/companies', 'priority': '0.7', 'changefreq': 'weekly'},
    {'loc': '/salary',    'priority': '0.6', 'changefreq': 'monthly'},
    {'loc': '/login',     'priority': '0.3', 'changefreq': 'monthly'},
    {'loc': '/register',  'priority': '0.3', 'changefreq': 'monthly'},
    {'loc': '/privacy',   'priority': '0.3', 'changefreq': 'yearly'},
    {'loc': '/terms',     'priority': '0.3', 'changefreq': 'yearly'},
]

def generate_static_sitemap():
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for pg in STATIC_PAGES:
        loc = f"{SITE_URL}{pg['loc']}"
        lines.append('  <url>')
        lines.append(f'    <loc>{xml_escape(loc)}</loc>')
        lines.append(f'    <changefreq>{pg["changefreq"]}</changefreq>')
        lines.append(f'    <priority>{pg["priority"]}</priority>')
        lines.append('  </url>')
    lines.append('</urlset>')
    return '\n'.join(lines)

# ── Jobs sitemap ──────────────────────────────────────────────────────────────

def _make_slug(title, job_id):
    import re
    s = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    return f"{s}-{job_id}"

def generate_jobs_sitemap(limit=5000):
    try:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        rows = con.execute("""
            SELECT id, title, company, location, created_at, is_featured
            FROM jobs
            WHERE is_active = 1
              AND (expires_at IS NULL OR expires_at > date('now'))
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        con.close()
    except Exception as e:
        print(f"[sitemap] DB error: {e}")
        rows = []

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for job in rows:
        slug    = _make_slug(job['title'], job['id'])
        loc     = f"{SITE_URL}/jobs/{slug}"
        lm      = lastmod(job['created_at'] or '')
        pri     = '0.9' if job['is_featured'] else '0.7'
        lines.append('  <url>')
        lines.append(f'    <loc>{xml_escape(loc)}</loc>')
        lines.append(f'    <lastmod>{lm}</lastmod>')
        lines.append(f'    <changefreq>daily</changefreq>')
        lines.append(f'    <priority>{pri}</priority>')
        lines.append('  </url>')
    lines.append('</urlset>')
    return '\n'.join(lines)

# ── Companies + classification landing pages sitemap ──────────────────────────

def generate_companies_sitemap(limit=2000):
    import sys
    from urllib.parse import urlencode
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api'))
    from seo_utils import make_slug
    from taxonomy import CLASSIFICATIONS, REGIONS

    rows = []
    try:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        rows = con.execute("""
            SELECT company, MAX(created_at) AS latest FROM jobs
            WHERE is_active = 1 AND company IS NOT NULL AND company != ''
            GROUP BY LOWER(company) ORDER BY latest DESC LIMIT ?
        """, (limit,)).fetchall()
        con.close()
    except Exception as e:
        print(f"[sitemap] DB error: {e}")

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    def add(loc, lm, freq, pri):
        lines.append('  <url>')
        lines.append(f'    <loc>{xml_escape(loc)}</loc>')
        lines.append(f'    <lastmod>{lm}</lastmod>')
        lines.append(f'    <changefreq>{freq}</changefreq>')
        lines.append(f'    <priority>{pri}</priority>')
        lines.append('  </url>')

    today = datetime.now().strftime('%Y-%m-%d')
    for name in CLASSIFICATIONS:
        add(f"{SITE_URL}/jobs?{urlencode({'classification': name})}", today, 'daily', '0.8')
    for region in REGIONS:
        add(f"{SITE_URL}/jobs?{urlencode({'state': region})}", today, 'daily', '0.7')
    for r in rows:
        add(f"{SITE_URL}/companies/{make_slug(r['company'])}", lastmod(r['latest'] or ''), 'weekly', '0.6')
    lines.append('</urlset>')
    return '\n'.join(lines)

# ── Master sitemap index ───────────────────────────────────────────────────────

def generate_sitemap_index():
    now = datetime.now().strftime('%Y-%m-%d')
    sub_maps = [
        {'loc': f"{SITE_URL}/sitemap-static.xml",    'lastmod': now},
        {'loc': f"{SITE_URL}/sitemap-jobs.xml",      'lastmod': now},
        {'loc': f"{SITE_URL}/sitemap-companies.xml", 'lastmod': now},
    ]
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for sm in sub_maps:
        lines.append('  <sitemap>')
        lines.append(f'    <loc>{xml_escape(sm["loc"])}</loc>')
        lines.append(f'    <lastmod>{sm["lastmod"]}</lastmod>')
        lines.append('  </sitemap>')
    lines.append('</sitemapindex>')
    return '\n'.join(lines)

# ── Flask response wrappers (must run inside Flask app context) ────────────────

def _make_response(xml_str, mimetype='application/xml'):
    from flask import make_response
    r = make_response(xml_str)
    r.content_type = f'{mimetype}; charset=utf-8'
    return r

def get_sitemap_index():
    return _make_response(generate_sitemap_index())

def get_sitemap_static():
    return _make_response(generate_static_sitemap())

def get_sitemap_jobs():
    return _make_response(generate_jobs_sitemap())

def get_sitemap_companies():
    return _make_response(generate_companies_sitemap())
