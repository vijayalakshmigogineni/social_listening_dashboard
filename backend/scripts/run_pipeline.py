"""Run the analysis pipeline over normalized_items and store AnalysisResult rows.

Usage:
    python scripts/run_pipeline.py [--source reddit] [--force]
                                   [--item-id reddit:abc123 ...] [--limit 30]

Each item produces one row under the current ANALYSIS_VERSION (unique key:
source_item_id + analysis_version). This calls the LLM for every RCM-relevant
post; to change only scoring weights on already-analyzed rows use
scripts/rescore.py instead (no LLM calls).

--force     re-runs and overwrites rows already analyzed; by default items
            that already have a current-version row are skipped
--item-id   (re-)analyze only this record (source:source_item_id), even if it
            already has a row; repeatable
--limit     analyze at most N items (pilot runs before a full re-run)

Each item is committed on its own, and an item that raises is rolled back,
reported and skipped (it stays unanalyzed, so the next run retries it) -- a
long run never loses finished work to one bad post. After three database
connection errors in a row the run stops; re-running resumes it.

The selection and storage logic lives in app/analysis/runner.py, shared with
the dashboard's Data Collection page.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.exc import OperationalError

from app.analysis import llm_fallback
from app.analysis.runner import analyze_item, select_items
from app.db.base import SessionLocal
from app.db.models import NormalizedItem

# Consecutive database connection errors after which the run stops instead of
# failing every remaining post (e.g. the network is down).
MAX_DB_ERRORS_IN_A_ROW = 3


def _item_id(value: str) -> tuple[str, str]:
    source, sep, source_item_id = value.partition(":")
    if not sep or not source or not source_item_id:
        raise argparse.ArgumentTypeError("expected source:source_item_id")
    return source, source_item_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--item-id", dest="item_ids", type=_item_id, action="append", default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        items, skipped = select_items(db, source=args.source, force=args.force or bool(args.item_ids),
                                      item_ids=args.item_ids, limit=args.limit)
        # Plain values up front: each item is re-loaded by id, so a rollback
        # or a replaced session never leaves the loop holding stale objects.
        todo = [(item.id, f"{item.source}:{item.source_item_id}") for item in items]
        print(f"{len(todo)} items to analyze (skipped as already analyzed: {skipped})", flush=True)

        processed = 0
        failed: list[str] = []
        db_errors_in_a_row = 0
        for n, (item_pk, key) in enumerate(todo, start=1):
            try:
                result = analyze_item(db, db.get(NormalizedItem, item_pk))
                db.commit()
            except Exception as exc:  # noqa: BLE001 -- report and move on
                try:
                    db.rollback()
                except Exception:  # noqa: BLE001 -- connection is gone (e.g. Neon dropped it)
                    db.close()
                    db = SessionLocal()
                failed.append(f"{key}: {type(exc).__name__}: {str(exc)[:160]}")
                print(f"[{n}/{len(todo)}] {key}: FAILED ({type(exc).__name__})", flush=True)
                db_errors_in_a_row = db_errors_in_a_row + 1 if isinstance(exc, OperationalError) else 0
                if db_errors_in_a_row >= MAX_DB_ERRORS_IN_A_ROW:
                    print(f"\nStopping: {db_errors_in_a_row} database errors in a row (network down?). "
                          "Re-run to resume; finished posts are saved.", flush=True)
                    break
                continue
            db_errors_in_a_row = 0
            processed += 1
            print(
                f"[{n}/{len(todo)}] {key}: rcm_relevant={result.rcm_relevant} "
                f"llm={result.score_breakdown['llm_source']} score={result.final_score:.1f}",
                flush=True,
            )

        print(f"\nDone. processed={processed} failed={len(failed)} skipped(already analyzed)={skipped}")
        print(f"LLM calls: {llm_fallback.CALL_STATS_BY_KIND}")
        for line in failed:
            print(f"  FAILED {line}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
