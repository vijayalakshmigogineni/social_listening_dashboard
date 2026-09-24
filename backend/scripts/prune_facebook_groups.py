"""Delete stored Facebook posts from groups that were dropped from the collector.

Usage (from backend/):
    python scripts/prune_facebook_groups.py --groups medical_claims_tasks usa_medical_billing --dry-run
    python scripts/prune_facebook_groups.py --groups medical_claims_tasks usa_medical_billing

Removes normalized_items rows where source=facebook and
source_metadata.group_key is one of --groups, plus EVERY analysis_results row
for those posts (production and experiment versions alike), so no orphan
scores are left behind. --dry-run only lists what would be deleted.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.base import SessionLocal  # noqa: E402
from app.db.models import AnalysisResult, NormalizedItem  # noqa: E402


def prune(db, group_keys: set[str], dry_run: bool = False) -> dict:
    rows = [
        r for r in db.query(NormalizedItem).filter_by(source="facebook").all()
        if (r.source_metadata or {}).get("group_key") in group_keys
    ]
    ids = [r.source_item_id for r in rows]
    analysis_q = db.query(AnalysisResult).filter(AnalysisResult.source_item_id.in_(ids))
    summary = {
        "posts": len(ids),
        "analysis_rows": analysis_q.count() if ids else 0,
        "ids": sorted(ids),
        "by_group": {k: sum(1 for r in rows if r.source_metadata.get("group_key") == k)
                     for k in sorted(group_keys)},
        "dry_run": dry_run,
    }
    if not dry_run and ids:
        analysis_q.delete(synchronize_session=False)
        for r in rows:
            db.delete(r)
        db.commit()
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--groups", nargs="+", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        summary = prune(db, set(args.groups), args.dry_run)
    finally:
        db.close()

    verb = "Would delete" if args.dry_run else "Deleted"
    print(f"{verb} {summary['posts']} posts and {summary['analysis_rows']} analysis rows "
          f"{summary['by_group']}")
    for sid in summary["ids"]:
        print(f"  facebook:{sid}")


if __name__ == "__main__":
    main()
