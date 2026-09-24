"""
Collection jobs: fetch posts from one or more sources and store them through
the existing upsert (collectors/common.py), which is also the deduplication --
a post already in normalized_items is updated in place and counted as a
duplicate, never inserted twice.

Since Last Sweep works off collection_checkpoints: per source, the end of the
window its last fully successful sweep covered. The next sweep fetches
(checkpoint, now]. A source whose sweep had any error keeps its old
checkpoint, so the next sweep re-covers the same window (the upsert makes the
overlap harmless). Latest N and Custom Range are ad-hoc pulls that do not
promise to cover every post since the checkpoint, so they never move it.
"""

from __future__ import annotations

import copy
import json
import re
from datetime import timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.collectors.common import upsert_normalized_items
from app.db.base import SessionLocal
from app.db.models import CollectionCheckpoint, CollectionJob, NormalizedItem
from app.services.collection_sources import ADAPTERS, FetchPlan, SourceAdapter, post_time
from app.services.jobs import as_utc, iso, utcnow

MODES = ("since_last_sweep", "custom_range", "latest_n")
BOOTSTRAP_LOOKBACK = timedelta(days=7)


def checkpoint_for(db: Session, source: str) -> tuple[Any, str]:
    """(start of the next sweep window, where that value came from)."""
    row = db.get(CollectionCheckpoint, source)
    if row is not None:
        return as_utc(row.last_successful_fetch), "checkpoint"

    # No sweep yet (data so far came from the terminal scripts): start from the
    # newest stored post, so the first sweep does not re-pull the whole history.
    newest = (
        db.query(func.max(NormalizedItem.created_at)).filter_by(source=source).scalar()
        or db.query(func.max(NormalizedItem.collected_at)).filter_by(source=source).scalar()
    )
    if newest is not None:
        return as_utc(newest), "newest_stored_post"
    return utcnow() - BOOTSTRAP_LOOKBACK, "default_lookback"


def list_checkpoints(db: Session, adapters: dict[str, SourceAdapter] = ADAPTERS) -> dict[str, dict]:
    out = {}
    for key in adapters:
        row = db.get(CollectionCheckpoint, key)
        start, origin = checkpoint_for(db, key)
        out[key] = {
            "last_successful_fetch": iso(row.last_successful_fetch) if row else None,
            "last_job_id": row.last_job_id if row else None,
            "next_sweep_from": iso(start),
            "next_sweep_from_origin": origin,
        }
    return out


def create_job(
    db: Session,
    mode: str,
    sources: list[str],
    start_date=None,
    end_date=None,
    post_limit: int | None = None,
    retry_of: int | None = None,
) -> CollectionJob:
    job = CollectionJob(
        mode=mode,
        sources=sources,
        start_date=start_date,
        end_date=end_date,
        post_limit=post_limit if mode != "since_last_sweep" else None,
        status="queued",
        source_results={s: _blank_result() for s in sources},
        errors=[],
        retry_of=retry_of,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _blank_result() -> dict[str, Any]:
    return {
        "status": "waiting",
        "fetched": 0,
        "new": 0,
        "duplicate": 0,
        "skipped": 0,
        "units_total": 0,
        "units_done": 0,
        "current_unit": None,
        "window_start": None,
        "window_end": None,
        "window_origin": None,
        "depth_per_unit": None,
        "errors": [],
        "warnings": [],
        "checkpoint_advanced": False,
        "started_at": None,
        "completed_at": None,
    }


def _plan_for(db: Session, job: CollectionJob, source: str, now) -> tuple[FetchPlan, str | None]:
    if job.mode == "since_last_sweep":
        start, origin = checkpoint_for(db, source)
        return FetchPlan(job.mode, window_start=start, window_end=now), origin
    if job.mode == "custom_range":
        end = min(as_utc(job.end_date), now)
        return FetchPlan(job.mode, as_utc(job.start_date), end, job.post_limit), "custom"
    return FetchPlan(job.mode, limit=job.post_limit), None


def _drop_id_collisions(db: Session, source: str, records: list[dict]) -> tuple[list[dict], int]:
    """analysis_results is keyed on source_item_id alone, so a post must not
    reuse an id another source already owns (same guard as collect_x.py)."""
    ids = [r["source_item_id"] for r in records]
    if not ids:
        return records, 0
    taken = {
        sid
        for (sid,) in db.query(NormalizedItem.source_item_id)
        .filter(NormalizedItem.source_item_id.in_(ids), NormalizedItem.source != source)
        .all()
    }
    kept = [r for r in records if r["source_item_id"] not in taken]
    return kept, len(records) - len(kept)


def readable_error(exc: Exception) -> str:
    """Apify errors embed the API's JSON body; keep just its message."""
    text = str(exc)
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        try:
            err = json.loads(match.group(0)).get("error") or {}
        except (ValueError, AttributeError):
            err = {}
        if isinstance(err, dict) and err.get("message"):
            prefix = text[: match.start()].rstrip(": ")
            return f"{prefix}: {err['message']}" if prefix else err["message"]
    return text


def _plural(word: str) -> str:
    return f"{word[:-1]}ies" if word.endswith("y") else f"{word}s"


def _group_unit_errors(unit_errors: list[tuple[str, str]], total_units: int, unit_label: str) -> list[str]:
    """One line per distinct error, naming the units it hit, instead of the
    same message repeated for every subreddit/forum/group."""
    by_message: dict[str, list[str]] = {}
    for name, message in unit_errors:
        by_message.setdefault(message, []).append(name)
    lines = []
    for message, names in by_message.items():
        if len(names) == total_units and total_units > 1:
            where = f"All {total_units} {_plural(unit_label)}"
        elif len(names) > 3:
            where = f"{', '.join(names[:3])} and {len(names) - 3} more"
        else:
            where = ", ".join(names)
        lines.append(f"{where}: {message}")
    return lines


def _collect_source(db, job, source, adapters, now, save) -> dict[str, Any]:
    res = copy.deepcopy(job.source_results[source])
    res.update(status="fetching", started_at=iso(utcnow()))

    adapter = adapters.get(source)
    if adapter is None:
        res.update(status="failed", errors=[f"Unknown source '{source}'"], completed_at=iso(utcnow()))
        return res
    reason = adapter.unavailable_reason()
    if reason:
        res.update(status="failed", errors=[reason], completed_at=iso(utcnow()))
        return res

    plan, origin = _plan_for(db, job, source, now)
    depth = adapter.depth_for(plan)
    units = adapter.units()
    res.update(
        window_start=iso(plan.window_start),
        window_end=iso(plan.window_end),
        window_origin=origin,
        depth_per_unit=depth,
        units_total=len(units),
    )
    save(source, res)

    if plan.window_start and plan.window_end and plan.window_start >= plan.window_end:
        res["warnings"].append("The date window is empty; nothing to fetch.")
        units = {}

    by_unit: dict[str, list[dict]] = {}
    unit_errors: list[tuple[str, str]] = []
    for name, arg in units.items():
        res["current_unit"] = name
        save(source, res)
        try:
            fetched = adapter.fetch_unit(name, arg, depth, plan)
        except Exception as exc:
            unit_errors.append((name, readable_error(exc)))
            res["errors"] = _group_unit_errors(unit_errors, len(units), adapter.unit_label)
        else:
            by_unit[name] = fetched.records
            if fetched.depth_reached and plan.window_start:
                times = [t for t in map(post_time, fetched.records) if t]
                if times and min(times) > plan.window_start:
                    res["warnings"].append(
                        f"{name}: reached the fetch depth ({depth} per {adapter.unit_label}) "
                        "before the start of the window; older posts may be missing."
                    )
        res["units_done"] += 1
        save(source, res)
    res["current_unit"] = None

    if units and not by_unit:
        res.update(status="failed", completed_at=iso(utcnow()))
        return res

    try:
        records = adapter.select(by_unit, plan)
        records, collisions = _drop_id_collisions(db, source, records)
        if collisions:
            res["warnings"].append(f"{collisions} post(s) skipped: id already used by another source.")
        summary = upsert_normalized_items(db, records)
    except Exception as exc:
        db.rollback()
        res["errors"].append(f"Storing posts failed: {readable_error(exc)}")
        res.update(status="failed", completed_at=iso(utcnow()))
        return res

    res.update(
        fetched=len(records),
        new=summary["inserted"],
        duplicate=summary["updated"],
        skipped=summary["skipped"] + collisions,
        status="partial" if res["errors"] else "completed",
    )

    if job.mode == "since_last_sweep" and not res["errors"]:
        row = db.get(CollectionCheckpoint, source) or CollectionCheckpoint(source=source)
        previous = as_utc(row.last_successful_fetch)
        if previous is None or plan.window_end > previous:
            row.last_successful_fetch = plan.window_end
            row.last_job_id = job.id
            db.add(row)
            db.commit()
            res["checkpoint_advanced"] = True

    res["completed_at"] = iso(utcnow())
    return res


def run_job(job_id: int, session_factory=SessionLocal, adapters: dict[str, SourceAdapter] = ADAPTERS) -> None:
    db = session_factory()
    try:
        job = db.get(CollectionJob, job_id)
        now = utcnow()
        job.status = "running"
        job.started_at = now
        db.commit()

        results = copy.deepcopy(job.source_results)

        def save(source: str, res: dict[str, Any]) -> None:
            results[source] = copy.deepcopy(res)
            job.source_results = copy.deepcopy(results)
            db.commit()

        for source in job.sources:
            try:
                res = _collect_source(db, job, source, adapters, now, save)
            except Exception as exc:  # anything the per-unit handling did not catch
                db.rollback()
                res = {**results[source], "status": "failed", "errors": [readable_error(exc)],
                       "completed_at": iso(utcnow())}
            save(source, res)

        statuses = [results[s]["status"] for s in job.sources]
        job.posts_fetched = sum(results[s]["fetched"] for s in job.sources)
        job.posts_new = sum(results[s]["new"] for s in job.sources)
        job.posts_duplicate = sum(results[s]["duplicate"] for s in job.sources)
        job.posts_skipped = sum(results[s]["skipped"] for s in job.sources)
        job.errors = [
            f"{adapters[s].label if s in adapters else s}: {e}"
            for s in job.sources
            for e in results[s]["errors"]
        ]
        if all(st == "completed" for st in statuses):
            job.status = "completed"
        elif all(st == "failed" for st in statuses):
            job.status = "failed"
        else:
            job.status = "completed_with_errors"
        job.completed_at = utcnow()
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(CollectionJob, job_id)
        if job is not None:
            job.status = "failed"
            job.errors = [*(job.errors or []), f"Collection job crashed: {exc}"]
            job.completed_at = utcnow()
            db.commit()
        raise
    finally:
        db.close()


def failed_sources(job: CollectionJob) -> list[str]:
    return [s for s, r in (job.source_results or {}).items() if r.get("status") in ("failed", "partial")]


def to_dict(job: CollectionJob, adapters: dict[str, SourceAdapter] = ADAPTERS) -> dict[str, Any]:
    started, completed = as_utc(job.started_at), as_utc(job.completed_at)
    return {
        "id": job.id,
        "mode": job.mode,
        "sources": job.sources,
        "start_date": iso(job.start_date),
        "end_date": iso(job.end_date),
        "post_limit": job.post_limit,
        "status": job.status,
        "posts_fetched": job.posts_fetched,
        "posts_new": job.posts_new,
        "posts_duplicate": job.posts_duplicate,
        "posts_skipped": job.posts_skipped,
        "source_results": job.source_results,
        "errors": job.errors,
        "retry_of": job.retry_of,
        "retryable_sources": failed_sources(job) if job.status not in ("queued", "running") else [],
        "created_at": iso(job.created_at),
        "started_at": iso(started),
        "completed_at": iso(completed),
        "duration_s": round((completed - started).total_seconds(), 1) if started and completed else None,
    }
