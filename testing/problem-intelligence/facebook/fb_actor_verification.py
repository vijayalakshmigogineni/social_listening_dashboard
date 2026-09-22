"""
Actor selection study, step 2 -- VERIFY the shortlist by actually running it.

Store metadata cannot answer the two questions that matter most:
  1. does the actor refuse to run on a FREE plan?
     (danek/facebook-search-ppr looks ideal in the metadata and then exits with
      "This actor is for paid users only")
  2. does it return the CONTENT it advertises, or just metadata?
     (parseforge/facebook-search-scraper advertises searchType="posts" and
      returns page-profile records with a failed-enrichment error)

So each shortlisted actor gets one deliberately tiny run, hard-capped on both
item count and dollar charge, and is judged on what actually comes back.

Usage:
    python fb_actor_verification.py            # run the unverified ones
    python fb_actor_verification.py --dry-run  # print the plan and cost, run nothing
"""

import sys
import json
from datetime import datetime, timezone

from fb_common import (ACTORS, run_actor, run_meta, classify_record,
                       check_budget, budget, save, now_iso)

# A post that we already know exists, from the group run that succeeded earlier.
KNOWN_GROUP_POST = "https://www.facebook.com/groups/290657479460430/permalink/1619623016563863/"
KNOWN_GROUP_URL = "https://www.facebook.com/groups/290657479460430"
# A page that appeared in the Task 2 post search, so we know it is real and public.
KNOWN_PAGE_URL = "https://www.facebook.com/GoodFinancialCents"

PLAN = [
    {
        "capability": "comments",
        "actor_key": "comments",
        "why": "Task 2 showed top_comments empty in 10/10 search results. Comment "
               "bodies are where practitioner follow-up detail lives, so this is "
               "the single most important unverified capability.",
        "input": {"startUrls": [{"url": KNOWN_GROUP_POST}], "resultsLimit": 5,
                  "includeNestedComments": False, "viewOption": "RANKED_UNFILTERED"},
        "max_items": 5,
        "est_cost": 0.05,
        "pass_if": "returns >=1 record containing comment TEXT and an author",
    },
    {
        "capability": "page_posts",
        "actor_key": "posts",
        "why": "Discovery surfaced page/profile posts as well as group posts. If "
               "pages can be harvested directly, discovered pages become standing "
               "sources the same way groups do.",
        "input": {"startUrls": [{"url": KNOWN_PAGE_URL}], "resultsLimit": 5},
        "max_items": 5,
        "est_cost": 0.05,
        "pass_if": "returns >=1 record containing post text, a post URL and a timestamp",
    },
]


def judge(capability, items):
    """Did this actor deliver the content it advertises? Shape only -- no relevance call."""
    if not items:
        return "FAIL", "zero records returned"
    errs = [i for i in items if isinstance(i, dict) and (i.get("error") or i.get("errorDescription"))]
    if len(errs) == len(items):
        return "FAIL", f"every record is an error: {errs[0].get('error') or errs[0].get('errorDescription')}"

    def any_text(keys):
        return [i for i in items if isinstance(i, dict) and any(i.get(k) for k in keys)]

    if capability == "comments":
        withtext = any_text(["text", "message", "commentText", "comment"])
        if withtext:
            return "PASS", f"{len(withtext)}/{len(items)} records carry comment text"
        return "FAIL", "records returned but none carry comment text"

    if capability == "page_posts":
        withtext = any_text(["text", "message", "postText"])
        if withtext:
            return "PASS", f"{len(withtext)}/{len(items)} records carry post text"
        return "FAIL", "records returned but none carry post text"

    return "UNKNOWN", "no rule for this capability"


def main():
    dry = "--dry-run" in sys.argv
    total_est = sum(p["est_cost"] for p in PLAN)

    print("=" * 80)
    print("ACTOR VERIFICATION PLAN")
    print("=" * 80)
    for p in PLAN:
        print(f"  {p['capability']:12s} {ACTORS[p['actor_key']]['name']:34s} "
              f"<= {p['max_items']} items, est ${p['est_cost']:.3f}")
        print(f"      pass_if: {p['pass_if']}")
    print(f"  TOTAL ESTIMATE: ${total_est:.3f}")
    used, cap, remaining = budget()
    print(f"  budget: ${remaining:.3f} remaining of ${cap}")
    if dry:
        print("\n--dry-run: nothing was run.")
        return 0

    check_budget(total_est)

    results = []
    for p in PLAN:
        print("\n" + "=" * 80)
        print(f"VERIFYING: {p['capability']}  via  {ACTORS[p['actor_key']]['name']}")
        print(f"  why: {p['why']}")
        print("=" * 80)
        try:
            run, items = run_actor(p["actor_key"], p["input"],
                                   max_items=p["max_items"],
                                   max_charge_usd=round(p["est_cost"] + 0.02, 3),
                                   label=p["capability"])
        except Exception as e:  # noqa: BLE001
            print(f"  RUN FAILED: {e}")
            results.append({**{k: p[k] for k in ("capability", "why", "input", "pass_if")},
                            "actor": ACTORS[p["actor_key"]]["name"],
                            "verdict": "FAIL", "reason": f"run failed: {e}", "items": []})
            continue

        verdict, reason = judge(p["capability"], items)
        print(f"\n  VERDICT: {verdict} -- {reason}")
        for i, it in enumerate(items[:3]):
            if not isinstance(it, dict):
                continue
            print(f"   [{i}] keys={sorted(it.keys())[:12]}")
            for k in ("id", "text", "message", "url", "postUrl", "date", "time",
                      "likesCount", "commentsCount", "error", "errorDescription"):
                if it.get(k):
                    print(f"       {k}: {str(it[k])[:130]}")

        results.append({
            "capability": p["capability"], "actor": ACTORS[p["actor_key"]]["name"],
            "why": p["why"], "input": p["input"], "pass_if": p["pass_if"],
            "verdict": verdict, "reason": reason,
            "returned": len(items),
            "record_kinds": {k: sum(1 for i in items if classify_record(i) == k)
                             for k in ("post", "group", "page", "error", "unknown")},
            "fields_present": sorted({k for i in items if isinstance(i, dict) for k in i}),
            "apify": run_meta(run, p["actor_key"], p["input"]),
            "items_raw": items,
        })

    used, cap, remaining = budget()
    save("facebook_actor_verification.json", {
        "verified_at": now_iso(),
        "budget_after": {"used_usd": used, "cap_usd": cap, "remaining_usd": remaining},
        "results": results,
    })

    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    for r in results:
        print(f"  {r['verdict']:8s} {r['capability']:12s} {r['actor']:34s} {r['reason']}")
    print(f"\n  budget remaining: ${remaining:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
