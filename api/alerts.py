#!/usr/bin/env python3
"""
Saved-search job alerts.

- dispatch_instant_alerts(db_path, job_id): called (in a thread) right after a job is created;
  emails every user whose *instant* alert matches the new job.
- run_digests(db_path): emails each *daily* alert the jobs created since it was last sent.
  Run from cron:  python api/alerts.py --db /path/to/jobs.db

Both functions open their own SQLite connection so they are safe outside a Flask request.
"""
import argparse
import datetime
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search import parse_filters, search_jobs, job_matches_alert  # noqa: E402
from taxonomy import format_salary  # noqa: E402
from seo_utils import make_job_slug  # noqa: E402

APP_URL = os.environ.get('APP_URL', 'http://localhost:5700').rstrip('/')


def _connect(db_path):
    con = sqlite3.connect(db_path, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def _email_job(job) -> dict:
    return {
        'title': job['title'], 'company': job['company'], 'location': job['location'],
        'salary': format_salary(job['salary_min'], job['salary_max'], job['salary_currency']) or 'Competitive',
        'link': f"{APP_URL}/jobs/{make_job_slug(job['title'] or 'job', job['id'])}",
    }


def alert_label(alert) -> str:
    parts = [alert['keywords'], alert['classification'], alert['location']]
    return alert['name'] or ' · '.join(p for p in parts if p) or 'All jobs'


def _send(alert, user, jobs) -> bool:
    try:
        from email_notifier import send_job_alert, is_configured
    except ImportError:
        return False
    if not is_configured():
        print(f"[alerts] SMTP not configured; would email {user['email']} {len(jobs)} job(s) for '{alert_label(alert)}'")
        return False
    res = send_job_alert(user['email'], user['name'] or 'there', [_email_job(j) for j in jobs], alert_label(alert))
    return bool(res.get('success'))


def dispatch_instant_alerts(db_path, job_id) -> int:
    """Email users whose instant alerts match the given job. Returns number of emails attempted."""
    sent = 0
    try:
        con = _connect(db_path)
    except sqlite3.Error as e:
        print(f"[alerts] cannot open db: {e}")
        return 0
    try:
        job = con.execute("SELECT * FROM jobs WHERE id = ? AND is_active = 1", (job_id,)).fetchone()
        if not job:
            return 0
        alerts = con.execute(
            """SELECT a.*, u.email, u.name FROM job_alerts a JOIN users u ON u.id = a.user_id
               WHERE a.is_active = 1 AND a.frequency = 'instant' AND u.email IS NOT NULL"""
        ).fetchall()
        now = datetime.datetime.now().isoformat()
        for alert in alerts:
            if job_matches_alert(con, alert, job_id):
                _send(alert, alert, [job])
                con.execute("UPDATE job_alerts SET last_sent_at = ? WHERE id = ?", (now, alert['id']))
                sent += 1
        con.commit()
    except Exception as e:
        print(f"[alerts] instant dispatch failed: {e}")
    finally:
        con.close()
    return sent


def run_digests(db_path, dry_run=False) -> int:
    """Send daily digests for alerts that have not been sent in the last ~23 hours."""
    con = _connect(db_path)
    sent = 0
    try:
        cutoff = (datetime.datetime.now() - datetime.timedelta(hours=23)).isoformat()
        alerts = con.execute(
            """SELECT a.*, u.email, u.name FROM job_alerts a JOIN users u ON u.id = a.user_id
               WHERE a.is_active = 1 AND a.frequency = 'daily' AND u.email IS NOT NULL
                 AND (a.last_sent_at IS NULL OR a.last_sent_at < ?)""", (cutoff,)
        ).fetchall()
        now = datetime.datetime.now().isoformat()
        for alert in alerts:
            since = alert['last_sent_at'] or (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
            filters = parse_filters({
                'q': alert['keywords'], 'location': alert['location'], 'classification': alert['classification'],
                'work_type': alert['work_type'], 'work_arrangement': alert['work_arrangement'],
                'salary_min': alert['salary_min'], 'since': since,
            })
            jobs = search_jobs(con, filters, page=1, limit=10, sort='date')['jobs']
            if not jobs:
                continue
            print(f"[alerts] digest -> {alert['email']}: {len(jobs)} job(s) for '{alert_label(alert)}'")
            if not dry_run:
                _send(alert, alert, jobs)
                con.execute("UPDATE job_alerts SET last_sent_at = ? WHERE id = ?", (now, alert['id']))
            sent += 1
        con.commit()
    finally:
        con.close()
    return sent


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Send daily job-alert digests')
    ap.add_argument('--db', default=os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'jobs.db')))
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    n = run_digests(a.db, dry_run=a.dry_run)
    print(f"[alerts] {n} digest(s) {'would be ' if a.dry_run else ''}sent")
