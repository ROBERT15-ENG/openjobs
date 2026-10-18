#!/usr/bin/env python3
"""
Dry-run: all-occupation AU visa/sponsorship SEEK scan with skilled-list matching.
No database writes.

  PYTHONPATH=. python scripts/scan_au_visa_occupations.py
  PYTHONPATH=. python scripts/scan_au_visa_occupations.py --no-occupation-filter
"""

from __future__ import annotations

import argparse
import json

from scrapers.occupation_demand import occupation_list_version
from scrapers.visa_sponsorship_au import fetch_visa_sponsorship_jobs


def main():
    p = argparse.ArgumentParser(description="AU visa sponsorship + occupation list scan")
    p.add_argument(
        "--no-occupation-filter",
        action="store_true",
        help="Keep sponsorship language only; skip skilled occupation list match",
    )
    p.add_argument("--max-pages", type=int, default=1)
    args = p.parse_args()

    jobs = fetch_visa_sponsorship_jobs(
        max_pages_per_query=args.max_pages,
        require_occupation_on_demand=not args.no_occupation_filter,
    )
    print(f"Occupation list version: {occupation_list_version()}")
    print(f"Matched jobs: {len(jobs)}")
    by_occ: dict[str, int] = {}
    for j in jobs:
        title = j.get("occupation_title") or "(no occ tag)"
        by_occ[title] = by_occ.get(title, 0) + 1
    print("By skilled occupation match:")
    for name, count in sorted(by_occ.items(), key=lambda x: (-x[1], x[0]))[:20]:
        print(f"  {count:3d}  {name}")
    print("\nSample:")
    for j in jobs[:8]:
        print(
            json.dumps(
                {
                    "title": j.get("title"),
                    "company": j.get("company"),
                    "location": j.get("location"),
                    "anzsco": j.get("anzsco"),
                    "occupation": j.get("occupation_title"),
                    "lists": j.get("skilled_lists"),
                    "tags": j.get("mobility_tags"),
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
