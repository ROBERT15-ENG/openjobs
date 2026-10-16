#!/usr/bin/env python3
"""
Live check: Australian teaching jobs mentioning visa sponsorship (SEEK AU).
Does not write to the database.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scrapers.teaching_au import fetch_teaching_sponsorship_jobs


def main():
    jobs = fetch_teaching_sponsorship_jobs(
        location="Australia",
        max_pages_per_query=1,
        require_sponsorship=True,
    )
    print(f"Matched teaching + sponsorship listings: {len(jobs)}\n")
    for j in jobs[:15]:
        print(f"- {j.get('title')} @ {j.get('company')} ({j.get('location')})")
        print(f"  {j.get('external_url')}")
        print(f"  query: {j.get('scrape_query')}")
    if len(jobs) > 15:
        print(f"... and {len(jobs) - 15} more")
    print("\nJSON sample (first job):")
    if jobs:
        print(json.dumps({k: jobs[0].get(k) for k in ('title', 'company', 'external_url', 'scrape_query')}, indent=2))


if __name__ == "__main__":
    main()
