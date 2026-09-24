"""Run the analysis pipeline over normalized_items and store AnalysisResult rows.

Usage:
    python scripts/run_pipeline.py [--source reddit] [--force]

Each item produces one row per scoring version -- v1 and v2 -- from a single
pass over Steps 1-5, which are the expensive part. The rows coexist because
the unique key is (source_item_id, analysis_version).

--force re-runs and overwrites rows already analyzed (useful while
iterating); by default items already analyzed under ALL versions are skipped.

The selection and storage logic lives in app/analysis/runner.py, shared with
the dashboard's Data Collection page.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.analysis.runner import analyze_item, select_items
from app.db.base import SessionLocal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        items, skipped = select_items(db, source=args.source, force=args.force)

        processed = 0
        for item in items:
            results = analyze_item(db, item)
            processed += 1
            scores = "  ".join(f"{r.scoring_version}={r.final_score:.2f}" for r in results)
            print(
                f"[{processed}] {item.source_item_id}: "
                f"rcm_relevant={results[0].rcm_relevant} {scores}",
                flush=True,
            )

        db.commit()
        print(f"\nDone. processed={processed} skipped(already analyzed)={skipped}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
