"""Run the LinkedIn collector and store results in the DB.

Usage:
    python scripts/collect_linkedin.py [--limit 10] [--query "..."]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.collectors.common import upsert_normalized_items
from app.collectors.linkedin import DEFAULT_QUERY, collect
from app.db.base import SessionLocal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--query", default=DEFAULT_QUERY)
    args = parser.parse_args()

    records = collect(query=args.query, limit=args.limit)
    print(f"\nCollected {len(records)} normalized records total.")

    db = SessionLocal()
    try:
        summary = upsert_normalized_items(db, records)
    finally:
        db.close()

    print(f"DB upsert summary: {summary}")


if __name__ == "__main__":
    main()
