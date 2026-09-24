"""
Minimal background-job runner for dashboard-started collection and analysis.

One job at a time, in a daemon thread of the API process: collection spends
Apify credits and analysis holds the zero-shot model, and both write to the
same SQLite file, so running them concurrently buys nothing but lock
contention. Job state lives in the collection_jobs / analysis_jobs rows (the
UI polls them); only the analysis job's current pipeline stage, which changes
several times per post, is kept in memory instead of committed.
"""

from __future__ import annotations

import threading
import traceback
from datetime import datetime, timezone
from typing import Callable

from app.db.base import SessionLocal
from app.db.models import AnalysisJob, CollectionJob

RUNNING_STATUSES = ("queued", "running")

_lock = threading.Lock()
_active: dict | None = None  # {"kind": "collection", "id": 3}

# analysis job id -> (stage number, stage name) for the post being analyzed
live_stage: dict[int, tuple[int, str]] = {}


class JobConflict(RuntimeError):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime | None) -> datetime | None:
    """SQLite hands DateTime(timezone=True) columns back naive; they were stored as UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def iso(dt: datetime | None) -> str | None:
    dt = as_utc(dt)
    return dt.isoformat() if dt else None


def active_job() -> dict | None:
    with _lock:
        return dict(_active) if _active else None


def start_job(kind: str, create: Callable[[], int], run: Callable[[int], None]) -> int:
    """Reserve the single job slot, create the job row, then run it in a thread.

    The slot is taken before the row exists so a refused request never leaves
    an orphaned "queued" job behind."""
    global _active
    with _lock:
        if _active:
            raise JobConflict(
                f"A {_active['kind']} job (#{_active['id']}) is still running. "
                "Wait for it to finish before starting another."
            )
        _active = {"kind": kind, "id": None}

    try:
        job_id = create()
    except Exception:
        with _lock:
            _active = None
        raise

    with _lock:
        _active = {"kind": kind, "id": job_id}

    def worker():
        global _active
        try:
            run(job_id)
        except Exception:  # run() records its own failures; this is a last resort
            traceback.print_exc()
        finally:
            with _lock:
                _active = None

    threading.Thread(target=worker, name=f"{kind}-job-{job_id}", daemon=True).start()
    return job_id


def mark_interrupted_jobs(session_factory=SessionLocal) -> None:
    """At startup: a job still marked queued/running died with the previous
    server process (restart, --reload). Say so instead of showing it as live."""
    db = session_factory()
    try:
        for model in (CollectionJob, AnalysisJob):
            for job in db.query(model).filter(model.status.in_(RUNNING_STATUSES)).all():
                job.status = "interrupted"
                job.completed_at = utcnow()
                job.errors = [*(job.errors or []), "The server restarted while this job was running."]
        db.commit()
    finally:
        db.close()
