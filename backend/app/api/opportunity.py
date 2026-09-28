"""
The single backend definition of the dashboard's opportunity metrics, shared
by the Overview endpoint (/api/stats/overview) and the All Signals list
(/api/posts). A KPI card and the Explorer view it drills into therefore
always count the same rows.

  Opportunity   current-version row with problem_evidence and
                final_score >= OPPORTUNITY_THRESHOLD
  New Today     an opportunity COLLECTED (inserted_at) since 00:00 today in
                REPORT_TZ
  RCM Relevant  current-version row with rcm_relevant
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.analysis.scoring_opportunity import OPPORTUNITY_THRESHOLD
from app.config import REPORT_TZ
from app.db.models import AnalysisResult, NormalizedItem
from app.schemas.analysis import ANALYSIS_VERSION


def join_condition():
    return (AnalysisResult.source_item_id == NormalizedItem.source_item_id) & (
        AnalysisResult.analysis_version == ANALYSIS_VERSION
    )


def base_query(db: Session, *, analyzed_only: bool = False):
    """normalized_items joined to their current-version analysis row. LEFT
    join by default so unanalyzed items stay visible in All Signals."""
    query = db.query(NormalizedItem, AnalysisResult)
    if analyzed_only:
        return query.join(AnalysisResult, join_condition())
    return query.outerjoin(AnalysisResult, join_condition())


def opportunity_clause():
    return and_(
        AnalysisResult.problem_evidence.is_(True),
        AnalysisResult.final_score >= OPPORTUNITY_THRESHOLD,
    )


def not_opportunity_clause():
    return or_(
        AnalysisResult.id.is_(None),
        AnalysisResult.problem_evidence.is_(False),
        AnalysisResult.final_score < OPPORTUNITY_THRESHOLD,
    )


def report_tz() -> ZoneInfo:
    return ZoneInfo(REPORT_TZ)


def to_utc(dt: datetime) -> datetime:
    """Query-parameter datetimes as UTC. Naive values are taken as UTC. The
    stored columns are UTC, and SQLite compares them as text without an
    offset, so every bound datetime must be UTC first."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def as_aware_utc(dt: datetime | None) -> datetime | None:
    """A stored value as aware UTC (SQLite returns them naive)."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def today_start(now: datetime | None = None) -> datetime:
    """00:00 today in REPORT_TZ, as an aware datetime in that zone."""
    tz = report_tz()
    local = (now or datetime.now(timezone.utc)).astimezone(tz)
    return local.replace(hour=0, minute=0, second=0, microsecond=0)


def definitions(now: datetime | None = None) -> dict:
    return {
        "opportunity_threshold": OPPORTUNITY_THRESHOLD,
        "opportunity_rule": f"problem_evidence and final_score >= {OPPORTUNITY_THRESHOLD:g}",
        "new_today_rule": "opportunity collected (inserted_at) since 00:00 today in report_tz",
        "rcm_relevant_rule": "rcm_relevant",
        "report_tz": REPORT_TZ,
        "today_start": today_start(now).isoformat(),
        "analysis_version": ANALYSIS_VERSION,
    }
