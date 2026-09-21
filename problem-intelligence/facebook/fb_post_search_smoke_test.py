"""
TASK 2 -- tiny POST discovery smoke test.

  query       = "medical billing"
  search_type = "posts"
  max_posts   = 10

Objective: does the Facebook Search Scraper return ACTUAL POSTS, or does it
return groups/pages/errors (which is what the first attempt produced)?

The first attempt sent `type` and `maxItems`. Neither is in this actor's input
schema. The real parameters are `search_type` and `max_posts`.

Writes: facebook_post_search_smoke_test.json (raw, untouched actor response)
"""

import sys
import json
from collections import Counter

from fb_common import (run_actor, run_meta, classify_record, check_budget,
                       save, now_iso, budget, fetch_run)

QUERY = "medical billing"
SEARCH_TYPE = "posts"
MAX_RESULTS = 10
EST_COST = MAX_RESULTS * 0.00259 + 0.00005  # scrapeforge: $0.00259/result + start

OUT = "facebook_post_search_smoke_test.json"

FIELDS_OF_INTEREST = [
    "id", "post_id", "postId", "legacyId", "feedbackId",
    "url", "post_url", "facebookUrl", "permalink",
    "name", "title", "groupTitle", "pageName",
    "text", "message", "post_text", "snippet",
    "user", "author", "author_name", "profile",
    "time", "timestamp", "date", "created_time", "publishedAt",
    "likesCount", "reactionsCount", "topReactionsCount", "commentsCount",
    "sharesCount", "reactions", "likes",
    "facebookId", "groupId", "pageId", "inputUrl",
    "error", "errorDescription",
]


def main():
    print("=" * 78)
    print("TASK 2 -- FACEBOOK POST DISCOVERY SMOKE TEST")
    print("=" * 78)
    print(f"  actor       : scrapeforge/facebook-search-posts")
    print(f"  query       : {QUERY}")
    print(f"  search_type : {SEARCH_TYPE}")
    print(f"  max_results : {MAX_RESULTS}")
    print(f"  est. cost   : ${EST_COST:.3f}")
    run_input = {
        "query": QUERY,
        "search_type": SEARCH_TYPE,
        "max_results": MAX_RESULTS,
    }

    # --from-run <id> re-analyses a run that was already billed, so a formatting
    # fix does not cost a second run.
    reuse = None
    if "--from-run" in sys.argv:
        reuse = sys.argv[sys.argv.index("--from-run") + 1]
    if reuse:
        run, items = fetch_run(reuse)
    else:
        check_budget(EST_COST)
        run, items = run_actor("search", run_input,
                               max_items=MAX_RESULTS,
                               max_charge_usd=round(EST_COST + 0.02, 3),
                               label=f'query="{QUERY}" search_type={SEARCH_TYPE}')

    # ---- per-record inspection -------------------------------------------
    print("\n" + "=" * 78)
    print("PER-RECORD INSPECTION")
    print("=" * 78)
    kinds = Counter()
    rows = []
    for i, rec in enumerate(items):
        kind = classify_record(rec)
        kinds[kind] += 1
        present = {k: rec.get(k) for k in FIELDS_OF_INTEREST if k in rec}
        rows.append({"index": i, "classified_as": kind,
                     "all_keys": sorted(rec.keys()) if isinstance(rec, dict) else None,
                     "fields_of_interest": present})
        print(f"\n[{i}] classified_as = {kind}")
        if not isinstance(rec, dict):
            print(f"     raw: {str(rec)[:200]}")
            continue
        print(f"     keys: {sorted(rec.keys())}")
        for k, v in present.items():
            s = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
            print(f"       {k:20s}: {s[:160]}")

    # ---- field availability across all records ---------------------------
    key_counts = Counter()
    for rec in items:
        if isinstance(rec, dict):
            key_counts.update(rec.keys())

    print("\n" + "=" * 78)
    print("REQUESTED:")
    print(f"  query       = {QUERY}")
    print(f"  search type = {SEARCH_TYPE}")
    print(f"  max         = {MAX_RESULTS}")
    print("\nRETURNED:")
    print(f"  total records = {len(items)}")
    print(f"  actual posts  = {kinds.get('post', 0)}")
    print(f"  groups        = {kinds.get('group', 0)}")
    print(f"  pages         = {kinds.get('page', 0)}")
    print(f"  errors        = {kinds.get('error', 0)}")
    print(f"  unknown       = {kinds.get('unknown', 0)}")
    print("\nFIELD AVAILABILITY (field: records containing it):")
    for k, c in key_counts.most_common():
        print(f"  {k:26s} {c}/{len(items)}")
    print("=" * 78)

    used, cap, remaining = budget()
    save(OUT, {
        "task": "TASK 2 - post discovery smoke test",
        "collected_at": now_iso(),
        "requested": {"query": QUERY, "search_type": SEARCH_TYPE, "max_results": MAX_RESULTS},
        "apify": run_meta(run, "search", run_input),
        "returned": {
            "total_records": len(items),
            "actual_posts": kinds.get("post", 0),
            "groups": kinds.get("group", 0),
            "pages": kinds.get("page", 0),
            "errors": kinds.get("error", 0),
            "unknown": kinds.get("unknown", 0),
        },
        "field_availability": dict(key_counts),
        "record_inspection": rows,
        "budget_after_run": {"used_usd": used, "cap_usd": cap, "remaining_usd": remaining},
        "items_raw": items,
    })

    if kinds.get("post", 0) == 0:
        print("\nRESULT: NO ACTUAL POSTS RETURNED. Do not proceed to bulk collection.")
        return 2
    print(f"\nRESULT: {kinds['post']} actual post records returned.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
