"""
Actor selection study, step 3 -- does ONE discovery actor cover posts, groups
AND pages?

scrapeforge/facebook-search-posts declares search_type enum
[posts, pages, groups, people, videos, events]. Declaring it is not the same as
returning it -- parseforge declared searchType="posts" and returned page
profiles. So each mode gets a 5-result probe.

If all three modes work, the project needs ONE discovery actor instead of three.
Cost: 3 modes x 5 results x $0.00259 ~= $0.04.
"""

import sys
from collections import Counter

from fb_common import run_actor, run_meta, classify_record, check_budget, budget, save, now_iso

QUERY = "medical billing"
MODES = ["groups", "pages"]   # "posts" already proven in Task 2
LIMIT = 5
EST = len(MODES) * LIMIT * 0.00259 + len(MODES) * 0.00005


def main():
    print(f"probing search_type modes {MODES} with query={QUERY!r}, {LIMIT} results each")
    print(f"est cost ${EST:.3f}")
    check_budget(EST)

    out = []
    for mode in MODES:
        run_input = {"query": QUERY, "search_type": mode, "max_results": LIMIT}
        run, items = run_actor("search", run_input, max_items=LIMIT,
                               max_charge_usd=round(LIMIT * 0.00259 + 0.02, 3),
                               label=f"search_type={mode}")
        kinds = Counter(classify_record(i) for i in items)
        print(f"\n  search_type={mode}: {len(items)} records  kinds={dict(kinds)}")
        for i, it in enumerate(items[:5]):
            if not isinstance(it, dict):
                continue
            print(f"   [{i}] keys={sorted(it.keys())[:14]}")
            for k in ("id", "group_id", "page_id", "name", "title", "url", "members",
                      "members_count", "followers", "likes", "category", "description",
                      "about", "privacy", "error"):
                if it.get(k) not in (None, "", [], {}):
                    print(f"       {k}: {str(it[k])[:120]}")
        out.append({"search_type": mode, "query": QUERY, "returned": len(items),
                    "record_kinds": dict(kinds),
                    "fields_present": sorted({k for i in items if isinstance(i, dict) for k in i}),
                    "apify": run_meta(run, "search", run_input),
                    "items_raw": items})

    used, cap, remaining = budget()
    save("facebook_search_type_probe.json",
         {"probed_at": now_iso(), "modes": out,
          "budget_after": {"used_usd": used, "remaining_usd": remaining}})
    print(f"\n  budget remaining: ${remaining:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
