"""
Batch runner around the pipeline: which items still need analysis, and how one
item's results are written to analysis_results. Shared by scripts/run_pipeline.py
and the dashboard's analysis job so both select and store rows identically.

Each item produces one v3 row (unique key: source_item_id + analysis_version).
Replies get their parent post's text as context.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.analysis.pipeline import StageCallback, build_text, run_pipeline
from app.db.models import AnalysisResult as AnalysisResultRow
from app.db.models import NormalizedItem
from app.schemas.analysis import ANALYSIS_VERSION_V3, AnalysisResult

ALL_VERSIONS = (ANALYSIS_VERSION_V3,)


def select_items(
    db: Session, source: str | None = None, force: bool = False
) -> tuple[list[NormalizedItem], int]:
    """(items to analyze, number skipped as already analyzed).

    An item counts as done once every version in ALL_VERSIONS has a row, so
    adding a new scoring version later backfills it without --force.
    """
    query = db.query(NormalizedItem)
    if source:
        query = query.filter_by(source=source)
    items = query.all()
    if force:
        return items, 0

    seen: dict[str, set[str]] = {}
    for sid, ver in db.query(
        AnalysisResultRow.source_item_id, AnalysisResultRow.analysis_version
    ).all():
        seen.setdefault(sid, set()).add(ver)
    already_done = {sid for sid, vers in seen.items() if set(ALL_VERSIONS) <= vers}

    todo = [item for item in items if item.source_item_id not in already_done]
    return todo, len(items) - len(todo)


def resolve_parent_text(db: Session, source: str, parent_id: str | None) -> str | None:
    """The parent post's text for a reply, as context for the semantic stage.

    NormalizedItem stores only parent_id; the parent is looked up among the
    same source's collected rows. None when the item is not a reply or its
    parent was never collected.
    """
    if not parent_id:
        return None
    parent = (
        db.query(NormalizedItem)
        .filter_by(source=source, source_item_id=parent_id)
        .one_or_none()
    )
    if parent is None:
        return None
    return build_text(parent.title, parent.text) or None


def analyze_item(
    db: Session, item: NormalizedItem, on_stage: StageCallback = None
) -> AnalysisResult:
    """Run the pipeline for one item and add/update its row. Does not commit."""
    result = run_pipeline(
        source_item_id=item.source_item_id,
        title=item.title,
        text=item.text,
        created_at=item.created_at,
        matched_keywords=(item.source_metadata or {}).get("matched_rcm_keywords"),
        on_stage=on_stage,
        parent_text=resolve_parent_text(db, item.source, item.parent_id),
        source=item.source,
    )
    existing = (
        db.query(AnalysisResultRow)
        .filter_by(source_item_id=result.source_item_id, analysis_version=result.analysis_version)
        .one_or_none()
    )
    payload = result.model_dump(exclude={"created_at", "updated_at"})
    if existing is None:
        db.add(AnalysisResultRow(**payload))
    else:
        for field, value in payload.items():
            setattr(existing, field, value)
    return result
