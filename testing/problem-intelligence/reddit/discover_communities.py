"""
Phase 1b step 1 -- measure candidate communities before collecting from them.

"Most followed with frequent discussions" is decided from data, not from a
guess. This probes a curated candidate list via the Apify actor's community
search and records, per community, weekly active users and weekly
contributions.

Known limitation: the actor returns numberOfMembers = 0 for every community,
so subscriber count is unavailable through this route. weeklyActiveUsers and
weeklyContributions are the usable signals, and weeklyContributions is the
better proxy for "frequent discussions" regardless.

Output: data/raw/community_probe.json
"""

import json
from pathlib import Path
from datetime import datetime, timezone

from fetch_reddit_60 import run_actor

HERE = Path(__file__).resolve().parent
OUT = HERE / "data" / "raw" / "community_probe.json"

# Candidates: the roadmap's named list, plus RCM-adjacent and clinician
# communities, plus pain-specific ones -- Phase 1 found pain relevance at
# 1-in-60, so whether any community carries it is an open question worth
# measuring here rather than assuming.
CANDIDATES = [
    # already collected in Phase 1, probed for comparison
    "CodingandBilling",
    "MedicalCoding",
    # roadmap-named
    "Medicalbillingandcoding",
    "healthIT",
    "medicine",
    "FamilyMedicine",
    "physicianassistant",
    # RCM / practice operations adjacent
    "MedicalBilling",
    "revenuecycle",
    "DentalBilling",
    "healthcare",
    "HealthInsurance",
    "Medicaid",
    "privatepractice",
    "therapists",
    "Optometry",
    "physicaltherapy",
    "dentistry",
    "nursing",
    "hospitalists",
    "emergencymedicine",
    "Psychiatry",
    # pain-specific -- the open question from Phase 1
    "ChronicPain",
    "painmanagement",
    "backpain",
]

BATCH = 8  # keep each actor run small enough to finish reliably


def probe(names):
    run_input = {
        "searches": names,
        "searchCommunities": True,
        "searchPosts": False,
        "searchComments": False,
        "searchUsers": False,
        "skipComments": True,
        "skipUserPosts": True,
        "skipCommunity": False,  # required: true returns nothing for community search
        "includeMediaLinks": True,
        "maxItems": len(names) * 6,
        "maxCommunitiesCount": 6,
        "ignoreStartUrls": True,
        "proxy": {"useApifyProxy": True},
    }
    run, items = run_actor(run_input)
    return run, items


def main():
    found = {}
    runs = []

    for i in range(0, len(CANDIDATES), BATCH):
        batch = CANDIDATES[i : i + BATCH]
        print(f"\nprobing batch {i // BATCH + 1}: {', '.join(batch)}")
        run, items = probe(batch)
        print(f"  status={run.get('status')} items={len(items)} cost={run.get('usageTotalUsd')}")
        runs.append(
            {
                "batch": batch,
                "run_id": run.get("id"),
                "status": run.get("status"),
                "usage_total_usd": run.get("usageTotalUsd"),
                "returned": len(items),
            }
        )
        for it in items:
            name = it.get("displayName")
            if name:
                found[name.lower()] = it

    payload = {
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "candidates": CANDIDATES,
        "runs": runs,
        "communities": list(found.values()),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Report only the communities we actually asked about; community search
    # returns fuzzy matches (a "revenue cycle" search returned r/economy).
    wanted = {c.lower() for c in CANDIDATES}
    rows = [v for k, v in found.items() if k in wanted]
    rows.sort(key=lambda x: (x.get("weeklyContributions") or 0), reverse=True)

    print("\n" + "=" * 78)
    print(f"{'community':30s} {'wklyActive':>11s} {'wklyContrib':>12s}  {'created':>10s}")
    print("=" * 78)
    for r in rows:
        created = (r.get("createdAt") or "")[:10]
        print(
            f"{r.get('displayName'):30s} {r.get('weeklyActiveUsers') or 0:>11} "
            f"{r.get('weeklyContributions') or 0:>12}  {created:>10s}"
        )

    missing = sorted(wanted - {r.get("displayName", "").lower() for r in rows})
    if missing:
        print("\nnot returned by community search:", ", ".join(missing))
    print(f"\nsaved: {OUT}")


if __name__ == "__main__":
    main()
