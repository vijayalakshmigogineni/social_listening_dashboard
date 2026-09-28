"""
Pipeline/debug endpoint -- explains how one record was scored. Powers the
developer-facing Pipeline/Debug tab, never the CEO-facing views.

Default (stored): the record's persisted current-version row -- the exact
score the dashboard shows, with its full breakdown (Step 1, Step 3, the LLM
assessment, the three normalized components, their 65/20/15 contributions
and caps). No LLM call, reproducible.

?live=true: re-runs every stage now (calls the LLM) and returns the full
per-stage trace as well; nothing is stored.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.analysis.pipeline import build_text, explain_pipeline
from app.analysis.runner import resolve_parent_text
from app.db.base import get_db
from app.db.models import AnalysisResult, NormalizedItem
from app.schemas.analysis import ANALYSIS_VERSION

router = APIRouter()


def _stored(db: Session, item: NormalizedItem) -> dict:
    row = (
        db.query(AnalysisResult)
        .filter_by(source_item_id=item.source_item_id, analysis_version=ANALYSIS_VERSION)
        .one_or_none()
    )
    base = {
        "mode": "stored",
        "input_text": build_text(item.title, item.text),
        "analysis_version": ANALYSIS_VERSION,
    }
    if row is None:
        return {**base, "analyzed": False, "scoring_version": None,
                "score_breakdown": None, "final_score": None}
    return {
        **base,
        "analyzed": True,
        "scoring_version": row.scoring_version,
        "step1_rcm_relevance": {
            "rcm_relevant": row.rcm_relevant,
            "rcm_relevance_confidence": row.rcm_relevance_confidence,
        },
        "step3_taxonomy": {
            "problem_category": row.problem_category,
            "payer_tags": row.payer_tags,
            "procedure_tags": row.procedure_tags,
            "denial_reason_tags": row.denial_reason_tags,
            "cpt_hcpcs_codes": row.cpt_hcpcs_codes,
            "specialty": row.specialty,
            "mentioned_organization": row.mentioned_organization,
        },
        "step5_evidence_confidence": {
            "evidence_quote": row.evidence_quote,
            "confidence": row.confidence,
        },
        "score_breakdown": row.score_breakdown,
        "final_score": row.final_score,
    }


@router.get("/{source}/{source_item_id}")
def explain(
    source: str,
    source_item_id: str,
    db: Session = Depends(get_db),
    live: bool = Query(False, description="Re-run every stage now (calls the LLM)"),
):
    item = (
        db.query(NormalizedItem)
        .filter_by(source=source, source_item_id=source_item_id)
        .one_or_none()
    )
    if item is None:
        raise HTTPException(404, "post not found")

    if live:
        explanation = {
            "mode": "live",
            "analyzed": True,
            **explain_pipeline(
                title=item.title,
                text=item.text,
                created_at=item.created_at,
                matched_keywords=(item.source_metadata or {}).get("matched_rcm_keywords"),
                parent_text=resolve_parent_text(db, item.source, item.parent_id),
                source=item.source,
            ),
        }
    else:
        explanation = _stored(db, item)

    return {
        "raw_record": {
            "source": item.source,
            "source_item_id": item.source_item_id,
            "title": item.title,
            "text": item.text,
            "url": item.url,
            "raw_data": item.raw_data,
        },
        "normalized_record": {
            "source": item.source,
            "source_item_id": item.source_item_id,
            "url": item.url,
            "title": item.title,
            "text": item.text,
            "author_name": item.author_name,
            "author_profile_url": item.author_profile_url,
            "author_role": item.author_role,
            "organization_name": item.organization_name,
            "location": item.location,
            "created_at": item.created_at,
            "collected_at": item.collected_at,
            "engagement": item.engagement,
            "source_metadata": item.source_metadata,
        },
        **explanation,
    }
