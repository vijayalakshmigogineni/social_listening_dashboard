"""
STEP 3 -- GROUP POST COLLECTION CAPABILITY TEST.

The brief is explicit: discovering a Group URL does NOT mean we can collect
posts from that Group. This script tests whether any of the four actors under
test can actually retrieve posts from a discovered public Group, and records
the honest answer either way.

    -> facebook_raw_group_posts.json

WHAT IS TESTED
    Test A: thedoor/facebook-page-scraper fed a GROUP url in `pageUrls`.
            This actor is the only one of the four with a post-retrieval role.
            Its schema says "Facebook pages"; whether it tolerates a group URL
            is an empirical question, so we ask it rather than assume.

    Test B: harvest group posts already present in the step-1 search output.
            scrapesmith search with searchType=posts returned
            /groups/<id>/permalink/<id> URLs, i.e. real posts from inside public
            groups. That is a genuine but INDIRECT path: it is keyword-driven
            discovery, not "give me the posts of group X".

No endpoint is invented and no Facebook restriction is bypassed. If both paths
fail to give targeted group-post retrieval, that is reported as a limitation.

Run:  python fb_03_group_posts.py
"""

import json
import os

from fb_common import (
    HERE, now_iso, save, load, check_budget, run_actor, run_log, run_meta,
)

# Set FB_RESUME_GROUP_RUN=<runId> to re-read an already-billed run instead of
# starting a new one. The first attempt at this test lost its poll to an Apify
# network timeout AFTER the run had been charged; resuming avoids paying twice.
RESUME_RUN_ID = os.getenv("FB_RESUME_GROUP_RUN")

GROUPS_TO_TEST = 2
POSTS_PER_GROUP = 3
RUN_CHARGE_CAP_USD = 0.15
RUN_ITEM_CAP = 8


def pick_groups():
    disc = load(HERE / "facebook_raw_groups.json")
    if not disc:
        raise SystemExit("facebook_raw_groups.json missing -- run fb_01_discovery.py first")

    def members(rec):
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

    ranked = sorted(disc["records"], key=members, reverse=True)
    return [{
        "url": r.get("url") or r.get("profileUrl"),
        "name": r.get("name"),
        "facebookId": r.get("facebookId"),
        "snippet": r.get("snippet"),
        "discovered_by_query": r.get("query"),
    } for r in ranked[:GROUPS_TO_TEST]]


def test_a_thedoor_with_group_urls(groups):
    """Feed group URLs to the page scraper and see what comes back."""
    print("\n--- TEST A: thedoor/facebook-page-scraper <- GROUP urls ---")
    run_input = {
        "pageUrls": [g["url"] for g in groups],
        "postsToScrape": POSTS_PER_GROUP,
        "includeTranscript": False,
    }
    if not RESUME_RUN_ID:
        check_budget(RUN_CHARGE_CAP_USD)
    run, items = run_actor(
        "page_thedoor", run_input,
        max_items=RUN_ITEM_CAP, max_charge_usd=RUN_CHARGE_CAP_USD,
        label=f"{len(groups)} GROUP urls x {POSTS_PER_GROUP} posts (capability probe)",
        timeout_seconds=900,
        resume_run_id=RESUME_RUN_ID,
    )

    usable = [r for r in items
              if isinstance(r, dict) and (r.get("post") or {}).get("text")]
    return {
        "test": "A - thedoor/facebook-page-scraper fed group URLs",
        "group_urls": [g["url"] for g in groups],
        "run": run_meta(run, "page_thedoor", run_input),
        "actor_log_tail": run_log(run),
        "records_returned": len(items),
        "records_with_post_text": len(usable),
        "supported": len(usable) > 0,
        "records": items,
    }


def test_b_group_posts_from_search(_groups):
    """Group posts that keyword discovery already surfaced -- $0, no new run."""
    print("\n--- TEST B: group posts already inside the step-1 search output ---")
    disc = load(HERE / "facebook_raw_search_posts.json")
    hits = [r for r in (disc or {}).get("records", [])
            if "/groups/" in str(r.get("url") or "")]
    print(f"  {len(hits)} of {len((disc or {}).get('records', []))} discovered posts "
          f"are group posts")
    for h in hits:
        print(f"    {h.get('url')}")
    return {
        "test": "B - group posts harvested from keyword search output",
        "cost_usd": 0.0,
        "note": ("These are real posts from inside public groups, obtained via "
                 "scrapesmith searchType=posts. This is keyword-driven discovery, "
                 "NOT targeted retrieval of a chosen group's feed."),
        "records_returned": len(hits),
        "supported_as_targeted_retrieval": False,
        "records": hits,
    }


def main():
    print(f"=== STEP 3: GROUP POST CAPABILITY TEST ({now_iso()}) ===")
    groups = pick_groups()
    print("Groups under test:")
    for g in groups:
        print(f"  - {g['name']}  {g['url']}  ({g['snippet']})")

    a = test_a_thedoor_with_group_urls(groups)
    b = test_b_group_posts_from_search(groups)

    targeted_supported = a["supported"]
    if targeted_supported:
        verdict = ("Group discovery works AND targeted group-post collection is "
                   "supported by thedoor/facebook-page-scraper.")
        required = None
    else:
        verdict = ("Group discovery works, but Group-post collection is not "
                   "supported by the tested actors.")
        required = {
            "capability_needed": "A dedicated Facebook GROUP feed scraper.",
            "why": ("The four actors under test cover keyword search (scrapesmith, "
                    "parseforge), page-feed retrieval (thedoor) and post comments "
                    "(apify). None of them takes a group URL and returns that "
                    "group's post feed."),
            "candidate_actor": {
                "slug": "apify/facebook-groups-scraper",
                "actor_id": "2chN8UQcH1CfxLRNE",
                "input": ["startUrls", "resultsLimit", "viewOption",
                          "onlyPostsNewerThan"],
                "status": ("NOT part of this test's actor set. Earlier work in "
                           "../facebook/facebook_actor_recommendation.json records a "
                           "verified pass on group 290657479460430 (run "
                           "lwd1sFYEcsEnAx10X, 10 posts with text/author/time/"
                           "engagement). Adding it would require approval since it "
                           "is outside the four actors named for this test."),
            },
            "access_note": ("Only PUBLIC groups are in scope. Private-group content "
                            "would require an authenticated session, which is out of "
                            "scope for public-content collection."),
        }

    payload = {
        "step": "3 - group post collection capability test",
        "produced_at": now_iso(),
        "question": ("Can any of the four actors under test retrieve posts from a "
                     "discovered public Facebook Group?"),
        "groups_tested": groups,
        "verdict": verdict,
        "targeted_group_post_retrieval_supported": targeted_supported,
        "indirect_group_posts_available_via_search": b["records_returned"] > 0,
        "required_capability_if_unsupported": required,
        "tests": [a, b],
        # Records that downstream normalization may consume. Only genuine group
        # posts land here -- never a substitute pulled from somewhere else.
        "records": (a["records"] if targeted_supported else b["records"]),
        "records_source": ("thedoor page scraper on group URLs" if targeted_supported
                           else "keyword search output (indirect)"),
    }
    save(HERE / "facebook_raw_group_posts.json", payload)

    print("\n=== VERDICT ===")
    print(f"  {verdict}")
    print(f"  targeted retrieval supported : {targeted_supported}")
    print(f"  indirect group posts found   : {b['records_returned']}")


if __name__ == "__main__":
    main()
