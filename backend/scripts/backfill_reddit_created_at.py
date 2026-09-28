"""One-off: fill normalized_items.created_at for Reddit rows collected before
the collector read the actor's `created_utc` field (they were stored undated).

Usage (from backend/):
    python scripts/backfill_reddit_created_at.py            # dry run (default)
    python scripts/backfill_reddit_created_at.py --apply    # write

Only rows with created_at IS NULL are touched; the value comes from the
row's own raw_data, parsed exactly as the collector now parses it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.collectors.common import parse_datetime  # noqa: E402
from app.db.base import SessionLocal  # noqa: E402
from app.db.models import NormalizedItem  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        rows = (
            db.query(NormalizedItem)
            .filter(NormalizedItem.source == "reddit", NormalizedItem.created_at.is_(None))
            .all()
        )
        filled = unparseable = 0
        for row in rows:
            raw = row.raw_data or {}
            value = parse_datetime(raw.get("createdAt") or raw.get("created_at") or raw.get("created_utc"))
            if value is None:
                unparseable += 1
                continue
            filled += 1
            if args.apply:
                row.created_at = value
        print(f"undated reddit rows: {len(rows)}  fillable: {filled}  no date in raw_data: {unparseable}")
        if args.apply:
            db.commit()
            print(f"wrote {filled} rows")
        else:
            print("dry run: nothing written (use --apply)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
