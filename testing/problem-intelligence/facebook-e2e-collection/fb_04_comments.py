"""
STEP 4 -- COMMENT COLLECTION.

Collects comments for a small sample of the post URLs gathered in steps 1-3.

    -> facebook_raw_comments.json

VERIFIED LIVE SCHEMA (fb_00_inspect_schemas.py):
    startUrls              array   REQUIRED   [{"url": "..."}]
    resultsLimit           integer optional
    includeNestedComments  boolean optional   up to 3 levels, one row per reply
    viewOption             string  optional   RANKED_THREADED|RECENT_ACTIVITY|RANKED_UNFILTERED
    onlyCommentsNewerThan  string  optional

includeNestedComments is turned ON deliberately. Deep reply trees are NOT a
dashboard requirement, but this is a feasibility test: we need to MEASURE
whether depth/parent information is available at all before deciding to ignore
it. Whatever comes back is preserved in raw_data.

Post selection mixes the three origins we have -- group posts, standalone
profile posts, and a page post -- so the report can say whether comment
collection works uniformly across post types or only for some.

Run:  python fb_04_comments.py
"""

import json
import os

from fb_common import (
    HERE, now_iso, save, load, check_budget, run_actor, run_log, run_meta,
)

RESUME_RUN_ID = os.getenv("FB_RESUME_COMMENTS_RUN")

COMMENTS_PER_POST = 10
POSTS_TO_SAMPLE = 4
RUN_CHARGE_CAP_USD = 0.30
RUN_ITEM_CAP = 45


def pick_posts():
    """
    Pick post URLs to pull comments from, preferring posts that advertise a
    non-zero comment count (a post with 0 comments proves nothing either way).
    Deliberately spans group posts / profile posts / page posts.
    """
    candidates = []

    search = load(HERE / "facebook_raw_search_posts.json") or {}
    for r in search.get("records", []):
        url = r.get("url")
        if not url:
            continue
        candidates.append({
            "url": url,
            "origin": "group_post_via_search" if "/groups/" in url else "search_post",
            "advertised_comments": r.get("commentsCount") or 0,
            "post_id": r.get("postId"),
            "author_name": r.get("authorName"),
        })

    pages = load(HERE / "facebook_raw_page_posts.json") or {}
    for r in pages.get("records", []):
        post = r.get("post") or {}
        if not post.get("url"):
            continue
        candidates.append({
            "url": post["url"],
            "origin": "page_post",
            "advertised_comments": (r.get("engagement") or {}).get("comments") or 0,
            "post_id": post.get("id"),
            "author_name": (r.get("page") or {}).get("name"),
        })

    with_comments = [c for c in candidates if c["advertised_comments"] > 0]
    with_comments.sort(key=lambda c: c["advertised_comments"], reverse=True)

    # Keep the sample varied: at most two posts from any single origin.
    picked, per_origin = [], {}
    for c in with_comments:
        if per_origin.get(c["origin"], 0) >= 2:
            continue
        per_origin[c["origin"]] = per_origin.get(c["origin"], 0) + 1
        picked.append(c)
        if len(picked) >= POSTS_TO_SAMPLE:
            break
    return picked, candidates


def main():
    print(f"=== STEP 4: COMMENT COLLECTION ({now_iso()}) ===")
    picked, all_candidates = pick_posts()
    if not picked:
        raise SystemExit("No post URLs with comments found -- run steps 1-2 first")

    print("Posts sampled for comments:")
    for p in picked:
        print(f"  - [{p['origin']}] {p['advertised_comments']} comments  {p['url']}")

    run_input = {
        "startUrls": [{"url": p["url"]} for p in picked],
        "resultsLimit": COMMENTS_PER_POST,
        "includeNestedComments": True,
        "viewOption": "RANKED_UNFILTERED",
    }

    if not RESUME_RUN_ID:
        check_budget(RUN_CHARGE_CAP_USD)
    run, items = run_actor(
        "comments_apify", run_input,
        max_items=RUN_ITEM_CAP, max_charge_usd=RUN_CHARGE_CAP_USD,
        label=f"{len(picked)} posts x up to {COMMENTS_PER_POST} comments",
        timeout_seconds=900,
        resume_run_id=RESUME_RUN_ID,
    )

    # Per-post yield: which of the sampled posts actually produced comments.
    per_post = {p["url"]: {"origin": p["origin"],
                           "advertised_comments": p["advertised_comments"],
                           "comments_returned": 0} for p in picked}
    for it in items:
        if not isinstance(it, dict):
            continue
        pu = it.get("postUrl") or it.get("facebookUrl") or it.get("postId")
        for u in per_post:
            if pu and (str(pu) in u or u in str(pu)):
                per_post[u]["comments_returned"] += 1
                break

    payload = {
        "step": "4 - comment collection",
        "produced_at": now_iso(),
        "sampled_posts": picked,
        "all_post_candidates": all_candidates,
        "requested": {
            "posts": len(picked),
            "comments_per_post": COMMENTS_PER_POST,
            "include_nested_comments": True,
            "target_total": len(picked) * COMMENTS_PER_POST,
            "run_item_cap": RUN_ITEM_CAP,
        },
        "returned": {"records": len(items), "per_post": per_post},
        "run": run_meta(run, "comments_apify", run_input),
        "actor_log_tail": run_log(run),
        "records": items,
    }
    save(HERE / "facebook_raw_comments.json", payload)

    print(f"\n  requested up to {len(picked) * COMMENTS_PER_POST}, returned {len(items)}")
    for u, v in per_post.items():
        print(f"    {v['comments_returned']:>3} returned  (advertised {v['advertised_comments']:>5})  "
              f"[{v['origin']}]  {u[:70]}")
    if items:
        print(f"\n  sample keys: {sorted(items[0].keys())}")
        print(json.dumps(items[0], indent=1, ensure_ascii=False)[:1400])


if __name__ == "__main__":
    main()
