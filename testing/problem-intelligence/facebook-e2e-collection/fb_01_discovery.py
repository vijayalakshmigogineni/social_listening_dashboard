"""
STEP 1 -- DISCOVERY.

Keyword search on Facebook for three result types, ~10 records each:

    searchType = posts   -> facebook_raw_search_posts.json
    searchType = pages   -> facebook_raw_pages.json
    searchType = groups  -> facebook_raw_groups.json

Primary actor:  scrapesmith/facebook-search-scraper
    VERIFIED LIVE SCHEMA (fb_00_inspect_schemas.py):
        queries             array   REQUIRED     (NOT `query`, NOT a single string)
        searchType          string  optional     enum: pages|posts|groups|events|people|all
        maxResultsPerQuery  integer optional
    Pricing: $0.005 actor start + $0.0005 per dataset item.

Comparison actor: parseforge/facebook-search-scraper
    VERIFIED LIVE SCHEMA:
        queries    array   REQUIRED
        searchType string  optional  enum: pages|groups|posts|videos
        maxItems   integer optional
    One small posts run only, to record how it compares. Earlier work in
    ../facebook/facebook_actor_recommendation.json found this actor returns
    PAGE-PROFILE records when asked for posts; this run re-tests that claim
    against the current build rather than inheriting the conclusion.

NO classification happens here. Promotional and educational hits are kept.
The only filtering is structural: obvious non-content rows (search_ads and
empty/error rows) are dropped, and records are deduplicated on the strongest
stable identifier available.

Run:  python fb_01_discovery.py
"""

import json

from fb_common import (
    HERE, SEARCH_QUERIES, now_iso, save, check_budget, run_actor, run_log, run_meta,
)

# 10 queries x 2 results each, hard-capped at 12 rows per run. That lands near
# the ~10 records the test asks for while spreading the sample across every
# query instead of letting one noisy keyword fill the whole slot.
MAX_PER_QUERY = 2
RUN_ITEM_CAP = 12
RUN_CHARGE_CAP_USD = 0.05

SEARCH_TYPES = {
    "posts":  HERE / "facebook_raw_search_posts.json",
    "pages":  HERE / "facebook_raw_pages.json",
    "groups": HERE / "facebook_raw_groups.json",
}

# Candidate stable-ID keys, strongest first. Facebook/Apify actors are not
# consistent about which one they emit, so we probe in priority order and fall
# back to the canonical URL, exactly as the brief requires.
ID_KEYS = [
    "postId", "post_id", "pageId", "page_id", "groupId", "group_id",
    "id", "facebookId", "fbid", "topLevelUrl",
]
URL_KEYS = ["url", "facebookUrl", "pageUrl", "postUrl", "groupUrl", "link", "permalink"]


def first_present(rec, keys):
    for k in keys:
        v = rec.get(k)
        if v not in (None, "", [], {}):
            return k, v
    return None, None


def is_non_content(rec):
    """
    Structural junk only -- never a relevance judgement.
    Drops search_ads rows, error rows, and rows with no identity at all.
    """
    if not isinstance(rec, dict):
        return True, "not-a-dict"
    blob = json.dumps(rec, ensure_ascii=False).lower()
    if rec.get("search_ads") or '"search_ads"' in blob[:400]:
        return True, "search_ads"
    if rec.get("error") or rec.get("errorDescription"):
        return True, f"error:{rec.get('error') or rec.get('errorDescription')}"
    _, rid = first_present(rec, ID_KEYS)
    _, rurl = first_present(rec, URL_KEYS)
    if rid is None and rurl is None:
        return True, "no-id-and-no-url"
    return False, None


def dedupe(records):
    """Return (kept, duplicate_log, id_source_counts)."""
    seen = {}
    kept, dupes, id_sources = [], [], {}
    for rec in records:
        k, v = first_present(rec, ID_KEYS)
        if v is None:
            k, v = first_present(rec, URL_KEYS)
            k = f"URL_FALLBACK:{k}"
        key = f"{k}={v}"
        id_sources[k] = id_sources.get(k, 0) + 1
        if key in seen:
            dupes.append({"duplicate_key": key, "first_index": seen[key]})
            continue
        seen[key] = len(kept)
        kept.append(rec)
    return kept, dupes, id_sources


def discover(search_type, out_path):
    print(f"\n=== DISCOVERY: searchType={search_type} ===")
    run_input = {
        "queries": SEARCH_QUERIES,
        "searchType": search_type,
        "maxResultsPerQuery": MAX_PER_QUERY,
    }
    check_budget(RUN_CHARGE_CAP_USD)
    run, items = run_actor(
        "search_scrapesmith", run_input,
        max_items=RUN_ITEM_CAP, max_charge_usd=RUN_CHARGE_CAP_USD,
        label=f"searchType={search_type}, {len(SEARCH_QUERIES)} queries x {MAX_PER_QUERY}",
    )

    dropped = []
    clean = []
    for rec in items:
        bad, why = is_non_content(rec)
        (dropped if bad else clean).append({"reason": why, "record": rec} if bad else rec)

    kept, dupes, id_sources = dedupe(clean)

    payload = {
        "step": f"1 - discovery ({search_type})",
        "produced_at": now_iso(),
        "search_queries": SEARCH_QUERIES,
        "requested": {
            "max_results_per_query": MAX_PER_QUERY,
            "run_item_cap": RUN_ITEM_CAP,
            "target_records": 10,
        },
        "returned": {
            "raw_from_actor": len(items),
            "dropped_non_content": len(dropped),
            "duplicates_removed": len(dupes),
            "kept": len(kept),
        },
        "id_key_used_counts": id_sources,
        "duplicates": dupes,
        "dropped_records": dropped,
        "run": run_meta(run, "search_scrapesmith", run_input),
        "actor_log_tail": run_log(run),
        "records": kept,
    }
    save(out_path, payload)
    print(f"  -> raw={len(items)} dropped={len(dropped)} dupes={len(dupes)} kept={len(kept)}")
    if kept:
        print(f"  sample keys: {sorted(kept[0].keys())}")
    return payload


def parseforge_comparison():
    """One small posts run against the second search actor, for the record."""
    print("\n=== DISCOVERY COMPARISON: parseforge/facebook-search-scraper ===")
    run_input = {
        "queries": SEARCH_QUERIES[:3],
        "searchType": "posts",
        "maxItems": 10,
    }
    check_budget(RUN_CHARGE_CAP_USD)
    run, items = run_actor(
        "search_parseforge", run_input,
        max_items=10, max_charge_usd=RUN_CHARGE_CAP_USD,
        label="searchType=posts comparison run",
    )
    payload = {
        "step": "1b - discovery comparison actor",
        "produced_at": now_iso(),
        "purpose": ("Compare the second named search actor against scrapesmith. "
                    "Not used as a data source for normalization unless it "
                    "outperforms the primary."),
        "returned": len(items),
        "run": run_meta(run, "search_parseforge", run_input),
        "actor_log_tail": run_log(run),
        "records": items,
    }
    save(HERE / "facebook_raw_search_parseforge_comparison.json", payload)
    if items:
        print(f"  sample keys: {sorted(items[0].keys())}")
    return payload


def main():
    print(f"=== STEP 1: FACEBOOK DISCOVERY ({now_iso()}) ===")
    summary = {}
    for st, path in SEARCH_TYPES.items():
        summary[st] = discover(st, path)["returned"]
    try:
        pf = parseforge_comparison()
        summary["parseforge_posts_comparison"] = {"returned": pf["returned"]}
    except Exception as e:
        print(f"  parseforge comparison failed: {e}")
        summary["parseforge_posts_comparison"] = {"error": str(e)}

    print("\n=== STEP 1 SUMMARY ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
