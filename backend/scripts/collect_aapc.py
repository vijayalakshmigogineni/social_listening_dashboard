"""Run the AAPC collector and store results in the DB.

Usage:
    python scripts/collect_aapc.py [--max-threads 5]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.collectors.aapc import collect
from app.collectors.common import upsert_normalized_items
from app.db.base import SessionLocal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-threads", type=int, default=5)
    args = parser.parse_args()

    records = collect(max_threads_per_forum=args.max_threads)
    print(f"\nCollected {len(records)} normalized records total.")

    db = SessionLocal()
    try:
        summary = upsert_normalized_items(db, records)
    finally:
        db.close()

    print(f"DB upsert summary: {summary}")


if __name__ == "__main__":
    main()
