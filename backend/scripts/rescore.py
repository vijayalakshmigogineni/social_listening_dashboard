"""Re-score stored analysis rows offline -- no LLM calls, no re-collection.

Usage (from backend/):
    python scripts/rescore.py --dry-run          # distribution report only
    python scripts/rescore.py                    # rewrite final_score/score_breakdown
    python scripts/rescore.py --source reddit
    python scripts/rescore.py --compare sld-analysis-v3 --dry-run

Reads every row under the current ANALYSIS_VERSION and recomputes its score
from what the row already holds: the Step 1 columns (rcm_relevant +
confidence), the Step 3 taxonomy columns and score_breakdown["llm_assessment"]
(the persisted Step 2 LLM output). Use it after changing weights or points in
app/analysis/scoring_opportunity.py; bump SCORING_VERSION when you do.

Rows that are RCM-relevant but have no llm_assessment cannot be scored
offline and are reported as "needs re-analysis" (run scripts/run_pipeline.py).

--compare VERSION adds a side-by-side of an older analysis version's stored
scores for the same posts (e.g. the retired v3 rows), to review movers.
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.analysis.pipeline import rescore_row  # noqa: E402
from app.analysis.scoring_opportunity import OPPORTUNITY_THRESHOLD, is_opportunity  # noqa: E402
from app.db.base import SessionLocal  # noqa: E402
from app.db.models import AnalysisResult, NormalizedItem  # noqa: E402
from app.schemas.analysis import (  # noqa: E402
    ANALYSIS_VERSION,
    SCORING_VERSION,
    ScoreBreakdownOpportunity,
    Step3Taxonomy,
)

BANDS = (20, 40, 60, 70, 80, 90)


def taxonomy_of(row: AnalysisResult) -> Step3Taxonomy:
    return Step3Taxonomy(
        problem_category=row.problem_category or [],
        procedure_tags=row.procedure_tags or [],
        payer_tags=row.payer_tags or [],
        denial_reason_tags=row.denial_reason_tags or [],
        cpt_hcpcs_codes=row.cpt_hcpcs_codes or [],
        specialty=row.specialty,
        mentioned_organization=row.mentioned_organization,
    )


def percentile(sorted_values: list[float], p: float) -> float:
    """Linear-interpolated percentile (p in 0-100) of an already-sorted list."""
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (k - lo)


def distribution(scores: list[float]) -> dict:
    if not scores:
        return {"n": 0}
    s = sorted(scores)
    report = {
        "n": len(s),
        "min": s[0],
        "max": s[-1],
        "mean": statistics.fmean(s),
        "median": statistics.median(s),
        "p75": percentile(s, 75),
        "p90": percentile(s, 90),
        "zeros": sum(1 for v in s if v == 0),
    }
    report.update({f">={b}": sum(1 for v in s if v >= b) for b in BANDS})
    return report


def print_distribution(label: str, scores: list[float]) -> None:
    d = distribution(scores)
    if d["n"] == 0:
        print(f"{label}: no rows")
        return
    stats = "  ".join(f"{k}={d[k]:.1f}" for k in ("min", "max", "mean", "median", "p75", "p90"))
    bands = "  ".join(f"{k}:{d[k]}" for k in ["zeros", *[f">={b}" for b in BANDS]])
    print(f"{label} (n={d['n']}): {stats}\n    {bands}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=None)
    parser.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    parser.add_argument("--compare", default=None, metavar="ANALYSIS_VERSION")
    parser.add_argument("--top", type=int, default=15, help="list the top N after re-scoring")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        query = (
            db.query(NormalizedItem, AnalysisResult)
            .join(AnalysisResult, AnalysisResult.source_item_id == NormalizedItem.source_item_id)
            .filter(AnalysisResult.analysis_version == ANALYSIS_VERSION)
        )
        if args.source:
            query = query.filter(NormalizedItem.source == args.source)
        rows = query.all()

        rescored: list[tuple[NormalizedItem, AnalysisResult, ScoreBreakdownOpportunity]] = []
        needs_reanalysis: list[str] = []
        by_source: dict[str, list[float]] = {}
        for item, row in rows:
            breakdown = rescore_row(row.rcm_relevant, row.rcm_relevance_confidence,
                                    row.score_breakdown, taxonomy_of(row))
            if breakdown is None:
                needs_reanalysis.append(f"{item.source}:{item.source_item_id}")
                continue
            rescored.append((item, row, breakdown))
            by_source.setdefault(item.source, []).append(breakdown.final_score)
            if not args.dry_run:
                row.score_breakdown = breakdown.model_dump()
                row.final_score = breakdown.final_score
                row.scoring_version = SCORING_VERSION

        print(f"{ANALYSIS_VERSION} rows: {len(rows)}  re-scored: {len(rescored)}  "
              f"needs re-analysis: {len(needs_reanalysis)}  scoring: {SCORING_VERSION}\n")
        print_distribution("ALL", [bd.final_score for _, _, bd in rescored])
        for source in sorted(by_source):
            print_distribution(f"  {source}", by_source[source])

        opportunities = sum(1 for _, row, bd in rescored if is_opportunity(bd.final_score, row.problem_evidence))
        print(f"\nopportunities (score >= {OPPORTUNITY_THRESHOLD:g} with problem evidence): {opportunities}")

        print(f"\nTop {args.top}:")
        for item, _, bd in sorted(rescored, key=lambda t: t[2].final_score, reverse=True)[: args.top]:
            title = (item.title or item.text or "").replace("\n", " ")[:70]
            print(f"  {bd.final_score:5.1f}  llm={bd.llm_score:5.1f} rcm={bd.rcm_score:5.1f} "
                  f"s3={bd.step3_score:5.1f}  {item.source}:{item.source_item_id}  {title}")

        if args.compare:
            old = dict(
                db.query(AnalysisResult.source_item_id, AnalysisResult.final_score)
                .filter(AnalysisResult.analysis_version == args.compare).all()
            )
            pairs = [(item, bd.final_score, old[item.source_item_id]) for item, _, bd in rescored
                     if item.source_item_id in old]
            print(f"\nCompared with {args.compare} ({len(pairs)} shared posts):")
            print_distribution(f"  {args.compare}", [o for _, _, o in pairs])
            movers = sorted(pairs, key=lambda t: t[1] - t[2])
            for label, chunk in (("fallers", movers[:10]), ("risers", movers[::-1][:10])):
                print(f"  biggest {label}:")
                for item, new, prev in chunk:
                    print(f"    {prev:5.1f} -> {new:5.1f}  {item.source}:{item.source_item_id}")

        if needs_reanalysis:
            print("\nNeeds re-analysis (RCM-relevant, no stored llm_assessment):")
            for key in needs_reanalysis[:20]:
                print(f"  {key}")
            if len(needs_reanalysis) > 20:
                print(f"  ... and {len(needs_reanalysis) - 20} more")

        if args.dry_run:
            print("\n--dry-run: nothing written.")
        else:
            db.commit()
            print(f"\nWrote {len(rescored)} rows.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
