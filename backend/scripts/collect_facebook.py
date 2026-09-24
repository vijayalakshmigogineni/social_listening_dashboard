"""Run the Facebook collector and store results in the DB.

Usage:
    python scripts/collect_facebook.py [--limit 20] [--per-group 8]
    python scripts/collect_facebook.py --top-up --limit 20 --groups pmr_interventional_pain_billing --per-group 12

--limit is the TOTAL number of posts kept (round-robin across groups);
--per-group is how many posts each group's actor run fetches.
--top-up counts the Facebook posts already stored and only adds new ones
until the stored total reaches --limit (already-stored ids are skipped).
Each run costs Apify credits (~$0.005 per post fetched, capped per run).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.collectors.common import upsert_normalized_items
from app.collectors.facebook import (
    DEFAULT_GROUPS,
    DEFAULT_LIMIT,
    DEFAULT_PER_GROUP,
    MAX_CHARGE_PER_RUN_USD,
    collect,
)
from app.db.base import SessionLocal
from app.db.models import NormalizedItem


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--per-group", type=int, default=DEFAULT_PER_GROUP)
    parser.add_argument("--groups", nargs="*", default=None,
                        help=f"Subset of group keys: {sorted(DEFAULT_GROUPS)}")
    parser.add_argument("--top-up", action="store_true")
    parser.add_argument("--max-charge", type=float, default=MAX_CHARGE_PER_RUN_USD,
                        help="Apify spend ceiling per group run, USD")
    args = parser.parse_args()

    groups = None
    if args.groups:
        unknown = set(args.groups) - set(DEFAULT_GROUPS)
        if unknown:
            parser.error(f"unknown group keys: {sorted(unknown)}")
        groups = {k: DEFAULT_GROUPS[k] for k in args.groups}

    db = SessionLocal()
    try:
        limit, exclude = args.limit, None
        if args.top_up:
            exclude = {sid for (sid,) in db.query(NormalizedItem.source_item_id)
                       .filter_by(source="facebook").all()}
            limit = args.limit - len(exclude)
            print(f"[facebook] top-up: {len(exclude)} already stored, adding up to {limit}")
            if limit <= 0:
                print("Nothing to do.")
                return

        records = collect(groups=groups, limit=limit, per_group=args.per_group,
                          exclude_ids=exclude, max_charge_usd=args.max_charge)
        print(f"\nCollected {len(records)} normalized records total.")
        summary = upsert_normalized_items(db, records)
    finally:
        db.close()

    print(f"DB upsert summary: {summary}")


if __name__ == "__main__":
    main()
