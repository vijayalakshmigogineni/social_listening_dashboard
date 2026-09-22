"""
Pipeline/debug endpoint -- exposes every stage's input/output for one
record, on demand (re-run, not stored -- analysis_results only holds the
merged final row per the fixed schema). This powers the developer-facing
Pipeline/Debug tab, never the CEO-facing views.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.analysis.pipeline import explain_pipeline
from app.db.base import get_db
from app.db.models import NormalizedItem

router = APIRouter()


@router.get("/{source}/{source_item_id}")
def explain(source: str, source_item_id: str, db: Session = Depends(get_db)):
    item = (
        db.query(NormalizedItem)
        .filter_by(source=source, source_item_id=source_item_id)
        .one_or_none()
    )
    if item is None:
        raise HTTPException(404, "post not found")

    matched_keywords = (item.source_metadata or {}).get("matched_rcm_keywords")
    explanation = explain_pipeline(
        title=item.title,
        text=item.text,
        created_at=item.created_at,
        matched_keywords=matched_keywords,
    )

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
