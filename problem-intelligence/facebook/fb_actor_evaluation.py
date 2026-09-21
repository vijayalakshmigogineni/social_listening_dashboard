"""
Actor selection study -- which Apify actors should this project actually use?

Step 1 (this file): free metadata sweep of every Facebook-related actor in the
Apify store. Pulls pricing, popularity, maintenance recency and the real input
schema of the latest build.

Nothing is run here, so this step costs $0. Actor *capability* is judged in
fb_actor_verification.py, because store metadata cannot tell you whether an
actor refuses to run on a FREE plan -- danek/facebook-search-ppr looked perfect
here and then exited with "This actor is for paid users only".
"""

import json
from datetime import datetime, timezone

import requests

from fb_common import AUTH, API, save

SEARCH_TERMS = ["facebook", "facebook posts", "facebook groups", "facebook comments",
                "facebook search", "facebook pages"]

# What this project needs, in the order the pipeline needs it.
CAPABILITIES = {
    "discovery":  "find RCM content by KEYWORD, with no hand-maintained source list",
    "group_posts": "retrieve public posts from a known group URL",
    "page_posts":  "retrieve public posts from a known page/profile URL",
    "comments":    "retrieve comment bodies under a post",
    "page_meta":   "retrieve page profile metadata (followers, category, about)",
}


def fetch_all_actors():
    seen = {}
    for term in SEARCH_TERMS:
        r = requests.get(f"{API}/store", headers=AUTH,
                         params={"search": term, "limit": 100}, timeout=60)
        r.raise_for_status()
        for a in r.json()["data"]["items"]:
            full = f"{a.get('username')}/{a.get('name')}"
            if "facebook" in full.lower() or "facebook" in (a.get("title") or "").lower() or "/fb-" in full.lower():
                seen[full] = a
    return seen


def actor_detail(full):
    aid = full.replace("/", "~")
    act = requests.get(f"{API}/acts/{aid}", headers=AUTH, timeout=60).json()["data"]
    infos = act.get("pricingInfos") or []
    cur = infos[-1] if infos else {}

    price_per_result = None
    start_fee = None
    if cur.get("pricingModel") == "PAY_PER_EVENT":
        for ev, d in (cur.get("pricingPerEvent", {}).get("actorChargeEvents") or {}).items():
            tiered = (d.get("eventTieredPricingUsd") or {}).get("FREE", {}).get("tieredEventPriceUsd")
            flat = d.get("eventPriceUsd")
            price = tiered if tiered is not None else flat
            if d.get("isPrimaryEvent") or "item" in ev or "post" in ev or "result" in ev:
                price_per_result = price
            if "start" in ev or ev == "init":
                start_fee = price
    elif cur.get("pricingModel") == "PRICE_PER_DATASET_ITEM":
        price_per_result = cur.get("pricePerUnitUsd")

    schema = {}
    try:
        bid = (act.get("taggedBuilds") or {}).get("latest", {}).get("buildId")
        build = requests.get(f"{API}/actor-builds/{bid}", headers=AUTH, timeout=60).json()["data"]
        schema = json.loads(build.get("inputSchema") or "{}")
        built_at = build.get("finishedAt")
    except Exception:  # noqa: BLE001
        built_at = None

    props = schema.get("properties") or {}
    search_type_enum = None
    for k in ("search_type", "searchType", "type", "searchQueries"):
        if k in props and props[k].get("enum"):
            search_type_enum = {k: props[k]["enum"]}

    return {
        "full_name": full,
        "actor_id": act.get("id"),
        "title": act.get("title"),
        "total_runs": (act.get("stats") or {}).get("totalRuns"),
        "deprecated": act.get("isDeprecated"),
        "pricing_model": cur.get("pricingModel"),
        "flat_monthly_usd": cur.get("pricePerUnitUsd") if cur.get("pricingModel") == "FLAT_PRICE_PER_MONTH" else None,
        "price_per_result_usd": price_per_result,
        "actor_start_usd": start_fee,
        "latest_build_finished_at": built_at,
        "input_fields": sorted(props.keys()),
        "required": schema.get("required"),
        "search_type_enum": search_type_enum,
        "has_date_filter": [k for k in props if any(
            t in k.lower() for t in ("date", "newerthan", "olderthan", "since", "until"))],
    }


def main():
    print("Sweeping the Apify store for Facebook actors (free, no runs)...")
    actors = fetch_all_actors()
    print(f"  found {len(actors)} facebook-related actors\n")

    rows = []
    for full in sorted(actors):
        try:
            rows.append(actor_detail(full))
        except Exception as e:  # noqa: BLE001
            print(f"  {full}: detail failed ({e})")

    rows.sort(key=lambda r: -(r.get("total_runs") or 0))

    print("=" * 118)
    print(f"{'actor':46s} {'runs':>10s} {'model':22s} {'$/result':>9s} {'dates':>5s}")
    print("=" * 118)
    for r in rows:
        model = r["pricing_model"] or "?"
        if model == "FLAT_PRICE_PER_MONTH":
            model = f"RENTAL ${r['flat_monthly_usd']}/mo"
        ppr = r["price_per_result_usd"]
        print(f"{r['full_name'][:46]:46s} {r['total_runs'] or 0:>10,} {model[:22]:22s} "
              f"{('$'+format(ppr,'.5f')) if ppr else '-':>9s} {'yes' if r['has_date_filter'] else '-':>5s}")

    save("facebook_actor_evaluation.json", {
        "swept_at": datetime.now(timezone.utc).isoformat(),
        "capabilities_needed": CAPABILITIES,
        "note": ("Store metadata only. It does NOT reveal free-plan gating -- "
                 "danek/facebook-search-ppr looks fine here but refuses to run."),
        "actors": rows,
    })


if __name__ == "__main__":
    main()
