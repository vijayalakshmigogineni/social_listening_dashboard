"""Run the LinkedIn collector and store results in the DB.

Usage:
    python scripts/collect_linkedin.py [--limit 10]              # all query families
    python scripts/collect_linkedin.py [--limit 10] --query "..." # single query, as before
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.collectors.common import upsert_normalized_items
from app.collectors.linkedin import collect, collect_families
from app.db.base import SessionLocal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--query", default=None, help="Single query; omit to run all query families")
    args = parser.parse_args()

    if args.query:
        records = collect(query=args.query, limit=args.limit)
    else:
        records = collect_families(limit_per_query=args.limit)
    print(f"\nCollected {len(records)} normalized records total.")

    db = SessionLocal()
    try:
        summary = upsert_normalized_items(db, records)
    finally:
        db.close()

    print(f"DB upsert summary: {summary}")


if __name__ == "__main__":
    main()
