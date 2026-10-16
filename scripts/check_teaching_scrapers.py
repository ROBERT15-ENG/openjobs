#!/usr/bin/env python3
"""
Check Australian teaching vacancy sources (NSW JobFeed by default — not SEEK).

Usage:
  PYTHONPATH=. python scripts/check_teaching_scrapers.py
  PYTHONPATH=. python scripts/check_teaching_scrapers.py --seek   # opt-in SEEK
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scrapers.sources.nsw_jobfeed import search_nsw_jobfeed
from scrapers.teaching_au import fetch_teaching_sponsorship_jobs


def main():
    parser = argparse.ArgumentParser(description="Check AU teaching scrapers (no SEEK by default)")
    parser.add_argument(
        "--seek",
        action="store_true",
        help="Also query SEEK (requires SCRAPER_ALLOW_SEEK or explicit sources)",
    )
    parser.add_argument(
        "--all-nsw",
        action="store_true",
        help="List all NSW JobFeed roles (ignore sponsorship/relocation filter)",
    )
    args = parser.parse_args()

    feed = search_nsw_jobfeed(require_mobility_or_sponsor=not args.all_nsw)
    print("=== NSW Department of Education JobFeed (official) ===")
    print(f"Feed as at: {feed.get('feed_as_at')}")
    print(f"Applications close: {feed.get('applications_close')}")
    print(f"Vacancies parsed: {len(feed.get('jobs') or [])}")
    for j in (feed.get("jobs") or [])[:8]:
        print(f"  - {j.get('title')[:70]} ({j.get('location')})")
    if len(feed.get("jobs") or []) > 8:
        print(f"  ... and {len(feed.get('jobs') or []) - 8} more")

    if args.seek:
        os.environ["SCRAPER_ALLOW_SEEK"] = "true"
        extra = fetch_teaching_sponsorship_jobs(sources=["seek"])
        print(f"\n=== SEEK (opt-in) matched: {len(extra)} ===")
        for j in extra[:5]:
            print(f"  - {j.get('title')}")

    print("\nFreshness: compare 'Feed as at' to today's date; role text includes contract start/end.")
    if feed.get("jobs"):
        print("\nSample job JSON:")
        print(json.dumps(feed["jobs"][0], indent=2)[:800])


if __name__ == "__main__":
    main()
