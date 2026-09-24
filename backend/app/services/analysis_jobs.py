"""
Analysis jobs: the dashboard's equivalent of `python scripts/run_pipeline.py`.

Same item selection and row writes as the script (app/analysis/runner.py):
posts not yet analyzed under every scoring version, v1 and v2 rows from one
pass. Two deliberate differences, both because this runs unattended behind a
progress bar: each post is committed on its own, so progress survives a
crash, and a post that raises is recorded as failed and skipped instead of
aborting the batch. A failed post stays unanalyzed, so the next run retries it.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.analysis.pipeline import STAGE_NAMES
from app.analysis.runner import analyze_item, select_items
from app.db.base import SessionLocal
from app.db.models import AnalysisJob
from app.services.jobs import as_utc, iso, live_stage, utcnow

MAX_STORED_ERRORS = 50


def pending_count(db: Session, source: str | None = None) -> int:
    items, _ = select_items(db, source=source)
    return len(items)


def create_job(db: Session, source: str | None = None, collection_job_id: int | None = None) -> AnalysisJob:
    job = AnalysisJob(
        source=source,
        collection_job_id=collection_job_id,
        status="queued",
        errors=[],
        scores={"v1": [], "v2": []},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _stage_label(number: int) -> str:
    return f"Step {number}/{len(STAGE_NAMES)} — {STAGE_NAMES[number - 1]}"


def run_job(job_id: int, session_factory=SessionLocal) -> None:
    db = session_factory()
    try:
        job = db.get(AnalysisJob, job_id)
        items, _ = select_items(db, source=job.source)
        job.status = "running"
        job.started_at = utcnow()
        job.total_posts = len(items)
        db.commit()

        processed = failed = 0
        errors: list[str] = []
        scores: dict[str, list[float]] = {"v1": [], "v2": []}

        def on_stage(number: int) -> None:
            live_stage[job_id] = (number, _stage_label(number))

        for item in items:
            label = f"{item.source}:{item.source_item_id}"
            try:
                results = analyze_item(db, item, on_stage=on_stage)
                db.commit()
            except Exception as exc:
                db.rollback()
                failed += 1
                if len(errors) < MAX_STORED_ERRORS:
                    errors.append(f"{label}: {type(exc).__name__}: {exc}")
            else:
                processed += 1
                for r in results:
                    key = "v2" if r.scoring_version.endswith("v2") else "v1"
                    scores[key].append(round(r.final_score, 2))

            job = db.get(AnalysisJob, job_id)
            job.processed_posts = processed
            job.failed_posts = failed
            job.current_stage = live_stage.get(job_id, (None, None))[1]
            job.errors = list(errors)
            job.scores = {k: list(v) for k, v in scores.items()}
            db.commit()

        job.current_stage = None
        if failed == 0:
            job.status = "completed"
        elif processed == 0:
            job.status = "failed"
        else:
            job.status = "completed_with_errors"
        job.completed_at = utcnow()
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(AnalysisJob, job_id)
        if job is not None:
            job.status = "failed"
            job.errors = [*(job.errors or []), f"Analysis job crashed: {exc}"]
            job.completed_at = utcnow()
            db.commit()
        raise
    finally:
        live_stage.pop(job_id, None)
        db.close()


def to_dict(job: AnalysisJob) -> dict[str, Any]:
    started, completed = as_utc(job.started_at), as_utc(job.completed_at)
    stage_number, stage = None, job.current_stage
    if job.status == "running" and job.id in live_stage:
        stage_number, stage = live_stage[job.id]
    return {
        "id": job.id,
        "source": job.source,
        "collection_job_id": job.collection_job_id,
        "status": job.status,
        "total_posts": job.total_posts,
        "processed_posts": job.processed_posts,
        "failed_posts": job.failed_posts,
        "current_stage": stage,
        "current_stage_number": stage_number,
        "stages": list(STAGE_NAMES),
        "errors": job.errors,
        "scores": job.scores,
        "created_at": iso(job.created_at),
        "started_at": iso(started),
        "completed_at": iso(completed),
        "duration_s": round((completed - started).total_seconds(), 1) if started and completed else None,
    }
