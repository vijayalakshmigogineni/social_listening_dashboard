"""
Dashboard analysis jobs and the collection/analysis API. The pipeline itself
is stubbed (its behaviour is covered by the step tests); these tests check
selection, per-post failure handling, progress and the stage hook. Isolated
in-memory DB only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.analysis import pipeline as pipeline_module
from app.analysis import runner, step1_relevance
from app.collectors.common import upsert_normalized_items
from app.db import models
from app.db.base import Base, get_db
from app.services import analysis_jobs, jobs
from tests.test_collection_jobs import _record


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _fake_pipeline(fail_ids=()):
    real = pipeline_module.run_pipeline_all_versions

    def fake(source_item_id, title, text, created_at, matched_keywords=None, on_stage=None, **kwargs):
        if source_item_id in fail_ids:
            raise RuntimeError("model exploded")
        # Short-circuit path of the real pipeline: zero keyword hits, resolved
        # as not relevant by a stubbed LLM, so no model is loaded.
        with patch.object(step1_relevance, "classify_relevance_llm",
                          return_value={"relevant": False, "confidence": 0.9}):
            return real(source_item_id, "", "I love hiking on weekends.", created_at, [], on_stage)

    return fake


def _seed(session_factory, ids):
    db = session_factory()
    upsert_normalized_items(db, [_record("reddit", sid, 1) for sid in ids])
    db.close()


def _run(session_factory):
    db = session_factory()
    job_id = analysis_jobs.create_job(db).id
    db.close()
    analysis_jobs.run_job(job_id, session_factory=session_factory)
    db = session_factory()
    try:
        return analysis_jobs.to_dict(db.get(models.AnalysisJob, job_id))
    finally:
        db.close()


def test_analysis_job_scores_pending_posts_and_skips_done(session_factory, monkeypatch):
    monkeypatch.setattr(runner, "run_pipeline_all_versions", _fake_pipeline())
    _seed(session_factory, ["a", "b"])

    job = _run(session_factory)
    assert job["status"] == "completed"
    assert (job["total_posts"], job["processed_posts"], job["failed_posts"]) == (2, 2, 0)
    assert len(job["scores"]["v1"]) == len(job["scores"]["v2"]) == 2

    db = session_factory()
    assert db.query(models.AnalysisResult).count() == 4  # v1 + v2 per post
    db.close()

    again = _run(session_factory)
    assert again["total_posts"] == 0  # already analyzed under both versions


def test_analysis_job_records_failed_posts_and_continues(session_factory, monkeypatch):
    monkeypatch.setattr(runner, "run_pipeline_all_versions", _fake_pipeline(fail_ids={"b"}))
    _seed(session_factory, ["a", "b", "c"])

    job = _run(session_factory)
    assert job["status"] == "completed_with_errors"
    assert (job["processed_posts"], job["failed_posts"]) == (2, 1)
    assert "reddit:b" in job["errors"][0]

    db = session_factory()
    assert analysis_jobs.pending_count(db) == 1  # the failed post is retried next run
    db.close()


def test_stage_hook_reports_stages_without_changing_results(monkeypatch):
    monkeypatch.setattr(step1_relevance, "classify_relevance_llm",
                        lambda *a, **k: {"relevant": False, "confidence": 0.9})
    stages: list[int] = []
    kwargs = dict(source_item_id="s1", title="", text="I love hiking on weekends.", created_at=None)
    with_hook = pipeline_module.run_pipeline_all_versions(**kwargs, on_stage=stages.append)
    without = pipeline_module.run_pipeline_all_versions(**kwargs)
    assert stages == [1, 4, 5]  # non-relevant short-circuit skips Steps 2-3
    assert [r.model_dump(exclude={"created_at", "updated_at"}) for r in with_hook] == [
        r.model_dump(exclude={"created_at", "updated_at"}) for r in without
    ]


# --- API -------------------------------------------------------------------


@pytest.fixture
def client(session_factory, monkeypatch):
    from app.main import app

    def override():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    # Run jobs inline against the test DB instead of in a thread on sld.db.
    def start_inline(kind, create, run):
        job_id = create()
        return job_id

    app.dependency_overrides[get_db] = override
    monkeypatch.setattr(jobs, "start_job", start_inline)
    yield TestClient(app)  # no `with`: skip lifespan, which touches the real DB
    app.dependency_overrides.clear()


def test_api_validates_collection_requests(client):
    assert client.post("/api/collection/jobs", json={"mode": "latest_n"}).status_code == 422
    assert client.post("/api/collection/jobs", json={"mode": "latest_n", "post_limit": 0}).status_code == 422
    r = client.post(
        "/api/collection/jobs",
        json={"mode": "custom_range", "post_limit": 5,
              "start_date": "2026-09-20T00:00:00Z", "end_date": "2026-09-19T00:00:00Z"},
    )
    assert r.status_code == 422
    r = client.post("/api/collection/jobs", json={"mode": "latest_n", "post_limit": 5, "sources": ["myspace"]})
    assert r.status_code == 400


def test_api_creates_and_lists_collection_job(client):
    r = client.post(
        "/api/collection/jobs",
        json={"mode": "since_last_sweep", "sources": ["reddit", "aapc"], "post_limit": 99},
    )
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "queued"
    assert body["sources"] == ["aapc", "reddit"]  # canonical order
    assert body["post_limit"] is None  # ignored for since_last_sweep
    assert set(body["source_results"]) == {"aapc", "reddit"}

    assert client.get(f"/api/collection/jobs/{body['id']}").json()["id"] == body["id"]
    assert [j["id"] for j in client.get("/api/collection/jobs").json()["results"]] == [body["id"]]
    assert client.get("/api/collection/jobs/999").status_code == 404

    sources = client.get("/api/collection/sources").json()["sources"]
    assert [s["key"] for s in sources] == ["aapc", "reddit", "linkedin", "facebook", "x"]
    assert all("checkpoint" in s for s in sources)


def test_api_rejects_second_job_while_one_runs(client, monkeypatch):
    def busy(kind, create, run):
        raise jobs.JobConflict("A collection job (#1) is still running.")

    monkeypatch.setattr(jobs, "start_job", busy)
    r = client.post("/api/analysis/jobs", json={})
    assert r.status_code == 409


def test_job_slot_is_exclusive():
    import threading

    release = threading.Event()
    started = jobs.start_job("collection", lambda: 1, lambda _id: release.wait(5))
    try:
        with pytest.raises(jobs.JobConflict):
            jobs.start_job("analysis", lambda: 2, lambda _id: None)
        assert jobs.active_job() == {"kind": "collection", "id": started}
    finally:
        release.set()
    for _ in range(100):
        if jobs.active_job() is None:
            break
        threading.Event().wait(0.02)
    assert jobs.active_job() is None


def test_interrupted_jobs_are_marked_on_startup(session_factory):
    db = session_factory()
    db.add(models.AnalysisJob(status="running", errors=[], scores={},
                              started_at=datetime.now(timezone.utc)))
    db.commit()
    db.close()
    jobs.mark_interrupted_jobs(session_factory)
    db = session_factory()
    job = db.query(models.AnalysisJob).one()
    assert job.status == "interrupted"
    db.close()
