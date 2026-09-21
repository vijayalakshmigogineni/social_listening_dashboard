"""
STEP 2 -- PAGE POST COLLECTION.

Takes the Page URLs discovered in step 1 and collects a small number of posts
from each with thedoor/facebook-page-scraper.

    -> facebook_raw_page_posts.json

VERIFIED LIVE SCHEMA (fb_00_inspect_schemas.py):
    pageUrls           array   REQUIRED    (NOT `startUrls`)
    postsToScrape      integer optional    per page
    includeTranscript  boolean optional
    postsNewerThan     string  optional    "7 days" or YYYY-MM-DD

Target ~10 posts total: 5 pages x 2 posts each.

Run:  python fb_02_page_posts.py   (requires fb_01_discovery.py to have run)
"""

import json

from fb_common import (
    HERE, now_iso, save, load, check_budget, run_actor, run_log, run_meta,
)

PAGES_PER_RUN = 5
POSTS_PER_PAGE = 2
RUN_CHARGE_CAP_USD = 0.25
RUN_ITEM_CAP = 12


def pick_pages():
    """
    Choose Page URLs from the discovery output.

    Selection is by expected POSTING ACTIVITY only -- pages with a follower
    count in their snippet are more likely to have public posts than a 2-follower
    listing. This is not a relevance/topic judgement; every discovered page
    stays in facebook_raw_pages.json regardless.
    """
    disc = load(HERE / "facebook_raw_pages.json")
    if not disc:
        raise SystemExit("facebook_raw_pages.json missing -- run fb_01_discovery.py first")

    def followers(rec):
        snip = (rec.get("snippet") or "")
        for tok in snip.replace("·", " ").split():
            t = tok.upper().replace(",", "")
            if t.endswith("K"):
                try:
                    return float(t[:-1]) * 1000
                except ValueError:
                    pass
            if t.isdigit():
                return float(t)
        return 0.0

    ranked = sorted(disc["records"], key=followers, reverse=True)
    picked = ranked[:PAGES_PER_RUN]
    return [{
        "url": r.get("url") or r.get("profileUrl"),
        "name": r.get("name"),
        "facebookId": r.get("facebookId"),
        "snippet": r.get("snippet"),
        "discovered_by_query": r.get("query"),
    } for r in picked]


def main():
    print(f"=== STEP 2: PAGE POST COLLECTION ({now_iso()}) ===")
    pages = pick_pages()
    print("Selected pages:")
    for p in pages:
        print(f"  - {p['name']}  {p['url']}  ({p['snippet']})")

    run_input = {
        "pageUrls": [p["url"] for p in pages],
        "postsToScrape": POSTS_PER_PAGE,
        "includeTranscript": False,
    }

    check_budget(RUN_CHARGE_CAP_USD)
    run, items = run_actor(
        "page_thedoor", run_input,
        max_items=RUN_ITEM_CAP, max_charge_usd=RUN_CHARGE_CAP_USD,
        label=f"{len(pages)} pages x {POSTS_PER_PAGE} posts",
        timeout_seconds=900,
    )

    payload = {
        "step": "2 - page post collection",
        "produced_at": now_iso(),
        "actor_input_schema_note": (
            "thedoor/facebook-page-scraper takes `pageUrls`, not `startUrls`. "
            "Confirmed against the live build in facebook_actor_live_schemas.json."
        ),
        "selected_pages": pages,
        "requested": {
            "pages": len(pages),
            "posts_per_page": POSTS_PER_PAGE,
            "target_total_posts": len(pages) * POSTS_PER_PAGE,
            "run_item_cap": RUN_ITEM_CAP,
        },
        "returned": {"records": len(items)},
        "run": run_meta(run, "page_thedoor", run_input),
        "actor_log_tail": run_log(run),
        "records": items,
    }
    save(HERE / "facebook_raw_page_posts.json", payload)

    print(f"\n  requested ~{len(pages) * POSTS_PER_PAGE} posts, returned {len(items)} records")
    if items:
        print(f"  sample keys: {sorted(items[0].keys())}")
        print(json.dumps(items[0], indent=1, ensure_ascii=False)[:1200])


if __name__ == "__main__":
    main()
