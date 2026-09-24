"""
Analysis job endpoints -- run the existing pipeline (the same code path as
scripts/run_pipeline.py) over posts not yet analyzed, from the dashboard.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import AnalysisJob
from app.services import analysis_jobs, jobs

router = APIRouter()


class AnalysisJobCreate(BaseModel):
    source: Optional[str] = None  # None = all sources
    collection_job_id: Optional[int] = None  # the collection this run follows, for history


@router.get("/pending")
def pending(db: Session = Depends(get_db), source: Optional[str] = Query(None)):
    return {"pending_posts": analysis_jobs.pending_count(db, source), "active_job": jobs.active_job()}


@router.post("/jobs", status_code=202)
def create_job(body: AnalysisJobCreate, db: Session = Depends(get_db)):
    created: dict = {}

    def create() -> int:
        job = analysis_jobs.create_job(db, body.source, body.collection_job_id)
        created["job"] = job
        return job.id

    try:
        jobs.start_job("analysis", create, analysis_jobs.run_job)
    except jobs.JobConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    return analysis_jobs.to_dict(created["job"])


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db), limit: int = Query(10, ge=1, le=100)):
    rows = db.query(AnalysisJob).order_by(AnalysisJob.id.desc()).limit(limit).all()
    return {"results": [analysis_jobs.to_dict(j) for j in rows]}


@router.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(AnalysisJob, job_id)
    if job is None:
        raise HTTPException(404, "analysis job not found")
    return analysis_jobs.to_dict(job)
