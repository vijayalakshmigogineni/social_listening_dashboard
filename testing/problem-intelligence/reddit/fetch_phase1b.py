"""
Phase 1b -- extend the Phase 1 reality check to five further communities.

Communities were chosen from measured activity (data/raw/community_probe.json),
not guessed, and then filtered to PRACTICE-SIDE voice only.

An earlier version of this file also collected r/ChronicPain, r/PainManagement
and r/HealthInsurance. Those were dropped before any data was kept: they are
patient communities, and they would have produced "my insurance denied my
injection" rather than "our billing team is fighting UHC denials". Patient
complaints are not RCM operational problem evidence, and mixing them in would
have depressed every base rate for a reason that has nothing to do with the
source's value.

The question this collection answers: do clinician / practice-operator
communities carry RCM operational problem evidence the way r/CodingandBilling
and r/MedicalCoding do, and at what rate?

Same actor, same credential, same unfiltered 30-most-recent method as Phase 1 --
unfiltered is the point, because a filtered sample cannot produce a base rate.
Raw responses are kept whole in data/raw/reddit_phase1b.json.

Usage:
    python problem-intelligence/fetch_phase1b.py
    python problem-intelligence/fetch_phase1b.py --force
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

from fetch_reddit_60 import run_actor, ACTOR_ID

HERE = Path(__file__).resolve().parent
OUTPUT_FILE = HERE / "data" / "raw" / "reddit_phase1b.json"

POSTS_PER_SUBREDDIT = 30

# (subreddit, weekly_contributions_at_probe, why it is in the set)
SUBREDDITS = [
    # highest-activity healthcare community in the probe whose members also run
    # the practice: mental health clinicians dealing with panels, credentialing,
    # claim denials and billing services themselves
    ("therapists", 8144, "clinician / private practice owner"),
    # roadmap-named; physicians, including practice owners. Prior-auth burden is
    # a known recurring genre here
    ("medicine", 2936, "clinician"),
    # roadmap-named; family physicians, a high share of whom own or run a practice
    ("FamilyMedicine", 1406, "clinician / practice owner"),
    # front-line staff who actually execute prior auths and referrals -- the
    # operational voice closest to the work itself
    ("MedicalAssistant", 679, "practice staff"),
    # small but precisely on target: practice owners talking about running a
    # practice. Low volume is expected and is itself a finding
    ("PrivatePractice", 82, "practice owner"),
]

# Ask for more than 30: Phase 1 showed the actor's scroll stops early, and
# over-requesting once is cheaper than a second top-up run per community.
REQUEST_LIMIT = 60


def build_input(subreddit, limit):
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
        "scrollTimeout": 120,
        "navigationTimeout": 60,
        "proxy": {"useApifyProxy": True},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT_FILE.exists() and not args.force:
        print(f"REFUSING TO OVERWRITE: {OUTPUT_FILE} exists. Use --force.")
        sys.exit(1)

    collected_at = datetime.now(timezone.utc).isoformat()
    blocks = []

    for subreddit, contrib, voice in SUBREDDITS:
        print(f"\n[r/{subreddit}] requesting up to {REQUEST_LIMIT} (target {POSTS_PER_SUBREDDIT})")
        run_input = build_input(subreddit, REQUEST_LIMIT)
        run, items = run_actor(run_input)

        posts = [i for i in items if i.get("dataType") == "post"]
        uniq = {i.get("id") for i in posts}
        dates = sorted(i.get("createdAt") or "" for i in posts)

        print(f"  status={run.get('status')} items={len(items)} posts={len(posts)} unique={len(uniq)}")
        if dates:
            print(f"  range {dates[0][:10]} .. {dates[-1][:10]}")
        print(f"  cost={run.get('usageTotalUsd')}")

        blocks.append(
            {
                "subreddit": subreddit,
                "weekly_contributions_at_probe": contrib,
                "expected_voice": voice,
                "requested": REQUEST_LIMIT,
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
                "items": items,
            }
        )

    payload = {
        "collection": {
            "phase": "Phase 1b - community expansion",
            "source": "reddit",
            "via": "apify:trudax/reddit-scraper-lite",
            "collected_at": collected_at,
            "selection_basis": "data/raw/community_probe.json weekly contributions",
            "subreddits": [s for s, _, _ in SUBREDDITS],
            "target_per_subreddit": POSTS_PER_SUBREDDIT,
            "returned_total": sum(b["returned"] for b in blocks),
        },
        "runs": blocks,
    }

    OUTPUT_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\n" + "=" * 70)
    print("PHASE 1B COLLECTION COMPLETE")
    print("=" * 70)
    for b in blocks:
        print(f"  r/{b['subreddit']:18s} {b['returned']:3d} items")
    print(f"  saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
