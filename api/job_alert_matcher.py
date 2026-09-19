"""Match saved job alerts to listings and send notification emails."""

import os
import sqlite3
from typing import Dict, List, Optional

from seo_util import job_url_path
from timeutil import iso_before, utcnow_iso

from email_notifier import send_job_alert

BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5700')


def _connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    from db import connect

    return connect(db_path)


def _keyword_terms(keyword: str) -> List[str]:
    return [term for term in keyword.replace(',', ' ').lower().split() if term]


def job_matches_alert(job: Dict, alert: Dict) -> bool:
    """Return True when an active job satisfies alert criteria."""
    keyword = (alert.get('keyword') or '').strip()
    if keyword:
        haystack = ' '.join([
            str(job.get('title') or ''),
            str(job.get('description') or ''),
            str(job.get('skills') or ''),
            str(job.get('company') or ''),
        ]).lower()
        terms = _keyword_terms(keyword)
        if terms and not any(term in haystack for term in terms):
            return False

    location = (alert.get('location') or '').strip().lower()
    if location:
        job_loc = (job.get('location') or '').lower()
        if location not in job_loc and job_loc not in location:
            return False

    if alert.get('remote_only'):
        arrangement = (job.get('work_arrangement') or '').lower()
        if arrangement != 'remote':
            return False

    salary_min = alert.get('salary_min')
    if salary_min:
        job_min = job.get('salary_min')
        if job_min is not None and int(job_min) < int(salary_min):
            return False

    return True


def _job_payload(job: Dict) -> Dict:
    link = f"{BASE_URL.rstrip('/')}{job_url_path(job['id'], job.get('title', ''))}"
    return {
        'id': job['id'],
        'title': job.get('title'),
        'company': job.get('company'),
        'location': job.get('location'),
        'salary': job.get('salary'),
        'link': link,
    }


def find_new_matches_for_alert(
    conn: sqlite3.Connection,
    alert: Dict,
    since: Optional[str] = None,
) -> List[Dict]:
    """Jobs matching alert that have not been emailed for this alert yet."""
    query = 'SELECT * FROM jobs WHERE is_active = 1'
    params: List = []
    if since:
        query += ' AND created_at >= ?'
        params.append(since)
    query += ' ORDER BY created_at DESC LIMIT 200'
    jobs = [dict(row) for row in conn.execute(query, params).fetchall()]

    sent_rows = conn.execute(
        'SELECT job_id FROM job_alert_sends WHERE alert_id = ?',
        (alert['id'],),
    ).fetchall()
    sent_ids = {row['job_id'] for row in sent_rows}

    matches = []
    for job in jobs:
        if job['id'] in sent_ids:
            continue
        if job_matches_alert(job, alert):
            matches.append(job)
    return matches


def notify_alerts_for_job(job_id: int, db_path: Optional[str] = None) -> Dict:
    """Notify users with matching active alerts when a single job is posted."""
    conn = _connect(db_path)
    try:
        job_row = conn.execute('SELECT * FROM jobs WHERE id = ? AND is_active = 1', (job_id,)).fetchone()
        if not job_row:
            return {'job_id': job_id, 'alerts_notified': 0, 'emails_sent': 0}

        job = dict(job_row)
        alerts = conn.execute(
            """
            SELECT ja.*, u.email, u.name
            FROM job_alerts ja
            JOIN users u ON u.id = ja.user_id
            WHERE ja.active = 1 AND u.email IS NOT NULL
            """
        ).fetchall()

        notified = 0
        emails_sent = 0
        now = utcnow_iso()
        payload = _job_payload(job)

        for alert_row in alerts:
            alert = dict(alert_row)
            if not job_matches_alert(job, alert):
                continue
            already = conn.execute(
                'SELECT 1 FROM job_alert_sends WHERE alert_id = ? AND job_id = ?',
                (alert['id'], job_id),
            ).fetchone()
            if already:
                continue

            result = send_job_alert(
                alert['email'],
                alert.get('name') or 'there',
                [payload],
                alert.get('keyword') or job.get('title', ''),
            )
            conn.execute(
                'INSERT INTO job_alert_sends (alert_id, job_id, sent_at) VALUES (?, ?, ?)',
                (alert['id'], job_id, now),
            )
            # Commit per alert: send_job_alert writes to the outbox on its own
            # connection and must not wait on this one's write lock.
            conn.commit()
            notified += 1
            if result.get('success'):
                emails_sent += 1

        return {'job_id': job_id, 'alerts_notified': notified, 'emails_sent': emails_sent}
    finally:
        conn.close()


def run_job_alert_matching(
    since_hours: int = 24,
    dry_run: bool = False,
    db_path: Optional[str] = None,
) -> Dict:
    """Scan recent jobs against all active alerts (for cron / admin trigger)."""
    conn = _connect(db_path)
    since = iso_before(hours=since_hours) if since_hours > 0 else None

    try:
        alerts = conn.execute(
            """
            SELECT ja.*, u.email, u.name
            FROM job_alerts ja
            JOIN users u ON u.id = ja.user_id
            WHERE ja.active = 1 AND u.email IS NOT NULL
            """
        ).fetchall()

        summary = {
            'dry_run': dry_run,
            'since_hours': since_hours,
            'alerts_checked': len(alerts),
            'notifications': 0,
            'emails_sent': 0,
            'jobs_matched': 0,
        }

        now = utcnow_iso()
        for alert_row in alerts:
            alert = dict(alert_row)
            matches = find_new_matches_for_alert(conn, alert, since=since)
            if not matches:
                continue

            summary['jobs_matched'] += len(matches)
            if dry_run:
                summary['notifications'] += 1
                continue

            jobs_payload = [_job_payload(job) for job in matches[:5]]
            result = send_job_alert(
                alert['email'],
                alert.get('name') or 'there',
                jobs_payload,
                alert.get('keyword') or 'your criteria',
            )
            for job in matches:
                conn.execute(
                    'INSERT OR IGNORE INTO job_alert_sends (alert_id, job_id, sent_at) VALUES (?, ?, ?)',
                    (alert['id'], job['id'], now),
                )
            conn.commit()
            summary['notifications'] += 1
            if result.get('success'):
                summary['emails_sent'] += 1

        return summary
    finally:
        conn.close()
