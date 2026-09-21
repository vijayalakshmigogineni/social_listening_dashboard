"""
Phase 1 "Manual Reality Check" -- 60-post Reddit collection.

Isolated from the existing source-research collectors. Reuses the APIFY_TOKEN
already present in linkedin/.env (read-only: the token is never copied,
printed, or written to disk here).

Collects the 30 most recent posts from r/CodingandBilling and r/MedicalCoding
via the Apify actor trudax/reddit-scraper-lite, and writes the untouched actor
response to data/raw/reddit_60.json.

Usage:
    python problem-intelligence/fetch_reddit_60.py
    python problem-intelligence/fetch_reddit_60.py --force   # allow overwrite
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

# Reuse the existing credential. We read the existing linkedin/.env in place;
# we do not modify it and we do not create a second token.
load_dotenv(REPO_ROOT / "linkedin" / ".env")

APIFY_TOKEN = os.getenv("APIFY_TOKEN")
if not APIFY_TOKEN:
    raise RuntimeError(
        "APIFY_TOKEN is not set. Expected it in linkedin/.env "
        "(the existing repo credential) or in the environment."
    )

ACTOR_ID = "oAuCIx3ItNrs2okjQ"  # trudax/reddit-scraper-lite

SUBREDDITS = ["CodingandBilling", "MedicalCoding"]
POSTS_PER_SUBREDDIT = 30

RAW_DIR = HERE / "data" / "raw"
OUTPUT_FILE = RAW_DIR / "reddit_60.json"

AUTH = {"Authorization": f"Bearer {APIFY_TOKEN}"}


# --------------------------------------------------------------------------
# Apify helpers
# --------------------------------------------------------------------------

def run_actor(run_input, poll_seconds=5, timeout_seconds=900):
    """Start an actor run, poll to completion, return (run_object, items)."""
    start = requests.post(
        f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs",
        headers={**AUTH, "Content-Type": "application/json"},
        data=json.dumps(run_input),
        timeout=30,
    )
    start.raise_for_status()
    run = start.json()["data"]
    run_id = run["id"]
    print(f"  run started: {run_id} (status={run['status']})")

    t0 = time.time()
    status = run["status"]
    while status not in ("SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"):
        time.sleep(poll_seconds)
        resp = requests.get(
            f"https://api.apify.com/v2/actor-runs/{run_id}",
            headers=AUTH,
            timeout=30,
        )
        resp.raise_for_status()
        run = resp.json()["data"]
        status = run["status"]
        elapsed = time.time() - t0
        print(f"    ...status={status} (elapsed {elapsed:.0f}s)")
        if elapsed > timeout_seconds:
            print(f"    polling timeout after {timeout_seconds}s; aborting wait")
            break

    dataset_id = run.get("defaultDatasetId")
    items = []
    if dataset_id:
        items_resp = requests.get(
            f"https://api.apify.com/v2/datasets/{dataset_id}/items",
            headers=AUTH,
            params={"format": "json", "clean": "true"},
            timeout=120,
        )
        items_resp.raise_for_status()
        items = items_resp.json()

    return run, items


def build_input(subreddit, limit):
    """Actor input for the N most recent posts of one subreddit."""
    return {
        "startUrls": [
            {"url": f"https://www.reddit.com/r/{subreddit}/new/", "method": "GET"}
        ],
        "skipComments": True,       # Phase 1 is posts only
        "skipUserPosts": True,
        "skipCommunity": True,
        "includeMediaLinks": True,  # gates score / numberOfComments in the output
        "searchPosts": True,
        "searchComments": False,
        "searchCommunities": False,
        "searchUsers": False,
        "sort": "new",
        "includeNSFW": True,        # do not filter: the base rate is the finding
        "maxItems": limit,
        "maxPostCount": limit,
        "maxComments": 0,
        "proxy": {"useApifyProxy": True},
    }


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
        help="allow overwriting an existing reddit_60.json",
    )
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if OUTPUT_FILE.exists() and not args.force:
        print(f"REFUSING TO OVERWRITE: {OUTPUT_FILE} already exists.")
        print("Re-run with --force if you really mean to replace it.")
        sys.exit(1)

    collected_at = datetime.now(timezone.utc).isoformat()
    per_subreddit = []

    for subreddit in SUBREDDITS:
        print(f"\n[r/{subreddit}] requesting {POSTS_PER_SUBREDDIT} most recent posts")
        run_input = build_input(subreddit, POSTS_PER_SUBREDDIT)
        run, items = run_actor(run_input)

        print(f"  final status: {run.get('status')}")
        print(f"  items returned: {len(items)}")
        print(f"  usageTotalUsd: {run.get('usageTotalUsd')}")

        per_subreddit.append(
            {
                "subreddit": subreddit,
                "requested": POSTS_PER_SUBREDDIT,
                "returned": len(items),
                "collected_at": collected_at,
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
                # The untouched actor response. Nothing is dropped or reshaped.
                "items": items,
            }
        )

    total = sum(block["returned"] for block in per_subreddit)

    payload = {
        "collection": {
            "phase": "Phase 1 - Manual Reality Check",
            "source": "reddit",
            "via": "apify:trudax/reddit-scraper-lite",
            "collected_at": collected_at,
            "subreddits": SUBREDDITS,
            "requested_per_subreddit": POSTS_PER_SUBREDDIT,
            "requested_total": POSTS_PER_SUBREDDIT * len(SUBREDDITS),
            "returned_total": total,
        },
        "runs": per_subreddit,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("COLLECTION COMPLETE")
    print("=" * 70)
    for block in per_subreddit:
        print(f"  r/{block['subreddit']}: {block['returned']} posts")
    print(f"  TOTAL: {total}")
    print(f"  saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
