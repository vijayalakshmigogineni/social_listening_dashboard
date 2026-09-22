"""
Build the Phase 1 working dataset from the raw Apify capture.

Reads data/raw/reddit_60.json (never modified), dedups on post id, keeps the
30 newest posts per subreddit by createdAt, and writes a flat normalised file
for labelling. The raw capture remains the source of truth; this file carries
no labels.

Output: data/reddit_60_posts.json
"""

import json
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent
RAW_FILE = HERE / "data" / "raw" / "reddit_60.json"
OUT_FILE = HERE / "data" / "reddit_60_posts.json"

PER_SUBREDDIT = 30


def main():
    raw = json.loads(RAW_FILE.read_text(encoding="utf-8"))

    # Dedup across all runs, keyed by post id.
    by_sub = defaultdict(dict)
    collected_at = {}
    for block in raw["runs"]:
        sub = block["subreddit"]
        for item in block["items"]:
            if item.get("dataType") != "post":
                continue
            pid = item.get("id")
            if pid is None:
                continue
            by_sub[sub][pid] = item
            collected_at.setdefault(pid, block["collected_at"])

    posts = []
    stats = {}
    for sub, items in by_sub.items():
        ordered = sorted(
            items.values(),
            key=lambda x: x.get("createdAt") or "",
            reverse=True,
        )
        kept = ordered[:PER_SUBREDDIT]
        stats[sub] = {
            "unique_collected": len(ordered),
            "kept": len(kept),
            "kept_date_range": [
                kept[-1].get("createdAt"),
                kept[0].get("createdAt"),
            ]
            if kept
            else None,
        }
        for item in kept:
            posts.append(
                {
                    "source": "reddit",
                    "community": item.get("parsedCommunityName")
                    or item.get("communityName"),
                    "post_id": item.get("id"),
                    "url": item.get("url"),
                    "permalink": item.get("link") or item.get("url"),
                    "title": item.get("title"),
                    "body": item.get("body"),
                    "author": item.get("username"),
                    "created_at": item.get("createdAt"),
                    "score": item.get("upVotes"),
                    "upvote_ratio": item.get("upVoteRatio"),
                    "num_comments": item.get("numberOfComments"),
                    "collected_at": collected_at.get(item.get("id")),
                }
            )

    posts.sort(key=lambda p: (p["community"] or "", p["created_at"] or ""), reverse=True)

    payload = {
        "meta": {
            "phase": "Phase 1 - Manual Reality Check",
            "source": "reddit",
            "via": "apify:trudax/reddit-scraper-lite",
            "raw_file": "data/raw/reddit_60.json",
            "per_subreddit_target": PER_SUBREDDIT,
            "total_posts": len(posts),
            "per_subreddit": stats,
        },
        "posts": posts,
    }

    OUT_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"total posts: {len(posts)}")
    for sub, s in stats.items():
        print(f"  r/{sub}: kept {s['kept']} of {s['unique_collected']} unique")
        print(f"      range {s['kept_date_range'][0]} .. {s['kept_date_range'][1]}")

    ids = [p["post_id"] for p in posts]
    print(f"unique ids: {len(set(ids))} / {len(ids)}")
    print(f"missing url: {sum(1 for p in posts if not p['url'])}")
    print(f"empty body: {sum(1 for p in posts if not (p['body'] or '').strip())}")
    print(f"saved: {OUT_FILE}")


if __name__ == "__main__":
    main()
