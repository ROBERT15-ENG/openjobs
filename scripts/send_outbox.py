#!/usr/bin/env python3
"""Deliver queued emails from the ``email_outbox`` table.

Usage:
  python3 scripts/send_outbox.py            # send up to 100 pending emails
  python3 scripts/send_outbox.py --limit 500
  python3 scripts/send_outbox.py --loop 30  # keep running, poll every 30s

The web app queues mail and drains opportunistically in a background thread;
run this from cron (every few minutes) or as a worker process so mail is still
delivered after restarts or SMTP outages.
"""

import argparse
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
API = os.path.join(ROOT, 'api')
sys.path.insert(0, API)
sys.path.insert(0, ROOT)

from email_notifier import drain_outbox, is_configured  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description='Send queued OpenJobs emails')
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--loop', type=int, default=0, help='Poll interval in seconds (0 = run once)')
    parser.add_argument('--db', default=os.environ.get('DATABASE_PATH', os.path.join(ROOT, 'jobs.db')))
    args = parser.parse_args()

    if not is_configured():
        print('SMTP not configured (SMTP_HOST/SMTP_USER/SMTP_PASS); nothing to do.')
        return 1
    if not os.path.exists(args.db):
        print(f'Database not found: {args.db}')
        return 1

    while True:
        result = drain_outbox(limit=args.limit, db_path=args.db)
        print(result)
        if not args.loop:
            return 0
        time.sleep(args.loop)


if __name__ == '__main__':
    raise SystemExit(main())
