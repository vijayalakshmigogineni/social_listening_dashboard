"""
Actor selection study, step 4 -- DISCOVERY BAKE-OFF.

The discovery slot is the hard one. scrapeforge/facebook-search-posts returns
real posts but its run log revealed a hard free-tier gate:
    "[free-tier] Free user detected. Limits: 20 results max, 1 run per 24h."
which makes it unusable as a production discovery engine on this plan.

So the candidates run head to head: same query, same limit, judged on
  - does it run at all on a FREE plan (the danek failure mode)
  - does it return POSTS or just page metadata (the parseforge failure mode)
  - is there a rate-limit / quota warning in its log
  - cost, and which fields come back

Each candidate is capped at 5 results.
"""

import os
import sys
import json
import time
from collections import Counter
from datetime import datetime, timezone

import requests

from fb_common import AUTH, API, classify_record, check_budget, budget, save, now_iso

QUERY = "medical billing"
LIMIT = 5

CANDIDATES = [
    {"key": "scraper_one/facebook-posts-search", "id": "TMBawM4LZpKN15DZX",
     "runs": 2239994, "price": 0.00259,
     "input": {"query": QUERY, "resultsCount": LIMIT, "searchType": "latest"},
     "note": "2.2M runs; searchType enum is top|latest (recency control, not content type)"},
    {"key": "powerai/facebook-post-search-scraper", "id": "Ew2lyICEnHMcqRo6T",
     "runs": 218486, "price": 0.003,
     "input": {"query": QUERY, "maxResults": LIMIT},
     "note": "has start_date/end_date, relevant to the historical-coverage question"},
    {"key": "danek/facebook-search-rental", "id": "xSewLChDcAk1hNhga",
     "runs": 2971199, "price": 0.005,
     "input": {"query": QUERY, "search_type": "posts", "max_posts": LIMIT, "max_retries": 3},
     "note": "3M runs; 'rental' pricing may gate it the way facebook-search-ppr did"},
]

EST = sum(c["price"] * LIMIT for c in CANDIDATES)


def run_one(c):
    """Start, poll, collect items AND the log (the log is where the gates show up)."""
    r = requests.post(f"{API}/acts/{c['id']}/runs",
                      headers={**AUTH, "Content-Type": "application/json"},
                      params={"maxItems": LIMIT, "maxTotalChargeUsd": round(c["price"] * LIMIT + 0.02, 3)},
                      data=json.dumps(c["input"]), timeout=60)
    if not r.ok:
        return None, [], f"START FAILED {r.status_code}: {r.text[:300]}"
    run = r.json()["data"]
    t0 = time.time()
    while run["status"] not in ("SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"):
        time.sleep(5)
        run = requests.get(f"{API}/actor-runs/{run['id']}", headers=AUTH, timeout=30).json()["data"]
        if time.time() - t0 > 300:
            break
    items = []
    if run.get("defaultDatasetId"):
        items = requests.get(f"{API}/datasets/{run['defaultDatasetId']}/items",
                             headers=AUTH, params={"format": "json"}, timeout=120).json()
    log = requests.get(f"{API}/logs/{run['id']}", headers=AUTH, timeout=60).text
    return run, items, log


GATE_WORDS = ("paid users only", "free tier", "free-tier", "upgrade your", "limit:",
              "rate limit", "quota", "per 24h", "subscription", "trial")


def main():
    print("=" * 84)
    print(f"DISCOVERY BAKE-OFF -- query={QUERY!r}, {LIMIT} results per candidate")
    print(f"estimated total ${EST:.3f}")
    print("=" * 84)
    check_budget(EST)

    results = []
    for c in CANDIDATES:
        print(f"\n{'='*84}\n{c['key']}  ({c['runs']:,} runs, ${c['price']}/result)")
        print(f"  note : {c['note']}")
        print(f"  input: {json.dumps(c['input'])}")
        run, items, log = run_one(c)

        gates = []
        if isinstance(log, str):
            for line in log.splitlines():
                if any(w in line.lower() for w in GATE_WORDS):
                    gates.append(line.strip()[:180])

        kinds = Counter(classify_record(i) for i in items)
        posts = kinds.get("post", 0)
        if run is None:
            verdict, reason = "FAIL", log
        elif not items:
            verdict = "FAIL"
            reason = f"0 records. gate: {gates[-1]}" if gates else "0 records, no gate message in log"
        elif posts == 0:
            verdict, reason = "FAIL", f"returned {len(items)} records but 0 look like posts ({dict(kinds)})"
        else:
            verdict = "PASS" if not gates else "PASS-WITH-LIMIT"
            reason = f"{posts}/{len(items)} records are posts"
            if gates:
                reason += f" | GATE: {gates[-1]}"

        print(f"  status : {run.get('status') if run else 'n/a'}  items={len(items)}  cost=${run.get('usageTotalUsd') if run else 0}")
        print(f"  VERDICT: {verdict} -- {reason}")
        for g in gates[:3]:
            print(f"    log> {g}")
        for i, it in enumerate(items[:2]):
            if isinstance(it, dict):
                print(f"   [{i}] keys={sorted(it.keys())[:12]}")
                for k in ("text", "message", "url", "post_url", "timestamp", "time", "date", "error"):
                    if it.get(k):
                        print(f"       {k}: {str(it[k])[:110]}")

        results.append({
            "actor": c["key"], "actor_id": c["id"], "total_runs": c["runs"],
            "price_per_result_usd": c["price"], "input": c["input"], "note": c["note"],
            "verdict": verdict, "reason": reason,
            "returned": len(items), "record_kinds": dict(kinds),
            "gate_messages": gates,
            "fields_present": sorted({k for i in items if isinstance(i, dict) for k in i}),
            "run_id": run.get("id") if run else None,
            "status": run.get("status") if run else None,
            "cost_usd": run.get("usageTotalUsd") if run else None,
            "items_raw": items,
        })

    used, cap, remaining = budget()
    save("facebook_discovery_bakeoff.json",
         {"tested_at": now_iso(), "query": QUERY, "limit_per_candidate": LIMIT,
          "results": results,
          "budget_after": {"used_usd": used, "remaining_usd": remaining}})

    print("\n" + "=" * 84)
    print("BAKE-OFF SUMMARY")
    print("=" * 84)
    for r in results:
        print(f"  {r['verdict']:16s} {r['actor']:40s} {r['returned']:>2} items  ${r['cost_usd']}")
    print(f"\n  budget remaining: ${remaining:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
