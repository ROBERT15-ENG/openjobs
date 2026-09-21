#!/usr/bin/env python3
"""
Job search: filter parsing, SQL building (FTS5 relevance with LIKE fallback) and facets.

Used by GET /api/jobs, the job-alert matcher and the sitemap. Everything here takes a
plain sqlite3 connection so it also works outside a Flask request.
"""
import datetime
import re
import sqlite3

from taxonomy import (AU_STATES, SALARY_BANDS, DATE_LISTED_OPTIONS,
                      normalize_classification, normalize_subclassification)
from db_schema import fts_available

JOB_COLUMNS = ["id", "title", "company", "location", "state", "salary", "salary_min", "salary_max",
               "salary_currency", "description", "category", "classification", "subclassification",
               "work_type", "work_arrangement", "skills", "created_at", "is_active", "expires_at",
               "view_count", "is_featured", "application_count", "company_rating", "employer_id"]

# bm25 weights per FTS column: title, company, location, description, skills, search_summary, classification
BM25_WEIGHTS = (10.0, 5.0, 1.0, 1.0, 3.0, 2.0, 2.0)

SORT_OPTIONS = ('relevance', 'date', 'salary_desc', 'salary_asc')

_TOKEN_RE = re.compile(r"[0-9A-Za-z\u00C0-\u024F]+")


def _csv(value):
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [v for v in value if v]
    return [v.strip() for v in str(value).split(',') if v.strip()]


def parse_filters(args) -> dict:
    """Normalise request args (a dict-like with .get) into a filter dict."""
    def _int(name):
        v = args.get(name)
        try:
            return int(v) if v not in (None, '') else None
        except (TypeError, ValueError):
            return None

    f = {
        'q': (args.get('q') or '').strip(),
        'location': (args.get('location') or '').strip(),
        'state': (args.get('state') or '').strip().upper() or None,
        'classification': normalize_classification(args.get('classification')),
        'subclassification': None,
        'work_type': _csv(args.get('work_type')),
        'work_arrangement': _csv(args.get('work_arrangement')),
        'salary_min': _int('salary_min'),
        'salary_max': _int('salary_max'),
        'date_listed': _int('date_listed'),
        'company': (args.get('company') or '').strip(),
        'category': (args.get('category') or '').strip(),
        'employer_id': _int('employer_id'),
        'since': args.get('since'),  # ISO timestamp, used by alerts
    }
    f['subclassification'] = normalize_subclassification(f['classification'], args.get('subclassification'))
    if f['state'] == 'REMOTE':
        f['state'] = 'Remote'
    return f


def fts_query(q: str) -> str:
    """Turn free text into a safe FTS5 query: each token becomes a quoted prefix term (implicit AND)."""
    tokens = _TOKEN_RE.findall(q or '')
    return ' '.join(f'"{t}"*' for t in tokens[:12])


def _location_clause(location: str):
    """Free-text 'where' box: exact state/'Remote' -> state filter, otherwise substring match."""
    loc = location.strip()
    if loc.lower().startswith('all '):
        loc = loc[4:]
    upper = loc.upper()
    if upper in AU_STATES:
        return "jobs.state = ?", [upper]
    for abbr, name in AU_STATES.items():
        if name.lower() == loc.lower():
            return "jobs.state = ?", [abbr]
    if loc.lower() in ('remote', 'work from home', 'wfh'):
        return "(jobs.state = 'Remote' OR jobs.work_arrangement = 'remote')", []
    if loc.lower() in ('australia',):
        return "jobs.state != 'International'", []
    return "jobs.location LIKE ?", [f"%{loc}%"]


def build_where(f: dict, exclude=None, use_fts=False):
    """Return (where_sql, params). `exclude` skips one dimension (for facet counts).
    Columns are qualified with `jobs.` because the FTS join exposes same-named columns."""
    where = ["jobs.is_active = 1", "(jobs.expires_at IS NULL OR jobs.expires_at > ?)"]
    params = [datetime.datetime.now().isoformat()]

    if f.get('q') and not use_fts:
        like = f"%{f['q']}%"
        where.append("(jobs.title LIKE ? OR jobs.company LIKE ? OR jobs.description LIKE ? "
                     "OR jobs.skills LIKE ? OR jobs.search_summary LIKE ?)")
        params += [like] * 5
    if f.get('location') and exclude != 'location':
        sql, p = _location_clause(f['location'])
        where.append(sql); params += p
    if f.get('state') and exclude != 'state':
        where.append("jobs.state = ?"); params.append(f['state'])
    if f.get('classification') and exclude != 'classification':
        where.append("jobs.classification = ?"); params.append(f['classification'])
        if f.get('subclassification') and exclude != 'subclassification':
            where.append("jobs.subclassification = ?"); params.append(f['subclassification'])
    if f.get('category'):
        where.append("jobs.category = ?"); params.append(f['category'])
    if f.get('company'):
        where.append("LOWER(jobs.company) = LOWER(?)"); params.append(f['company'])
    if f.get('employer_id'):
        where.append("jobs.employer_id = ?"); params.append(f['employer_id'])
    if f.get('work_type') and exclude != 'work_type':
        ph = ','.join('?' * len(f['work_type']))
        where.append(f"jobs.work_type IN ({ph})"); params += f['work_type']
    if f.get('work_arrangement') and exclude != 'work_arrangement':
        ph = ','.join('?' * len(f['work_arrangement']))
        where.append(f"jobs.work_arrangement IN ({ph})"); params += f['work_arrangement']
    if exclude != 'salary':
        if f.get('salary_min'):
            where.append("(jobs.salary_max >= ? OR (jobs.salary_max IS NULL AND jobs.salary_min >= ?))")
            params += [f['salary_min'], f['salary_min']]
        if f.get('salary_max'):
            where.append("(jobs.salary_min <= ? OR (jobs.salary_min IS NULL AND jobs.salary_max <= ?))")
            params += [f['salary_max'], f['salary_max']]
    if f.get('date_listed') and exclude != 'date_listed':
        since = datetime.datetime.now() - datetime.timedelta(days=f['date_listed'])
        where.append("jobs.created_at >= ?"); params.append(since.isoformat())
    if f.get('since'):
        where.append("jobs.created_at > ?"); params.append(f['since'])
    return " AND ".join(where), params


def _order_by(sort: str, has_relevance: bool) -> str:
    if sort == 'relevance' and has_relevance:
        return "is_featured DESC, rank ASC, created_at DESC"   # bm25: lower is better
    if sort == 'salary_desc':
        return "is_featured DESC, COALESCE(salary_max, salary_min) DESC NULLS LAST, created_at DESC"
    if sort == 'salary_asc':
        return "is_featured DESC, COALESCE(salary_min, salary_max) ASC NULLS LAST, created_at DESC"
    return "is_featured DESC, created_at DESC"


def search_jobs(db, f: dict, page=1, limit=20, sort=None, include_facets=False):
    """Run a search. Returns {'jobs': [...], 'pagination': {...}, 'facets': {...}?, 'sort': str}."""
    page = max(1, page)
    limit = max(1, min(limit, 100))
    offset = (page - 1) * limit
    if sort not in SORT_OPTIONS:
        sort = 'relevance' if f.get('q') else 'date'

    match = fts_query(f['q']) if f.get('q') else ''
    use_fts = bool(match) and fts_available(db)
    cols = ', '.join(f"jobs.{c}" for c in JOB_COLUMNS)

    def run(use_fts):
        where, params = build_where(f, use_fts=use_fts)
        if use_fts:
            weights = ', '.join(str(w) for w in BM25_WEIGHTS)
            base_from = "FROM jobs JOIN jobs_fts ON jobs_fts.rowid = jobs.id"
            where = f"jobs_fts MATCH ? AND {where}"
            params = [match] + params
            select = f"SELECT {cols}, bm25(jobs_fts, {weights}) AS rank, " \
                     f"snippet(jobs_fts, 3, '<mark>', '</mark>', '…', 28) AS snippet {base_from} WHERE {where}"
        else:
            base_from = "FROM jobs"
            select = f"SELECT {cols}, 0 AS rank, NULL AS snippet {base_from} WHERE {where}"
        total = db.execute(f"SELECT COUNT(*) {base_from} WHERE {where}", params).fetchone()[0]
        rows = db.execute(f"{select} ORDER BY {_order_by(sort, use_fts)} LIMIT ? OFFSET ?",
                          params + [limit, offset]).fetchall()
        return total, rows

    try:
        total, rows = run(use_fts)
    except sqlite3.OperationalError:
        use_fts = False
        total, rows = run(False)

    result = {
        'jobs': [dict(r) for r in rows],
        'pagination': {'page': page, 'limit': limit, 'total': total, 'pages': (total + limit - 1) // limit},
        'sort': sort if (sort != 'relevance' or use_fts) else 'date',
    }
    if include_facets:
        result['facets'] = facets(db, f, match if use_fts else '')
    return result


def _facet_query(db, f, dim, select_expr, group=True, match=''):
    where, params = build_where(f, exclude=dim, use_fts=bool(match))
    base_from = "FROM jobs"
    if match:
        base_from = "FROM jobs JOIN jobs_fts ON jobs_fts.rowid = jobs.id"
        where = f"jobs_fts MATCH ? AND {where}"
        params = [match] + params
    sql = f"SELECT {select_expr} {base_from} WHERE {where}"
    if group:
        sql += " GROUP BY 1 ORDER BY 2 DESC"
    return db.execute(sql, params).fetchall()


def facets(db, f: dict, match: str = ''):
    """Counts per filter value, each computed with that dimension's own filter removed."""
    out = {}
    for dim in ('work_type', 'work_arrangement', 'classification', 'state'):
        rows = _facet_query(db, f, dim, f"jobs.{dim} AS value, COUNT(*) AS count", match=match)
        out[dim] = [{'value': r['value'], 'count': r['count']} for r in rows if r['value']]

    if f.get('classification'):
        rows = _facet_query(db, f, 'subclassification', "jobs.subclassification AS value, COUNT(*) AS count", match=match)
        out['subclassification'] = [{'value': r['value'], 'count': r['count']} for r in rows if r['value']]

    now = datetime.datetime.now()
    cases = ', '.join(f"SUM(CASE WHEN jobs.created_at >= '{(now - datetime.timedelta(days=d)).isoformat()}' THEN 1 ELSE 0 END) AS d{d}"
                      for d, _ in DATE_LISTED_OPTIONS)
    row = _facet_query(db, f, 'date_listed', cases, group=False, match=match)[0]
    out['date_listed'] = [{'value': d, 'label': label, 'count': row[f'd{d}']} for d, label in DATE_LISTED_OPTIONS]

    band_cases = []
    for i, (lo, hi, _) in enumerate(SALARY_BANDS):
        cond = f"COALESCE(jobs.salary_max, jobs.salary_min) >= {lo}"
        if hi is not None:
            cond += f" AND COALESCE(jobs.salary_max, jobs.salary_min) < {hi}"
        band_cases.append(f"SUM(CASE WHEN {cond} THEN 1 ELSE 0 END) AS b{i}")
    row = _facet_query(db, f, 'salary', ', '.join(band_cases), group=False, match=match)[0]
    out['salary'] = [{'min': lo, 'max': hi, 'label': label, 'count': row[f'b{i}']}
                     for i, (lo, hi, label) in enumerate(SALARY_BANDS)]
    return out


def suggest_keywords(db, q: str, limit=8):
    """Autocomplete for the 'what' box: job titles, skills and companies starting with q."""
    q = (q or '').strip()
    if len(q) < 2:
        return []
    like = f"{q}%"
    any_like = f"% {q}%"
    seen, out = set(), []
    for row in db.execute(
        "SELECT title AS v, COUNT(*) AS n FROM jobs WHERE is_active = 1 AND (title LIKE ? OR title LIKE ?) "
        "GROUP BY LOWER(title) ORDER BY n DESC LIMIT ?", (like, any_like, limit)):
        if row['v'].lower() not in seen:
            seen.add(row['v'].lower()); out.append({'value': row['v'], 'type': 'title', 'count': row['n']})
    for row in db.execute("SELECT name AS v FROM skills_taxonomy WHERE name LIKE ? ORDER BY demand_score DESC LIMIT ?", (like, limit)):
        if row['v'].lower() not in seen:
            seen.add(row['v'].lower()); out.append({'value': row['v'], 'type': 'skill'})
    for row in db.execute(
        "SELECT company AS v, COUNT(*) AS n FROM jobs WHERE is_active = 1 AND company LIKE ? "
        "GROUP BY LOWER(company) ORDER BY n DESC LIMIT ?", (like, limit)):
        if row['v'].lower() not in seen:
            seen.add(row['v'].lower()); out.append({'value': row['v'], 'type': 'company', 'count': row['n']})
    return out[:limit]


def suggest_locations(db, q: str, limit=8):
    from taxonomy import all_locations
    q = (q or '').strip().lower()
    if len(q) < 2:
        return []
    seen, out = set(), []
    for row in db.execute(
        "SELECT location AS v, COUNT(*) AS n FROM jobs WHERE is_active = 1 AND location LIKE ? "
        "GROUP BY LOWER(location) ORDER BY n DESC LIMIT ?", (f"%{q}%", limit)):
        if row['v'] and row['v'].lower() not in seen:
            seen.add(row['v'].lower()); out.append({'value': row['v'], 'count': row['n']})
    for loc in all_locations():
        if q in loc.lower() and loc.lower() not in seen and len(out) < limit:
            seen.add(loc.lower()); out.append({'value': loc})
    return out[:limit]


def job_matches_alert(db, alert, job_id) -> bool:
    """Does a single (just-created) job satisfy a saved-search alert?"""
    f = parse_filters({
        'q': alert['keywords'], 'location': alert['location'], 'classification': alert['classification'],
        'work_type': alert['work_type'], 'work_arrangement': alert['work_arrangement'],
        'salary_min': alert['salary_min'],
    })
    match = fts_query(f['q']) if f['q'] else ''
    use_fts = bool(match) and fts_available(db)
    where, params = build_where(f, use_fts=use_fts)
    if use_fts:
        sql = f"SELECT 1 FROM jobs JOIN jobs_fts ON jobs_fts.rowid = jobs.id WHERE jobs_fts MATCH ? AND {where} AND jobs.id = ?"
        params = [match] + params + [job_id]
    else:
        sql = f"SELECT 1 FROM jobs WHERE {where} AND id = ?"
        params = params + [job_id]
    try:
        return db.execute(sql, params).fetchone() is not None
    except sqlite3.OperationalError:
        return False
