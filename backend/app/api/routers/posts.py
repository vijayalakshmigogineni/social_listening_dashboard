"""
Post listing/search/filter/detail endpoints. Every record returned here is
the join of a normalized_items row with its current-version (ANALYSIS_VERSION)
analysis_results row (LEFT JOIN, so unanalyzed items are still
visible/debuggable, just with null analysis fields and a final_score of None
so they sort last). The opportunity filters use app/api/opportunity.py, the
same definitions as the Overview KPIs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session

from app.analysis.scoring_opportunity import is_opportunity
from app.api.opportunity import base_query, not_opportunity_clause, opportunity_clause, to_utc
from app.db.base import get_db
from app.db.models import AnalysisResult, NormalizedItem
from app.schemas.analysis import ANALYSIS_VERSION

router = APIRouter()

SORT_OPTIONS = {"score_desc", "score_asc", "recent", "oldest"}


def _row_to_dict(item: NormalizedItem, analysis: AnalysisResult | None) -> dict[str, Any]:
    base = {
        "source": item.source,
        "source_item_id": item.source_item_id,
        "url": item.url,
        "title": item.title,
        "text": item.text,
        "author_id": item.author_id,
        "author_name": item.author_name,
        "author_profile_url": item.author_profile_url,
        "author_role": item.author_role,
        "organization_name": item.organization_name,
        "organization_url": item.organization_url,
        "location": item.location,
        "created_at": item.created_at,
        "collected_at": item.collected_at,
        "engagement": item.engagement,
        "parent_id": item.parent_id,
        "conversation_id": item.conversation_id,
        "media_type": item.media_type,
        "source_metadata": item.source_metadata,
    }

    if analysis is None:
        base.update(
            {
                "analyzed": False,
                "rcm_relevant": None,
                "problem_evidence": None,
                "problem_category": [],
                "payer_tags": [],
                "procedure_tags": [],
                "denial_reason_tags": [],
                "specialty": None,
                "speaker_type": None,
                "content_stance": None,
                "seeking_level": None,
                "evidence_quote": None,
                "confidence": None,
                "final_score": None,
                "llm_score": None,
                "rcm_score": None,
                "step3_score": None,
                "opportunity_type": None,
                "probeps_fit": None,
                "opportunity_reasoning": None,
                "is_opportunity": False,
                "score_breakdown": None,
                "analysis_version": None,
                "scoring_version": None,
            }
        )
    else:
        breakdown = analysis.score_breakdown or {}
        assessment = breakdown.get("llm_assessment") or {}
        base.update(
            {
                "analyzed": True,
                "rcm_relevant": analysis.rcm_relevant,
                "problem_evidence": analysis.problem_evidence,
                "problem_category": analysis.problem_category,
                "payer_tags": analysis.payer_tags,
                "procedure_tags": analysis.procedure_tags,
                "denial_reason_tags": analysis.denial_reason_tags,
                "specialty": analysis.specialty,
                "speaker_type": analysis.speaker_type,
                "content_stance": analysis.content_stance,
                "seeking_level": analysis.seeking_level,
                "evidence_quote": analysis.evidence_quote,
                "confidence": analysis.confidence,
                "final_score": analysis.final_score,
                "llm_score": breakdown.get("llm_score"),
                "rcm_score": breakdown.get("rcm_score"),
                "step3_score": breakdown.get("step3_score"),
                "opportunity_type": assessment.get("opportunity_type"),
                "probeps_fit": assessment.get("probeps_fit"),
                "opportunity_reasoning": assessment.get("opportunity_reasoning"),
                "is_opportunity": is_opportunity(analysis.final_score, analysis.problem_evidence),
                "score_breakdown": analysis.score_breakdown,
                "analysis_version": analysis.analysis_version,
                "scoring_version": analysis.scoring_version,
            }
        )
    return base



@router.get("")
def list_posts(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Keyword search across title/text/tags"),
    source: Optional[str] = Query(None),
    problem_category: Optional[str] = Query(None),
    payer: Optional[str] = Query(None),
    specialty: Optional[str] = Query(None),
    seeking_level: Optional[str] = Query(None),
    speaker_type: Optional[str] = Query(None),
    content_stance: Optional[str] = Query(None),
    rcm_relevant: Optional[bool] = Query(None),
    opportunity: Optional[bool] = Query(
        None, description="Only (true) or no (false) opportunities -- same rule as the Overview KPI"),
    opportunity_type: Optional[str] = Query(None),
    score_min: Optional[float] = Query(None),
    score_max: Optional[float] = Query(None),
    date_from: Optional[datetime] = Query(None, description="Post date (created_at) from"),
    date_to: Optional[datetime] = Query(None, description="Post date (created_at) to"),
    collected_from: Optional[datetime] = Query(None, description="Collected (inserted_at) from"),
    collected_to: Optional[datetime] = Query(None, description="Collected (inserted_at) to"),
    sort: str = Query("score_desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    if sort not in SORT_OPTIONS:
        raise HTTPException(400, f"sort must be one of {sorted(SORT_OPTIONS)}")

    query = base_query(db)

    if source:
        query = query.filter(NormalizedItem.source == source)
    if date_from:
        query = query.filter(NormalizedItem.created_at >= to_utc(date_from))
    if date_to:
        query = query.filter(NormalizedItem.created_at <= to_utc(date_to))
    if collected_from:
        query = query.filter(NormalizedItem.inserted_at >= to_utc(collected_from))
    if collected_to:
        query = query.filter(NormalizedItem.inserted_at <= to_utc(collected_to))
    if rcm_relevant is not None:
        query = query.filter(AnalysisResult.rcm_relevant == rcm_relevant)
    if opportunity is not None:
        query = query.filter(opportunity_clause() if opportunity else not_opportunity_clause())
    if opportunity_type:
        query = query.filter(
            AnalysisResult.score_breakdown["llm_assessment"]["opportunity_type"].as_string()
            == opportunity_type
        )
    if problem_category:
        query = query.filter(
            cast(AnalysisResult.problem_category, String).contains(f'"{problem_category}"')
        )
    if payer:
        query = query.filter(cast(AnalysisResult.payer_tags, String).contains(f'"{payer}"'))
    if specialty:
        query = query.filter(AnalysisResult.specialty == specialty)
    if seeking_level == "none":
        query = query.filter(AnalysisResult.id.isnot(None), AnalysisResult.seeking_level.is_(None))
    elif seeking_level:
        query = query.filter(AnalysisResult.seeking_level == seeking_level)
    if speaker_type:
        query = query.filter(AnalysisResult.speaker_type == speaker_type)
    if content_stance:
        query = query.filter(AnalysisResult.content_stance == content_stance)
    if score_min is not None:
        query = query.filter(AnalysisResult.final_score >= score_min)
    if score_max is not None:
        query = query.filter(AnalysisResult.final_score <= score_max)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(
            or_(
                func.lower(NormalizedItem.title).like(like),
                func.lower(NormalizedItem.text).like(like),
                func.lower(cast(AnalysisResult.payer_tags, String)).like(like),
                func.lower(cast(AnalysisResult.procedure_tags, String)).like(like),
                func.lower(cast(AnalysisResult.problem_category, String)).like(like),
                func.lower(func.coalesce(AnalysisResult.specialty, "")).like(like),
                func.lower(func.coalesce(NormalizedItem.organization_name, "")).like(like),
            )
        )

    total = query.count()

    if sort == "score_desc":
        query = query.order_by(AnalysisResult.final_score.desc().nulls_last())
    elif sort == "score_asc":
        query = query.order_by(AnalysisResult.final_score.asc().nulls_last())
    elif sort == "recent":
        query = query.order_by(NormalizedItem.created_at.desc().nulls_last())
    elif sort == "oldest":
        query = query.order_by(NormalizedItem.created_at.asc().nulls_last())

    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": [_row_to_dict(item, analysis) for item, analysis in rows],
    }


@router.get("/{source}/{source_item_id}")
def get_post(
    source: str,
    source_item_id: str,
    db: Session = Depends(get_db),
):
    item = (
        db.query(NormalizedItem)
        .filter_by(source=source, source_item_id=source_item_id)
        .one_or_none()
    )
    if item is None:
        raise HTTPException(404, "post not found")

    analysis = (
        db.query(AnalysisResult)
        .filter_by(
            source_item_id=source_item_id, analysis_version=ANALYSIS_VERSION
        )
        .one_or_none()
    )
    return _row_to_dict(item, analysis)
