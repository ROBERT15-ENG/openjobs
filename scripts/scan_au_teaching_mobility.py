#!/usr/bin/env python3
"""
Scan all Australian states/territories for teaching roles with mobility language.

Combines NSW DET JobFeed + per-state SEEK queries (education / visa / relocation wording).
"""
import argparse
import json
import sys
from collections import Counter

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scrapers.au_states import AU_STATES, STATE_CODES
from scrapers.mobility_language import mobility_snippet, mobility_tags_for_job
from scrapers.teaching_all_states import fetch_teaching_mobility_all_states


def main():
    p = argparse.ArgumentParser(description="All-states teaching mobility scan")
    p.add_argument(
        "--nsw-only",
        action="store_true",
        help="Only NSW JobFeed (no per-state SEEK)",
    )
    p.add_argument("--json", action="store_true", help="Print JSON summary")
    args = p.parse_args()

    result = fetch_teaching_mobility_all_states(
        include_nsw_jobfeed=True,
        include_seek_by_state=not args.nsw_only,
        require_mobility_language=True,
        max_pages_per_query=1,
    )
    jobs = result["jobs"]
    meta = result["meta"]
    by_state = result["by_state"]

    tag_counter: Counter = Counter()
    visa_explicit = []
    incentive_only = []

    for job in jobs:
        tags = job.get("mobility_tags") or mobility_tags_for_job(job)
        for t in tags:
            tag_counter[t] += 1
        if "visa_or_sponsor" in tags:
            visa_explicit.append(job)
        elif tags:
            incentive_only.append(job)

    if args.json:
        summary = {
            "meta": meta,
            "total": len(jobs),
            "visa_explicit": len(visa_explicit),
            "incentive_only": len(incentive_only),
            "by_state": {k: len(v) for k, v in sorted(by_state.items())},
            "tags": dict(tag_counter),
        }
        print(json.dumps(summary, indent=2))
        return

    print("=== Australia — all states & territories ===")
    if meta.get("nsw_feed_as_at"):
        print(f"NSW JobFeed as at: {meta['nsw_feed_as_at']}")
        print(f"NSW applications close: {meta.get('nsw_applications_close')}")
    if not args.nsw_only:
        print(f"Market search: {meta.get('seek_states_queried', 0)} states/territories via SEEK")

    print(f"\nTotal roles (teaching + mobility language): {len(jobs)}")
    print(f"  Explicit visa/sponsor wording: {len(visa_explicit)}")
    print(f"  Relocation/incentives (typical public sector): {len(incentive_only)}")

    print("\nBy state/territory:")
    for code, _, name in AU_STATES:
        n = len(by_state.get(code, []))
        bar = "·" * min(n, 40)
        print(f"  {code:3} {name:28} {n:4}  {bar}")
    other = len(by_state.get("AU", []))
    if other:
        print(f"  AU  (unassigned)              {other:4}")

    print(f"\nBy language tag: {dict(tag_counter)}")

    print("\n--- Visa / sponsorship wording (any state) ---")
    for j in visa_explicit[:12]:
        snip = mobility_snippet(j.get("description") or j.get("title") or "")
        print(f"  [{j.get('state_code')}] {j.get('title')[:60]} | {j.get('location')}")
        if snip:
            print(f"       …{snip}…")

    print("\n--- Relocation / incentives (sample) ---")
    for j in incentive_only[:6]:
        if j.get("state_code") != "NSW" and j.get("source") != "nsw_jobfeed":
            continue
        snip = mobility_snippet(j.get("description") or "")
        print(f"  [NSW] {j.get('title')[:60]}")
        if snip:
            print(f"       …{snip}…")

    empty_states = [code for code, _, name in AU_STATES if not by_state.get(code)]
    if empty_states and not args.nsw_only:
        print(
            f"\nNo mobility-keyword matches this run in: {', '.join(empty_states)}. "
            "Listings may still exist on state DET portals or under different wording."
        )


if __name__ == "__main__":
    main()
