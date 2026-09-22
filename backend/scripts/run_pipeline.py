"""Run the analysis pipeline over normalized_items and store AnalysisResult rows.

Usage:
    python scripts/run_pipeline.py [--source reddit] [--force]

--force re-runs and overwrites rows already analyzed under the current
ANALYSIS_VERSION (useful while iterating); by default already-analyzed
items are skipped.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.analysis.pipeline import run_pipeline
from app.db.base import SessionLocal
from app.db.models import AnalysisResult as AnalysisResultRow
from app.db.models import NormalizedItem
from app.schemas.analysis import ANALYSIS_VERSION


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        query = db.query(NormalizedItem)
        if args.source:
            query = query.filter_by(source=args.source)
        items = query.all()

        already_done = {
            row.source_item_id
            for row in db.query(AnalysisResultRow.source_item_id)
            .filter_by(analysis_version=ANALYSIS_VERSION)
            .all()
        }

        processed = 0
        skipped = 0
        for item in items:
            if not args.force and item.source_item_id in already_done:
                skipped += 1
                continue

            matched_keywords = (item.source_metadata or {}).get("matched_rcm_keywords")
            result = run_pipeline(
                source_item_id=item.source_item_id,
                title=item.title,
                text=item.text,
                created_at=item.created_at,
                matched_keywords=matched_keywords,
            )

            existing = (
                db.query(AnalysisResultRow)
                .filter_by(
                    source_item_id=item.source_item_id, analysis_version=ANALYSIS_VERSION
                )
                .one_or_none()
            )
            payload = result.model_dump(exclude={"created_at", "updated_at"})
            if existing is None:
                db.add(AnalysisResultRow(**payload))
            else:
                for field, value in payload.items():
                    setattr(existing, field, value)

            processed += 1
            print(
                f"[{processed}] {item.source_item_id}: rcm_relevant={result.rcm_relevant} "
                f"problem_evidence={result.problem_evidence} score={result.final_score:.2f}"
            )

        db.commit()
        print(f"\nDone. processed={processed} skipped(already analyzed)={skipped}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
