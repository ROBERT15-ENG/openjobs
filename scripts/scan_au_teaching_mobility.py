#!/usr/bin/env python3
"""
Scan Australia for current teaching roles with visa/sponsorship-style language.

Sources (default): NSW DET JobFeed. Optional: SEEK (--national) for other states/employers.
"""
import argparse
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scrapers.mobility_language import (
    mobility_snippet,
    mobility_tags_for_job,
)
from scrapers.sources.nsw_jobfeed import search_nsw_jobfeed
from scrapers.teaching_filters import is_teaching_role
from scrapers.teaching_au import fetch_teaching_sponsorship_jobs


def _state_from_location(loc: str) -> str:
    loc = loc or ""
    for code in ("NSW", "VIC", "QLD", "WA", "SA", "TAS", "NT", "ACT"):
        if code in loc.upper():
            return code
    if "NSW" in loc or "New South Wales" in loc:
        return "NSW"
    return "AU/other"


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--national",
        action="store_true",
        help="Include SEEK AU (set SCRAPER_ALLOW_SEEK) for non-NSW employers",
    )
    args = p.parse_args()

    all_jobs = []
    tag_counter: Counter = Counter()
    state_counter: Counter = Counter()
    visa_explicit = []
    incentive_only = []

    feed = search_nsw_jobfeed(require_mobility_or_sponsor=True)
    print("=== NSW Department of Education JobFeed ===")
    print(f"Feed as at: {feed.get('feed_as_at')}")
    print(f"Applications close: {feed.get('applications_close')}")
    all_jobs.extend(feed.get("jobs") or [])

    if args.national:
        os.environ["SCRAPER_ALLOW_SEEK"] = "true"
        seek_jobs = fetch_teaching_sponsorship_jobs(
            sources=["seek"],
            require_sponsorship=True,
            australia_only=True,
        )
        print(f"\n=== SEEK Australia (teaching + mobility language) ===")
        print(f"Matched: {len(seek_jobs)}")
        all_jobs.extend(seek_jobs)

    for job in all_jobs:
        tags = mobility_tags_for_job(job)
        if not tags:
            tags = job.get("mobility_tags") or []
        for t in tags:
            tag_counter[t] += 1
        st = _state_from_location(job.get("location", ""))
        state_counter[st] += 1
        blob = (job.get("description") or "") + " " + (job.get("title") or "")
        if "visa_or_sponsor" in tags:
            visa_explicit.append(job)
        elif tags:
            incentive_only.append(job)

    print("\n=== Summary: teaching-related mobility language (current sources) ===")
    print(f"Total roles with mobility language: {len(all_jobs)}")
    print(f"  Explicit visa/sponsor-style wording: {len(visa_explicit)}")
    print(f"  Relocation/incentive/regional only: {len(incentive_only)}")
    print(f"By tag: {dict(tag_counter)}")
    print(f"By state/region: {dict(state_counter)}")

    print("\n--- Examples: explicit visa/sponsor wording ---")
    for j in visa_explicit[:8]:
        snip = mobility_snippet(j.get("description") or j.get("title") or "")
        print(f"  • {j.get('title')[:65]} | {j.get('location')}")
        if snip:
            print(f"      …{snip}…")

    print("\n--- Examples: relocation / recruitment incentives (common in public schools) ---")
    for j in incentive_only[:6]:
        snip = mobility_snippet(j.get("description") or "")
        print(f"  • {j.get('title')[:65]} | {j.get('location')}")
        if snip:
            print(f"      …{snip}…")

    if not args.national:
        print(
            "\nNote: NSW JobFeed covers NSW public schools only. "
            "Run with --national to include SEEK for VIC/QLD/WA private & sector employers."
        )


if __name__ == "__main__":
    main()
