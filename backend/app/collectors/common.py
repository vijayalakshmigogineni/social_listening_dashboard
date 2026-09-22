"""Shared helpers for turning normalized dicts into stored rows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from dateutil import parser as dateutil_parser
from sqlalchemy.orm import Session

from app.db.models import NormalizedItem as NormalizedItemRow
from app.schemas.normalized import NormalizedItem, validate_no_analysis_fields


def parse_datetime(value: Any) -> datetime | None:
    """Best-effort parse of whatever a source/scraper hands back for a timestamp."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        # epoch seconds vs. milliseconds
        ts = value / 1000 if value > 1e12 else value
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(value, str):
        try:
            dt = dateutil_parser.parse(value)
        except (ValueError, OverflowError):
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    return None


def upsert_normalized_items(db: Session, records: list[dict[str, Any]]) -> dict[str, int]:
    """
    Validate each record against the canonical schema, then insert or update
    it keyed on (source, source_item_id). Returns counts for a run summary.
    """
    inserted = 0
    updated = 0
    skipped = 0

    for raw_record in records:
        validate_no_analysis_fields(raw_record)
        try:
            item = NormalizedItem(**raw_record)
        except Exception as exc:  # pydantic ValidationError etc.
            print(f"  ! skipping invalid record ({raw_record.get('source_item_id')}): {exc}")
            skipped += 1
            continue

        existing = (
            db.query(NormalizedItemRow)
            .filter_by(source=item.source, source_item_id=item.source_item_id)
            .one_or_none()
        )

        payload = item.model_dump()

        if existing is None:
            db.add(NormalizedItemRow(**payload))
            inserted += 1
        else:
            for field, value in payload.items():
                setattr(existing, field, value)
            updated += 1

    db.commit()
    return {"inserted": inserted, "updated": updated, "skipped": skipped}
