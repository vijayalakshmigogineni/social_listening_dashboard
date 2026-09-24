"""Evidence-gathering for Facebook source selection. Writes raw JSON only --
nothing here touches the database.

Usage (from backend/):
    python scripts/probe_facebook_groups.py discover --out data/facebook_sourcing/20260924 \
        --query "spinal cord stimulator denied UHC" --query "kyphoplasty prior authorization denied"
    python scripts/probe_facebook_groups.py probe --out data/facebook_sourcing/20260924 \
        --group 290657479460430 --group 153075608691474 --per-group 10

discover -- keyword post search (scraper_one/facebook-posts-search) to surface
            groups whose posts actually discuss SLD topics; group ids are pulled
            from /groups/<id>/ permalinks.
probe    -- recent posts from specific groups (apify/facebook-groups-scraper),
            so a group is judged by what it posts, not by its name.

Every run is recorded in <out>/spend.json with an estimated cost; a run that
would push the estimated total past --budget is refused before it starts.
Estimates are items x published price plus a per-run allowance, which errs
high; the Apify account usage is the authoritative figure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.collectors.apify_client import run_actor_sync  # noqa: E402

SEARCH_ACTOR = "scraper_one/facebook-posts-search"
GROUPS_ACTOR = "apify/facebook-groups-scraper"
GROUP_SEARCH_ACTOR = "easyapi/facebook-groups-search-scraper"
# group search observed at ~$0.23 per 15-result run (Apify run history, 24 Sep 2026)
PRICE_PER_ITEM = {SEARCH_ACTOR: 0.0026, GROUPS_ACTOR: 0.005, GROUP_SEARCH_ACTOR: 0.016}
RUN_ALLOWANCE_USD = 0.01
DEFAULT_BUDGET_USD = 1.20

GROUP_ID_RE = re.compile(r"facebook\.com/groups/([A-Za-z0-9._-]+)")


class BudgetExceeded(RuntimeError):
    pass


class Ledger:
    def __init__(self, path: Path, budget: float):
        self.path = path
        self.budget = budget
        self.runs = json.loads(path.read_text(encoding="utf-8"))["runs"] if path.exists() else []

    @property
    def spent(self) -> float:
        return round(sum(r["estimated_usd"] for r in self.runs), 4)

    def estimate(self, actor: str, max_items: int) -> float:
        return round(max_items * PRICE_PER_ITEM[actor] + RUN_ALLOWANCE_USD, 4)

    def check(self, actor: str, max_items: int) -> float:
        est = self.estimate(actor, max_items)
        if self.spent + est > self.budget:
            raise BudgetExceeded(
                f"run would bring estimated spend to ${self.spent + est:.2f} > budget ${self.budget:.2f}")
        return est

    def record(self, actor: str, label: str, max_items: int, returned: int) -> None:
        # Charge on what came back (pay-per-result), never less than the allowance.
        est = round(returned * PRICE_PER_ITEM[actor] + RUN_ALLOWANCE_USD, 4)
        self.runs.append({"at": datetime.now(timezone.utc).isoformat(), "actor": actor,
                          "label": label, "max_items": max_items, "returned": returned,
                          "estimated_usd": est})
        self.path.write_text(json.dumps({"budget_usd": self.budget, "spent_estimate_usd": self.spent,
                                         "runs": self.runs}, indent=1), encoding="utf-8")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:60]


def group_ids_in(items: list[dict]) -> list[str]:
    found = []
    for item in items:
        for m in GROUP_ID_RE.finditer(json.dumps(item, ensure_ascii=False)):
            if m.group(1) not in found:
                found.append(m.group(1))
    return found


def discover(out: Path, queries: list[str], per_query: int, ledger: Ledger, runner=run_actor_sync) -> dict:
    (out / "discovery").mkdir(parents=True, exist_ok=True)
    groups: dict[str, list[str]] = {}
    for query in queries:
        est = ledger.check(SEARCH_ACTOR, per_query)
        print(f"[discover] {query!r} (max {per_query}, est ${est:.3f})")
        items = runner(SEARCH_ACTOR, {"query": query, "resultsCount": per_query, "searchType": "latest"},
                       max_items=per_query, max_total_charge_usd=est + 0.02, timeout_s=900)
        ledger.record(SEARCH_ACTOR, f"discover:{query}", per_query, len(items))
        (out / "discovery" / f"{_slug(query)}.json").write_text(
            json.dumps({"query": query, "items": items}, indent=1, ensure_ascii=False), encoding="utf-8")
        for gid in group_ids_in(items):
            groups.setdefault(gid, []).append(query)
        print(f"[discover]   {len(items)} posts, groups: {group_ids_in(items)}")
    return groups


def group_search(out: Path, queries: list[str], per_query: int, ledger: Ledger, runner=run_actor_sync) -> dict:
    """Group directory search: names/URLs only, no posts -- candidates still
    have to be probed before they count as evidence."""
    (out / "group_search").mkdir(parents=True, exist_ok=True)
    found: dict[str, dict] = {}
    for query in queries:
        est = ledger.check(GROUP_SEARCH_ACTOR, per_query)
        print(f"[group-search] {query!r} (max {per_query}, est ${est:.3f})")
        items = runner(GROUP_SEARCH_ACTOR, {"searchQuery": query, "maxItems": per_query},
                       max_items=per_query, max_total_charge_usd=est + 0.05, timeout_s=900)
        ledger.record(GROUP_SEARCH_ACTOR, f"group-search:{query}", per_query, len(items))
        (out / "group_search" / f"{_slug(query)}.json").write_text(
            json.dumps({"query": query, "items": items}, indent=1, ensure_ascii=False), encoding="utf-8")
        for item in items:
            for gid in group_ids_in([item]):
                found.setdefault(gid, {"name": item.get("name"), "queries": []})["queries"].append(query)
        print(f"[group-search]   {len(items)} groups")
    return found


def probe(out: Path, group_ids: list[str], per_group: int, ledger: Ledger, runner=run_actor_sync) -> dict:
    (out / "probes").mkdir(parents=True, exist_ok=True)
    counts = {}
    for gid in group_ids:
        target = out / "probes" / f"{gid}.json"
        if target.exists():
            print(f"[probe] {gid}: already probed, skipping (no second charge)")
            continue
        est = ledger.check(GROUPS_ACTOR, per_group)
        url = f"https://www.facebook.com/groups/{gid}"
        print(f"[probe] {url} (max {per_group}, est ${est:.3f})")
        items = runner(GROUPS_ACTOR, {"startUrls": [{"url": url}], "resultsLimit": per_group,
                                      "viewOption": "CHRONOLOGICAL"},
                       max_items=per_group, max_total_charge_usd=est + 0.02, timeout_s=900)
        ledger.record(GROUPS_ACTOR, f"probe:{gid}", per_group, len(items))
        target.write_text(json.dumps({"group_id": gid, "group_url": url, "items": items},
                                     indent=1, ensure_ascii=False), encoding="utf-8")
        counts[gid] = len(items)
        title = next((i.get("groupTitle") for i in items if i.get("groupTitle")), None)
        print(f"[probe]   {len(items)} items, title={title!r}")
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["discover", "group-search", "probe"])
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--group", action="append", default=[])
    parser.add_argument("--per-query", type=int, default=12)
    parser.add_argument("--per-group", type=int, default=10)
    parser.add_argument("--budget", type=float, default=DEFAULT_BUDGET_USD)
    args = parser.parse_args()

    ledger = Ledger(args.out / "spend.json", args.budget)
    try:
        if args.mode == "discover":
            groups = discover(args.out, args.query, args.per_query, ledger)
            print(json.dumps(groups, indent=1))
        elif args.mode == "group-search":
            groups = group_search(args.out, args.query, args.per_query, ledger)
            print(json.dumps(groups, indent=1, ensure_ascii=False))
        else:
            probe(args.out, args.group, args.per_group, ledger)
    except BudgetExceeded as exc:
        print(f"STOPPED: {exc}")
    print(f"estimated spend so far: ${ledger.spent:.3f} of ${ledger.budget:.2f}")


if __name__ == "__main__":
    main()
