"""
Top-up collector for Phase 1.

The first pass came back short / stale for some subreddits (the actor's scroll
can stop early or serve a cached listing page). This runs additional Apify
actor runs, appends them to data/raw/reddit_60.json as extra run blocks, and
never discards anything already collected.

Selection of the final 30-per-subreddit happens downstream in
build_dataset.py, which dedups on post id and keeps the newest by createdAt.

Usage:
    python problem-intelligence/topup_reddit.py CodingandBilling 60
    python problem-intelligence/topup_reddit.py MedicalCoding 60
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

from fetch_reddit_60 import run_actor, ACTOR_ID, OUTPUT_FILE


def build_topup_input(subreddit, limit):
    """Same shape as the first pass, but with a longer scroll budget."""
    return {
        "startUrls": [
            {"url": f"https://www.reddit.com/r/{subreddit}/new/", "method": "GET"}
        ],
        "skipComments": True,
        "skipUserPosts": True,
        "skipCommunity": True,
        "includeMediaLinks": True,
        "searchPosts": True,
        "searchComments": False,
        "searchCommunities": False,
        "searchUsers": False,
        "sort": "new",
        "includeNSFW": True,
        "maxItems": limit,
        "maxPostCount": limit,
        "maxComments": 0,
        "scrollTimeout": 120,     # first pass stopped early at the 40s default
        "navigationTimeout": 60,  # schema maximum
        "proxy": {"useApifyProxy": True},
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    subreddit = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 60

    if not OUTPUT_FILE.exists():
        print(f"missing {OUTPUT_FILE}; run fetch_reddit_60.py first")
        sys.exit(1)

    payload = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))

    print(f"\n[r/{subreddit}] top-up run, maxItems={limit}")
    run_input = build_topup_input(subreddit, limit)
    run, items = run_actor(run_input)

    print(f"  final status: {run.get('status')}")
    print(f"  items returned: {len(items)}")
    print(f"  usageTotalUsd: {run.get('usageTotalUsd')}")

    payload["runs"].append(
        {
            "subreddit": subreddit,
            "requested": limit,
            "returned": len(items),
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "topup": True,
            "apify": {
                "actor_id": ACTOR_ID,
                "actor_name": "trudax/reddit-scraper-lite",
                "run_id": run.get("id"),
                "status": run.get("status"),
                "started_at": run.get("startedAt"),
                "finished_at": run.get("finishedAt"),
                "dataset_id": run.get("defaultDatasetId"),
                "usage_total_usd": run.get("usageTotalUsd"),
                "run_input": run_input,
            },
            "items": items,
        }
    )

    payload["collection"]["returned_total"] = sum(
        b["returned"] for b in payload["runs"]
    )

    OUTPUT_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Report unique-post coverage for this subreddit across all runs so far.
    seen = {}
    for block in payload["runs"]:
        if block["subreddit"] != subreddit:
            continue
        for item in block["items"]:
            seen[item.get("id")] = item.get("createdAt")

    dates = sorted(v for v in seen.values() if v)
    print(f"\n  unique posts for r/{subreddit} across all runs: {len(seen)}")
    if dates:
        print(f"  date range: {dates[0]} .. {dates[-1]}")
    print(f"  appended to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
