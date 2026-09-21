"""
Actor selection study, step 5 -- assemble the recommendation.

Consolidates the sweep (111 actors), the verification runs and the discovery
bake-off into one report: which actor fills each slot of the pipeline, which
were rejected and on what evidence.

Every PASS/FAIL here is backed by a real Apify run id, not by store metadata.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

OUT = Path(__file__).resolve().parent / "facebook_actor_recommendation.json"

REC = {
    "report": "Facebook actor selection -- recommended stack",
    "produced_at": datetime.now(timezone.utc).isoformat(),
    "scope": "DATA COLLECTION FEASIBILITY ONLY. No intelligence/classification layer.",
    "method": (
        "111 Facebook actors swept from the Apify store (metadata only, $0). The "
        "shortlist was then VERIFIED with real, tiny, cost-capped runs, because store "
        "metadata cannot reveal free-plan gating or whether an actor actually returns "
        "the content it advertises. Two actors that look ideal in metadata fail in practice."
    ),

    "recommended_stack": [
        {
            "slot": "1. DISCOVERY (keyword -> posts, no manual source list)",
            "primary": "scraper_one/facebook-posts-search",
            "actor_id": "TMBawM4LZpKN15DZX",
            "price_per_result_usd": 0.00259,
            "total_runs": 2239994,
            "params": {
                "query": "str", "resultsCount": "int", "searchType": "top|latest",
                "location": "str", "startDate": "str", "endDate": "str",
            },
            "status": "VERIFIED PASS -- 5/5 real posts, no rate-limit gate in log",
            "why": (
                "Returns real post objects, reaches INSIDE public groups (a group permalink "
                "appeared in the 5-result sample), exposes startDate/endDate for the "
                "historical question, and showed no free-tier gate. Cheapest verified "
                "discovery option."
            ),
            "fields": ["postId", "url", "postText", "author", "timestamp", "reactions",
                       "reactionsCount", "commentsCount", "sharesCount", "attachments"],
            "backup": (
                "danek/facebook-search-rental -- VERIFIED PASS, 5/5 posts, $0.005/result, "
                "richer schema including associated_group_id, but roughly 2x the price"
            ),
        },
        {
            "slot": "2. GROUP POST RETRIEVAL (known public group -> posts)",
            "primary": "apify/facebook-groups-scraper",
            "actor_id": "2chN8UQcH1CfxLRNE",
            "price_per_result_usd": 0.005,
            "total_runs": 5920715,
            "params": {
                "startUrls": "array", "resultsLimit": "int",
                "viewOption": "CHRONOLOGICAL|RECENT_ACTIVITY|TOP_POSTS",
                "searchGroupKeyword": "str", "onlyPostsNewerThan": "date",
            },
            "status": "VERIFIED PASS -- 10 real posts with text, author, time, likes, comments, shares",
            "evidence_run": "lwd1sFYEcsEnAx10X (group 290657479460430)",
            "why": (
                "The highest-signal source found so far. Content included genuine denial "
                "discussion (a 64492/TON denial question, a cryoablation-via-Iovera "
                "reimbursement question) rather than the marketing noise that dominates "
                "open keyword search."
            ),
            "known_limitation": (
                "searchGroupKeyword for DISCOVERING groups returned no_items, and the "
                "actor's own field description says keyword search without login returns "
                "nothing in most cases. Use it for retrieval from known groups, not for discovery."
            ),
        },
        {
            "slot": "3. COMMENTS (post -> comment bodies)",
            "primary": "apify/facebook-comments-scraper",
            "actor_id": "us5srxAYnsrkgUv2v",
            "price_per_result_usd": 0.0025,
            "total_runs": 11122675,
            "params": {
                "startUrls": "array", "resultsLimit": "int", "includeNestedComments": "bool",
                "viewOption": "RANKED_THREADED|RECENT_ACTIVITY|RANKED_UNFILTERED",
                "onlyCommentsNewerThan": "date",
            },
            "status": "VERIFIED PASS -- 4/4 records carried comment text",
            "evidence_run": "euBgsTZJXPX7kLSSM",
            "why": (
                "Highest information density observed anywhere in this investigation. The "
                "comment thread under one denial post carried specific CPT-level "
                "reimbursement knowledge. Search results carry top_comments EMPTY in 10/10 "
                "cases, so this is a required second hop, not an optional one."
            ),
            "fields": ["id", "commentId", "text", "date", "author", "likesCount",
                       "commentUrl", "facebookId", "groupTitle", "postTitle", "feedbackId"],
        },
        {
            "slot": "4. PAGE POST RETRIEVAL (known page -> posts)",
            "primary": "apify/facebook-posts-scraper",
            "actor_id": "KoJrdxJCTtpon81KY",
            "price_per_result_usd": 0.005,
            "total_runs": 45803845,
            "params": {
                "startUrls": "array", "resultsLimit": "int", "captionText": "bool",
                "onlyPostsNewerThan": "date", "onlyPostsOlderThan": "date",
            },
            "status": "VERIFIED PASS -- 5/5 records carried post text",
            "evidence_run": "jAPjKPsE9y3Ivh2Od",
            "why": (
                "Most-used Facebook actor on Apify (45.8M runs). Has BOTH newer-than and "
                "older-than date bounds, which makes it the best candidate for the "
                "historical-window test."
            ),
            "cheaper_alternative": (
                "danek/facebook-pages-posts-ppr -- $0.00299/result, start_date + end_date, "
                "590k runs. UNVERIFIED."
            ),
        },
        {
            "slot": "5. PAGE METADATA (optional, for source profiling)",
            "primary": "apify/facebook-pages-scraper",
            "actor_id": "4Hv5RhChiaDk6iwad",
            "price_per_result_usd": 0.012,
            "total_runs": 33642593,
            "status": (
                "VERIFIED PASS -- run fwL3bPmuUMSmMu0cc returned followers, likes, "
                "categories, email, phone, website, creation_date, pageId"
            ),
            "why": (
                "Only needed to profile a discovered page before adopting it as a standing "
                "source. Most expensive per result; use sparingly."
            ),
        },
    ],

    "rejected_with_evidence": [
        {
            "actor": "parseforge/facebook-search-scraper",
            "reason": (
                "searchType='posts' returns PAGE-PROFILE records, not posts. Emits "
                "'Facebook returned no page data for this URL (not billed)' when the hit is "
                "a group. THIS IS THE ACTOR BEHIND THE ORIGINALLY REPORTED PROBLEM."
            ),
            "evidence_runs": ["K5H4Y7vDSsIawWyUf", "0nHJo0vgYtcwbYues"],
        },
        {
            "actor": "danek/facebook-search-ppr (titled 'Facebook Search Scraper')",
            "reason": (
                "Refuses to run on FREE plans. Log: 'This actor is for paid users only'. "
                "Exits with 0 results. Its correct params would be query / search_type / max_posts."
            ),
            "evidence_run": "pHTRz045M0h5ldS8J",
        },
        {
            "actor": "scrapeforge/facebook-search-posts",
            "reason": (
                "WORKS and returns real posts, but the log reveals a hard free-tier gate: "
                "'Limits: 20 results max, 1 run per 24h.' Unusable as a production discovery "
                "engine on this plan. Retained only as the Task 2 evidence run."
            ),
            "evidence_runs": ["KRgyp8AI6LTPLfGRQ", "IKTEa3sXZLsfkkaPu", "sgflssYmugE8RBs5F"],
        },
        {
            "actor": "apify/facebook-search-scraper",
            "reason": (
                "Not a post search. Its input is `categories` + `locations`; it is a "
                "business/places directory scraper. Returned 6 local business listings."
            ),
            "evidence_run": "dZMbaoJePLiwIYZ0k",
        },
        {
            "actor": "powerai/facebook-post-search-scraper",
            "reason": (
                "Rejected our input: 'Field input.maxResults must be >= 10'. Cannot do the "
                "small-sample testing this phase requires. Not re-tested."
            ),
            "evidence": "HTTP 400 invalid-input on run start",
        },
    ],

    "unverified_but_promising": [
        {
            "actor": "automation-lab/facebook-group-posts-scraper",
            "actor_id": "Qj1Ba9prQDoc2PAme",
            "price_per_result_usd": 0.00253,
            "params": ["startUrls", "searchTerms", "since", "maxItems", "maxPagesPerGroup"],
            "why_interesting": (
                "Applies KEYWORD FILTERING INSIDE specified groups -- the exact shape of this "
                "project's requirement (RCM keywords x high-signal groups). Would cut cost by "
                "filtering server-side instead of pulling everything and filtering locally."
            ),
            "caution": "only 1,335 total runs -- low maturity, unproven reliability",
        },
        {
            "actor": "curious_coder/facebook-post-scraper",
            "actor_id": "AtBpiepuIUNs2k2ku",
            "price_per_result_usd": 0.0015,
            "why_interesting": (
                "Cheapest post retrieval found, and exposes an explicit `cursors` input -- the "
                "only actor seen with a first-class pagination handle, directly relevant to "
                "the pagination task."
            ),
            "caution": (
                "takes a `cookie` input, which implies authenticated scraping for full "
                "function. Not tested; authenticated access is out of scope for "
                "public-content-only collection."
            ),
        },
    ],

    "cost_model_per_1000_items_usd": {
        "discovery_scraper_one": 2.59,
        "group_posts": 5.00,
        "comments": 2.50,
        "page_posts": 5.00,
        "page_metadata": 12.00,
    },

    "plan_constraint": (
        "Both Apify accounts are FREE tier with a $5/cycle ceiling. APIFY_TOKEN "
        "(rapturous_juncus) has ~$0.47 left; APIFY_TOKEN1 (bewildered_temperature_xvn) "
        "is the one in use. Several actors gate behaviour on plan tier, so production "
        "volume requires a paid plan and the stack should be re-validated there."
    ),
}


def main():
    OUT.write_text(json.dumps(REC, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"saved: {OUT.name}")
    for s in REC["recommended_stack"]:
        print(f"  {s['slot'][:50]:50s} -> {s['primary']}")
    print(f"  rejected: {len(REC['rejected_with_evidence'])}  "
          f"promising-unverified: {len(REC['unverified_but_promising'])}")


if __name__ == "__main__":
    main()
