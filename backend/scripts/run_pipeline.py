"""Run the analysis pipeline over normalized_items and store AnalysisResult rows.

Usage:
    python scripts/run_pipeline.py [--source reddit] [--force]

Each item produces one row per scoring version -- v1 and v2 -- from a single
pass over Steps 1-5, which are the expensive part. The rows coexist because
the unique key is (source_item_id, analysis_version).

--force re-runs and overwrites rows already analyzed (useful while
iterating); by default items already analyzed under ALL versions are skipped.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.analysis.pipeline import run_pipeline_all_versions
from app.db.base import SessionLocal
from app.db.models import AnalysisResult as AnalysisResultRow
from app.db.models import NormalizedItem
from app.schemas.analysis import ANALYSIS_VERSION, ANALYSIS_VERSION_V2

ALL_VERSIONS = (ANALYSIS_VERSION, ANALYSIS_VERSION_V2)


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

        # An item counts as done only once every version has a row, so adding
        # a new scoring version backfills it without --force.
        seen: dict[str, set[str]] = {}
        for sid, ver in db.query(
            AnalysisResultRow.source_item_id, AnalysisResultRow.analysis_version
        ).all():
            seen.setdefault(sid, set()).add(ver)
        already_done = {sid for sid, vers in seen.items() if set(ALL_VERSIONS) <= vers}

        processed = 0
        skipped = 0
        for item in items:
            if not args.force and item.source_item_id in already_done:
                skipped += 1
                continue

            matched_keywords = (item.source_metadata or {}).get("matched_rcm_keywords")
            results = run_pipeline_all_versions(
                source_item_id=item.source_item_id,
                title=item.title,
                text=item.text,
                created_at=item.created_at,
                matched_keywords=matched_keywords,
            )

            for result in results:
                # Look up by the result's OWN version, not a module constant --
                # otherwise a second version is checked against the first's row.
                existing = (
                    db.query(AnalysisResultRow)
                    .filter_by(
                        source_item_id=result.source_item_id,
                        analysis_version=result.analysis_version,
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
