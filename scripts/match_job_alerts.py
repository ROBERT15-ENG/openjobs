#!/usr/bin/env python3
"""Match job alerts to recent listings and send notification emails.

Usage:
  python3 scripts/match_job_alerts.py
  python3 scripts/match_job_alerts.py --since-hours 48
  python3 scripts/match_job_alerts.py --dry-run

Set SMTP_HOST, SMTP_USER, SMTP_PASS for real delivery; otherwise logs no-op sends.
"""

import argparse
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
API = os.path.join(ROOT, 'api')
sys.path.insert(0, API)
sys.path.insert(0, ROOT)

from job_alert_matcher import run_job_alert_matching  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description='Run job alert email matching')
    parser.add_argument('--since-hours', type=int, default=24, help='Only consider jobs from the last N hours')
    parser.add_argument('--dry-run', action='store_true', help='Match without sending email or recording sends')
    parser.add_argument('--db', default=os.environ.get('DATABASE_PATH', os.path.join(ROOT, 'jobs.db')))
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f'Database not found: {args.db}')
        print('Run: python3 scripts/init_db.py')
        return 1

    os.environ.setdefault('DATABASE_PATH', args.db)
    result = run_job_alert_matching(since_hours=args.since_hours, dry_run=args.dry_run, db_path=args.db)
    print(result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
