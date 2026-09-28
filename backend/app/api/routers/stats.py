"""Overview endpoint -- every number on the Overview page, computed here.

KPIs, chart series and the Top 3 all use the definitions in
app/api/opportunity.py, which /api/posts uses too, so a card or chart bar
drills into an All Signals view with exactly the same count. Each chart
bucket carries the /api/posts filter that reproduces it (`filter`).

Chart series count opportunities. Aggregation runs in Python over the
opportunity rows: dialect-neutral (SQLite and PostgreSQL) and cheap at this
data size.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.opportunity import (
    as_aware_utc,
    base_query,
    definitions,
    opportunity_clause,
    report_tz,
    today_start,
)
from app.api.routers.posts import _row_to_dict
from app.db.base import get_db
from app.db.models import AnalysisResult, NormalizedItem

router = APIRouter()

TOP_N = 3
# Opportunities Over Time shows the most recent window ending at the current
# period; older opportunities (forum threads can be years old) are counted in
# `earlier` rather than stretching the axis.
WINDOW = {"day": 30, "week": 26, "month": 12}


def _bucket_start(day: date, bucket: str) -> date:
    if bucket == "week":
        return day - timedelta(days=day.weekday())  # Monday
    if bucket == "month":
        return day.replace(day=1)
    return day


def _next_bucket(start: date, bucket: str) -> date:
    if bucket == "week":
        return start + timedelta(days=7)
    if bucket == "month":
        return (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start + timedelta(days=1)


def _window_start(last: date, bucket: str) -> date:
    start = last
    for _ in range(WINDOW[bucket] - 1):
        start = _bucket_start(start - timedelta(days=1), bucket)
    return start


def _over_time(created: list[datetime], bucket: str) -> tuple[list[dict], int]:
    """(zero-filled buckets for the WINDOW ending at the current period,
    opportunities dated before it), cut in REPORT_TZ. Each bucket's filter is
    its inclusive created_at range."""
    tz = report_tz()
    counts = Counter(_bucket_start(dt.astimezone(tz).date(), bucket) for dt in created)
    last = max([_bucket_start(today_start().date(), bucket), *counts])
    start = _window_start(last, bucket)
    earlier = sum(n for key, n in counts.items() if key < start)
    series = []
    while start <= last:
        nxt = _next_bucket(start, bucket)
        date_from = datetime(start.year, start.month, start.day, tzinfo=tz)
        date_to = datetime(nxt.year, nxt.month, nxt.day, tzinfo=tz) - timedelta(microseconds=1)
        series.append({
            "key": start.isoformat(),
            "count": counts.get(start, 0),
            "filter": {"opportunity": True, "date_from": date_from.isoformat(),
                       "date_to": date_to.isoformat()},
        })
        start = nxt
    return series, earlier


def _ranked(counter: Counter, filter_key: str) -> list[dict]:
    return [
        {"key": key, "count": n, "filter": {"opportunity": True, filter_key: key}}
        for key, n in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


@router.get("/overview")
def overview(
    db: Session = Depends(get_db),
    bucket: str = Query("month", pattern="^(day|week|month)$",
                        description="Opportunities Over Time bucket size"),
):
    opportunities = base_query(db, analyzed_only=True).filter(opportunity_clause())
    start_today = today_start()

    total_opportunities = opportunities.count()
    new_today = opportunities.filter(
        NormalizedItem.inserted_at >= as_aware_utc(start_today)
    ).count()
    rcm_relevant = base_query(db, analyzed_only=True).filter(
        AnalysisResult.rcm_relevant.is_(True)
    ).count()

    rows = opportunities.with_entities(
        NormalizedItem.source,
        NormalizedItem.created_at,
        AnalysisResult.problem_category,
        AnalysisResult.seeking_level,
    ).all()

    categories: Counter = Counter()
    for _, _, cats, _ in rows:
        categories.update(set(cats or []))
    created = [as_aware_utc(c) for _, c, _, _ in rows if c is not None]

    top = opportunities.order_by(AnalysisResult.final_score.desc()).limit(TOP_N).all()
    points, earlier = _over_time(created, bucket)

    return {
        "kpis": {
            "total_opportunities": {"value": total_opportunities, "filter": {"opportunity": True}},
            "new_today": {"value": new_today, "filter": {
                "opportunity": True, "collected_from": start_today.isoformat()}},
            "rcm_relevant": {"value": rcm_relevant, "filter": {"rcm_relevant": True}},
        },
        "series": {
            "opportunities_over_time": {
                "bucket": bucket,
                "points": points,
                "earlier": earlier,
                "undated": len(rows) - len(created),
            },
            "problem_category": _ranked(categories, "problem_category"),
            "source_contribution": _ranked(Counter(s for s, _, _, _ in rows), "source"),
            "seeking_level": _ranked(Counter(lvl or "none" for _, _, _, lvl in rows), "seeking_level"),
        },
        "top": [_row_to_dict(item, analysis) for item, analysis in top],
        "definitions": definitions(),
    }
