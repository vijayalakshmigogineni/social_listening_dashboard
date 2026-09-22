"""Run the Reddit collector and store results in the DB.

Usage:
    python scripts/collect_reddit.py [--max-items 30] [--subreddits CodingandBilling MedicalCoding]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.collectors.common import upsert_normalized_items
from app.collectors.reddit import collect
from app.db.base import SessionLocal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-items", type=int, default=30)
    parser.add_argument("--subreddits", nargs="*", default=None)
    args = parser.parse_args()

    records = collect(subreddits=args.subreddits, max_items_per_subreddit=args.max_items)
    print(f"\nCollected {len(records)} normalized records total.")

    db = SessionLocal()
    try:
        summary = upsert_normalized_items(db, records)
    finally:
        db.close()

    print(f"DB upsert summary: {summary}")


if __name__ == "__main__":
    main()
