"""
Data Collection endpoints -- start a collection job from the dashboard and
poll it, edit which units (subreddits, forums, groups, ...) each source
collects, and read live per-source stats. The collectors and their
credentials stay server-side; the browser only picks a mode, sources, limits
and unit lists.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.opportunity import as_aware_utc, join_condition, opportunity_clause, report_tz
from app.db.base import get_db
from app.db.models import AnalysisResult, CollectionJob, NormalizedItem
from app.services import collection_jobs, jobs, source_settings
from app.services.collection_sources import ADAPTERS, MAX_POST_LIMIT

STATS_DAYS = 14  # sparkline window: posts collected per day

router = APIRouter()


class CollectionJobCreate(BaseModel):
    mode: Literal["since_last_sweep", "custom_range", "latest_n"]
    # Omitted or empty = all sources.
    sources: Optional[list[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    # Per source. Required for custom_range and latest_n, ignored for since_last_sweep.
    post_limit: Optional[int] = Field(None, ge=1, le=MAX_POST_LIMIT)

    @model_validator(mode="after")
    def _check_mode_fields(self):
        if self.mode in ("custom_range", "latest_n") and self.post_limit is None:
            raise ValueError("post_limit is required for this mode")
        if self.mode == "custom_range":
            if self.start_date is None or self.end_date is None:
                raise ValueError("start_date and end_date are required for custom_range")
            self.start_date = _utc(self.start_date)
            self.end_date = _utc(self.end_date)
            if self.start_date >= self.end_date:
                raise ValueError("start_date must be before end_date")
            if self.start_date >= datetime.now(timezone.utc):
                raise ValueError("start_date is in the future")
        else:
            self.start_date = self.end_date = None
        if self.mode == "since_last_sweep":
            self.post_limit = None
        return self


def _utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _resolve_sources(sources: list[str] | None) -> list[str]:
    if not sources:
        return list(ADAPTERS)
    unknown = sorted(set(sources) - set(ADAPTERS))
    if unknown:
        raise HTTPException(400, f"unknown source(s) {unknown}; expected some of {list(ADAPTERS)}")
    return [s for s in ADAPTERS if s in sources]  # stable display order, no repeats


def _start(db: Session, mode, sources, start_date, end_date, post_limit, retry_of=None) -> dict:
    source_settings.refresh(db)  # collect exactly the units the page last saved
    created: dict = {}

    def create() -> int:
        job = collection_jobs.create_job(db, mode, sources, start_date, end_date, post_limit, retry_of)
        created["job"] = job
        return job.id

    try:
        jobs.start_job("collection", create, collection_jobs.run_job)
    except jobs.JobConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    return collection_jobs.to_dict(created["job"])


@router.get("/sources")
def list_sources(db: Session = Depends(get_db)):
    source_settings.refresh(db)
    checkpoints = collection_jobs.list_checkpoints(db)
    return {
        "max_post_limit": MAX_POST_LIMIT,
        "sources": [{**a.describe(), "checkpoint": checkpoints[k]} for k, a in ADAPTERS.items()],
        "active_job": jobs.active_job(),
    }


@router.post("/jobs", status_code=202)
def create_job(body: CollectionJobCreate, db: Session = Depends(get_db)):
    sources = _resolve_sources(body.sources)
    return _start(db, body.mode, sources, body.start_date, body.end_date, body.post_limit)


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db), limit: int = Query(20, ge=1, le=100)):
    rows = db.query(CollectionJob).order_by(CollectionJob.id.desc()).limit(limit).all()
    return {"results": [collection_jobs.to_dict(j) for j in rows]}


@router.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(CollectionJob, job_id)
    if job is None:
        raise HTTPException(404, "collection job not found")
    return collection_jobs.to_dict(job)


@router.post("/jobs/{job_id}/retry", status_code=202)
def retry_job(job_id: int, db: Session = Depends(get_db)):
    """Re-run only the sources that failed (or partly failed) in a finished job,
    with the same mode and parameters. For Since Last Sweep those sources' windows
    start from the same checkpoint again, since a failure never advances it."""
    job = db.get(CollectionJob, job_id)
    if job is None:
        raise HTTPException(404, "collection job not found")
    if job.status in jobs.RUNNING_STATUSES:
        raise HTTPException(409, "job is still running")
    sources = collection_jobs.failed_sources(job)
    if not sources:
        raise HTTPException(400, "job has no failed sources to retry")
    return _start(db, job.mode, sources, job.start_date, job.end_date, job.post_limit, retry_of=job.id)


class UnitIn(BaseModel):
    name: str = ""
    value: str


class UnitsUpdate(BaseModel):
    units: list[UnitIn]


def _editable(db: Session, key: str):
    if key not in ADAPTERS:
        raise HTTPException(404, f"unknown source {key!r}")
    if jobs.active_job() is not None:
        raise HTTPException(409, "a job is running; edit sources after it finishes")
    return ADAPTERS[key]


@router.put("/sources/{key}/units")
def save_units(key: str, body: UnitsUpdate, db: Session = Depends(get_db)):
    """Replace the units this source collects. Takes effect from the next job."""
    adapter = _editable(db, key)
    try:
        source_settings.save(db, key, [u.model_dump() for u in body.units])
    except source_settings.InvalidUnits as exc:
        raise HTTPException(400, str(exc)) from exc
    return {**adapter.describe(), "checkpoint": collection_jobs.list_checkpoints(db)[key]}


@router.delete("/sources/{key}/units")
def reset_units(key: str, db: Session = Depends(get_db)):
    """Back to the collector's in-code default list."""
    adapter = _editable(db, key)
    source_settings.reset(db, key)
    return {**adapter.describe(), "checkpoint": collection_jobs.list_checkpoints(db)[key]}


@router.get("/source-stats")
def source_stats(db: Session = Depends(get_db)):
    """Live per-source numbers for the source cards: what each source holds,
    how much of it is analyzed / RCM relevant / an opportunity (same
    definitions as the Overview), when it last brought posts in, and posts
    collected per day over the last STATS_DAYS days (REPORT_TZ)."""
    posts = dict(db.query(NormalizedItem.source, func.count(NormalizedItem.id))
                 .group_by(NormalizedItem.source).all())
    newest = dict(db.query(NormalizedItem.source, func.max(NormalizedItem.created_at))
                  .group_by(NormalizedItem.source).all())
    last = dict(db.query(NormalizedItem.source, func.max(NormalizedItem.inserted_at))
                .group_by(NormalizedItem.source).all())
    analyzed_q = db.query(NormalizedItem.source, func.count(AnalysisResult.id)).join(
        AnalysisResult, join_condition()).group_by(NormalizedItem.source)
    analyzed = dict(analyzed_q.all())
    relevant = dict(analyzed_q.filter(AnalysisResult.rcm_relevant.is_(True)).all())
    opportunities = dict(analyzed_q.filter(opportunity_clause()).all())

    tz = report_tz()
    today = datetime.now(timezone.utc).astimezone(tz).date()
    first_day = today - timedelta(days=STATS_DAYS - 1)
    since = datetime(first_day.year, first_day.month, first_day.day, tzinfo=tz).astimezone(timezone.utc)
    daily: dict[str, Counter] = {}
    for source, inserted in (db.query(NormalizedItem.source, NormalizedItem.inserted_at)
                             .filter(NormalizedItem.inserted_at >= since).all()):
        daily.setdefault(source, Counter())[as_aware_utc(inserted).astimezone(tz).date()] += 1
    days = [first_day + timedelta(days=i) for i in range(STATS_DAYS)]

    def iso(dt):
        return as_aware_utc(dt).isoformat() if dt else None

    return {
        "days": [d.isoformat() for d in days],
        "sources": {
            key: {
                "posts": posts.get(key, 0),
                "analyzed": analyzed.get(key, 0),
                "pending": posts.get(key, 0) - analyzed.get(key, 0),
                "rcm_relevant": relevant.get(key, 0),
                "opportunities": opportunities.get(key, 0),
                "last_collected_at": iso(last.get(key)),
                "newest_post_at": iso(newest.get(key)),
                "collected_per_day": [daily.get(key, Counter()).get(d, 0) for d in days],
            }
            for key in sorted(set(posts) | set(ADAPTERS))
        },
    }
