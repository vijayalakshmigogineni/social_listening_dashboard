"""Dashboard summary endpoint -- aggregate counts for the CEO Overview tab."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.routers.posts import resolve_version
from app.db.base import get_db
from app.db.models import AnalysisResult, NormalizedItem

router = APIRouter()


@router.get("/summary")
def summary(
    db: Session = Depends(get_db),
    version: str = Query("v1", description="Scoring version to read: v1 or v2"),
):
    analysis_version = resolve_version(version)
    total_posts = db.query(func.count(NormalizedItem.id)).scalar()

    analyzed_q = db.query(AnalysisResult).filter_by(analysis_version=analysis_version)
    total_analyzed = analyzed_q.count()
    total_rcm_relevant = analyzed_q.filter(AnalysisResult.rcm_relevant.is_(True)).count()
    total_problem_evidence = analyzed_q.filter(AnalysisResult.problem_evidence.is_(True)).count()

    by_source = dict(
        db.query(NormalizedItem.source, func.count(NormalizedItem.id))
        .group_by(NormalizedItem.source)
        .all()
    )

    by_seeking_level = dict(
        analyzed_q.with_entities(AnalysisResult.seeking_level, func.count(AnalysisResult.id))
        .group_by(AnalysisResult.seeking_level)
        .all()
    )

    by_speaker_type = dict(
        analyzed_q.with_entities(AnalysisResult.speaker_type, func.count(AnalysisResult.id))
        .group_by(AnalysisResult.speaker_type)
        .all()
    )

    avg_score = analyzed_q.with_entities(func.avg(AnalysisResult.final_score)).scalar()

    # Problem categories are stored as a JSON list per row -- count in Python
    # rather than fighting SQLite JSON1 syntax for a small V1 dataset.
    category_counts: dict[str, int] = {}
    for (categories,) in analyzed_q.with_entities(AnalysisResult.problem_category).all():
        for c in categories or []:
            category_counts[c] = category_counts.get(c, 0) + 1

    return {
        "total_posts": total_posts,
        "total_analyzed": total_analyzed,
        "total_rcm_relevant": total_rcm_relevant,
        "total_problem_evidence": total_problem_evidence,
        "avg_score": round(avg_score, 2) if avg_score is not None else None,
        "by_source": by_source,
        "by_seeking_level": by_seeking_level,
        "by_speaker_type": by_speaker_type,
        "by_problem_category": category_counts,
        "analysis_version": analysis_version,
    }
