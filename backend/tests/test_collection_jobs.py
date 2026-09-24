"""
Dashboard collection jobs: modes, windows, limits, dedup, partial failure and
the Since Last Sweep checkpoint. Collectors are replaced with fake adapters
(no Apify calls) and everything runs against an isolated in-memory DB, never
the real backend/data/sld.db.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401  (registers the tables on Base.metadata)
from app.db.base import Base
from app.db.models import CollectionCheckpoint, NormalizedItem
from app.services import collection_jobs
from app.services.collection_sources import FetchPlan, SourceAdapter, UnitFetch, post_time

NOW = datetime.now(timezone.utc)


def _record(source: str, sid: str, hours_ago: float) -> dict:
    return {
        "source": source,
        "source_item_id": sid,
        "url": None,
        "title": None,
        "text": f"post {sid}",
        "author_id": None,
        "author_name": None,
        "author_profile_url": None,
        "author_role": None,
        "organization_name": None,
        "organization_url": None,
        "location": None,
        "created_at": NOW - timedelta(hours=hours_ago),
        "collected_at": NOW,
        "engagement": None,
        "parent_id": None,
        "conversation_id": sid,
        "media_type": "text",
        "raw_data": {"id": sid},
        "source_metadata": {},
    }


class FakeAdapter(SourceAdapter):
    """Two units; each returns the posts listed for it, newest first."""

    needs_apify = False
    unit_label = "unit"
    sweep_depth, max_depth = 10, 50

    def __init__(self, key: str, posts: dict[str, list[tuple[str, float]]], fail_units=()):
        self.key = self.label = key
        self.posts = posts
        self.fail_units = set(fail_units)
        self.calls: list[tuple[str, int, FetchPlan]] = []

    def units(self):
        return {name: name for name in self.posts}

    def fetch_unit(self, name, arg, depth, plan):
        self.calls.append((name, depth, plan))
        if name in self.fail_units:
            raise RuntimeError("Authentication error")
        records = [_record(self.key, sid, h) for sid, h in self.posts[name][:depth]]
        return UnitFetch(records, len(records) >= depth)


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _run(session_factory, adapters, mode, sources, **kwargs):
    db = session_factory()
    try:
        job = collection_jobs.create_job(db, mode, sources, **kwargs)
        job_id = job.id
    finally:
        db.close()
    collection_jobs.run_job(job_id, session_factory=session_factory, adapters=adapters)
    db = session_factory()
    try:
        return collection_jobs.to_dict(db.get(models.CollectionJob, job_id))
    finally:
        db.close()


def _adapters(*adapters):
    return {a.key: a for a in adapters}


def test_latest_n_limits_to_newest_posts(session_factory):
    fake = FakeAdapter("reddit", {"a": [("r1", 1), ("r2", 5)], "b": [("r3", 2), ("r4", 9)]})
    job = _run(session_factory, _adapters(fake), "latest_n", ["reddit"], post_limit=3)

    assert job["status"] == "completed"
    res = job["source_results"]["reddit"]
    assert (res["fetched"], res["new"], res["duplicate"]) == (3, 3, 0)
    db = session_factory()
    stored = {sid for (sid,) in db.query(NormalizedItem.source_item_id).all()}
    db.close()
    assert stored == {"r1", "r3", "r2"}  # r4 is the oldest and falls outside N=3
    # Latest N never moves the Since Last Sweep checkpoint.
    assert res["checkpoint_advanced"] is False


def test_custom_range_filters_to_window(session_factory):
    fake = FakeAdapter("aapc", {"a": [("p1", 1), ("p2", 30), ("p3", 80)], "b": [("p4", 50)]})
    job = _run(
        session_factory, _adapters(fake), "custom_range", ["aapc"],
        start_date=NOW - timedelta(hours=60), end_date=NOW - timedelta(hours=10), post_limit=10,
    )
    res = job["source_results"]["aapc"]
    assert res["fetched"] == 2  # p2 (30h) and p4 (50h); p1 is too new, p3 too old
    db = session_factory()
    assert {sid for (sid,) in db.query(NormalizedItem.source_item_id).all()} == {"p2", "p4"}
    db.close()
    # custom_range fetches at least a sweep's depth so the filter has material
    assert all(depth == fake.sweep_depth for _, depth, _ in fake.calls)


def test_multiple_sources_and_duplicates(session_factory):
    a = FakeAdapter("reddit", {"u": [("r1", 1), ("r2", 2)]})
    b = FakeAdapter("linkedin", {"u": [("l1", 1)], "v": [("l1", 1), ("l2", 3)]})
    adapters = _adapters(a, b)

    first = _run(session_factory, adapters, "latest_n", ["reddit", "linkedin"], post_limit=5)
    assert first["status"] == "completed"
    assert (first["posts_fetched"], first["posts_new"], first["posts_duplicate"]) == (4, 4, 0)
    # l1 came back from both LinkedIn units but is one post
    assert first["source_results"]["linkedin"]["fetched"] == 2

    second = _run(session_factory, adapters, "latest_n", ["reddit", "linkedin"], post_limit=5)
    assert (second["posts_fetched"], second["posts_new"], second["posts_duplicate"]) == (4, 0, 4)
    db = session_factory()
    assert db.query(NormalizedItem).count() == 4
    db.close()


def test_failed_source_does_not_fail_others(session_factory):
    ok = FakeAdapter("facebook", {"g": [("f1", 1)]})
    bad = FakeAdapter("aapc", {"forum": [("p1", 1)]}, fail_units={"forum"})
    job = _run(session_factory, _adapters(ok, bad), "since_last_sweep", ["aapc", "facebook"])

    assert job["status"] == "completed_with_errors"
    assert job["source_results"]["facebook"]["status"] == "completed"
    assert job["source_results"]["aapc"]["status"] == "failed"
    assert job["errors"] == ["aapc: forum: Authentication error"]
    assert job["retryable_sources"] == ["aapc"]

    db = session_factory()
    assert db.get(CollectionCheckpoint, "facebook") is not None
    assert db.get(CollectionCheckpoint, "aapc") is None  # failed source: not advanced
    db.close()


def test_partial_unit_failure_stores_posts_but_keeps_checkpoint(session_factory):
    fake = FakeAdapter("reddit", {"a": [("r1", 1)], "b": [("r2", 1)]}, fail_units={"b"})
    job = _run(session_factory, _adapters(fake), "since_last_sweep", ["reddit"])
    res = job["source_results"]["reddit"]
    assert res["status"] == "partial"
    assert res["new"] == 1
    assert res["checkpoint_advanced"] is False
    assert job["status"] == "completed_with_errors"


def test_since_last_sweep_uses_and_advances_checkpoint(session_factory):
    # Existing data from the terminal scripts: newest stored post is 20h old.
    db = session_factory()
    from app.collectors.common import upsert_normalized_items

    upsert_normalized_items(db, [_record("x", "old", 20)])
    db.close()

    fake = FakeAdapter("x", {"acct": [("n1", 2), ("n2", 10), ("old", 20), ("older", 40)]})
    first = _run(session_factory, _adapters(fake), "since_last_sweep", ["x"])
    res = first["source_results"]["x"]
    assert res["window_origin"] == "newest_stored_post"
    assert res["fetched"] == 3  # n1, n2 and the boundary post itself; "older" is before the window
    assert (res["new"], res["duplicate"]) == (2, 1)
    assert res["checkpoint_advanced"] is True

    db = session_factory()
    checkpoint = db.get(CollectionCheckpoint, "x").last_successful_fetch
    db.close()

    # Second sweep starts at the checkpoint, so the earlier posts are out of window.
    second = _run(session_factory, _adapters(fake), "since_last_sweep", ["x"])
    res2 = second["source_results"]["x"]
    assert res2["window_origin"] == "checkpoint"
    assert datetime.fromisoformat(res2["window_start"]).replace(tzinfo=None) == checkpoint.replace(tzinfo=None)
    assert res2["fetched"] == 0


def test_since_last_sweep_warns_when_depth_does_not_reach_window_start(session_factory):
    posts = [(f"p{i}", i * 0.1) for i in range(30)]  # 30 posts in the last 3 hours
    fake = FakeAdapter("reddit", {"sub": posts})
    fake.sweep_depth = 5
    db = session_factory()
    db.add(CollectionCheckpoint(source="reddit", last_successful_fetch=NOW - timedelta(days=1)))
    db.commit()
    db.close()

    job = _run(session_factory, _adapters(fake), "since_last_sweep", ["reddit"])
    res = job["source_results"]["reddit"]
    assert res["fetched"] == 5
    assert any("fetch depth" in w for w in res["warnings"])


def test_unavailable_source_is_reported_not_hidden(session_factory, monkeypatch):
    fake = FakeAdapter("linkedin", {"q": [("l1", 1)]})
    monkeypatch.setattr(fake, "unavailable_reason", lambda: "APIFY_TOKEN is not set in the backend .env")
    job = _run(session_factory, _adapters(fake), "latest_n", ["linkedin"], post_limit=5)
    assert job["status"] == "failed"
    assert job["source_results"]["linkedin"]["errors"] == ["APIFY_TOKEN is not set in the backend .env"]
    assert fake.calls == []


def test_id_collision_with_another_source_is_skipped(session_factory):
    from app.collectors.common import upsert_normalized_items

    db = session_factory()
    upsert_normalized_items(db, [_record("facebook", "123", 1)])
    db.close()
    fake = FakeAdapter("x", {"acct": [("123", 1), ("456", 2)]})
    job = _run(session_factory, _adapters(fake), "latest_n", ["x"], post_limit=5)
    res = job["source_results"]["x"]
    assert (res["fetched"], res["new"], res["skipped"]) == (1, 1, 1)


def test_depth_for_modes():
    fake = FakeAdapter("reddit", {"a": [], "b": [], "c": [], "d": []})
    assert fake.depth_for(FetchPlan("since_last_sweep")) == fake.sweep_depth
    assert fake.depth_for(FetchPlan("latest_n", limit=20)) == 5
    assert fake.depth_for(FetchPlan("latest_n", limit=1000)) == fake.max_depth
    assert fake.depth_for(FetchPlan("custom_range", limit=4)) == fake.sweep_depth


def test_reddit_post_time_falls_back_to_raw_created_utc():
    record = {"created_at": None, "raw_data": {"created_utc": "2026-09-22T13:00:30.000Z"}}
    assert post_time(record) == datetime(2026, 9, 22, 13, 0, 30, tzinfo=timezone.utc)


def test_errors_are_readable_and_grouped(session_factory):
    err = RuntimeError(
        'Failed to start actor a~b: {\n  "error": {\n    "type": "user-or-token-not-found",\n'
        '    "message": "User was not found or authentication token is not valid"\n  }\n}'
    )
    assert collection_jobs.readable_error(err) == (
        "Failed to start actor a~b: User was not found or authentication token is not valid"
    )

    fake = FakeAdapter("reddit", {"a": [], "b": [], "c": []}, fail_units={"a", "b", "c"})
    job = _run(session_factory, _adapters(fake), "latest_n", ["reddit"], post_limit=5)
    assert job["source_results"]["reddit"]["errors"] == ["All 3 units: Authentication error"]


def test_real_adapters_drive_existing_collectors(monkeypatch):
    """Each adapter's fetch_unit goes through its collector's own functions
    (actor input, normalization, collectable filter); only the Apify call is stubbed."""
    from app.collectors import facebook, linkedin, reddit, x
    from app.services.collection_sources import ADAPTERS

    calls = []

    def fake_actor(module_raw):
        def run(actor_id, run_input, **kwargs):
            calls.append((actor_id, run_input, kwargs))
            return module_raw
        return run

    when = "2026-09-23T10:00:00.000Z"
    monkeypatch.setattr(reddit, "run_actor_sync", fake_actor(
        [{"id": "r1", "title": "t", "body": "denial", "created_utc": when}]))
    monkeypatch.setattr(linkedin, "run_actor_sync", fake_actor(
        [{"id": "l1", "content": "prior auth", "linkedinUrl": "u", "postedAt": {"date": when}, "author": {}}]))
    monkeypatch.setattr(facebook, "run_actor_sync", fake_actor(
        [{"legacyId": "f1", "text": "denied claim", "time": when, "user": {}},
         {"error": "private group"}]))
    monkeypatch.setattr(x, "run_actor_sync", fake_actor(
        [{"id": "x1", "recordType": "tweet", "createdAt": when, "author": {"username": "a"},
          "text": "Prior auth denied again for a routine procedure; payer insists on a peer to peer review every single time we submit."},
         {"id": "x2", "recordType": "tweet", "createdAt": when, "author": {}, "text": "too short"}]))

    window = FetchPlan("since_last_sweep", datetime(2026, 9, 22, tzinfo=timezone.utc), NOW)
    for key, expected in [("reddit", ["r1"]), ("linkedin", ["l1"]), ("facebook", ["f1"]), ("x", ["x1"])]:
        adapter = ADAPTERS[key]
        name, arg = next(iter(adapter.units().items()))
        fetched = adapter.fetch_unit(name, arg, 5, window)
        assert [r["source_item_id"] for r in fetched.records] == expected, key
        assert all(r["source"] == key for r in fetched.records)
        assert adapter.select({name: fetched.records}, window) == fetched.records

    reddit_input = calls[0][1]
    assert reddit_input == {"subredditName": reddit.DEFAULT_SUBREDDITS[0], "maxPosts": 5, "subredditSort": "new"}
    fb_kwargs = calls[2][2]
    assert fb_kwargs["max_total_charge_usd"] == facebook.MAX_CHARGE_PER_RUN_USD  # spend cap kept
    x_query = calls[3][1]["query"]
    assert "since:2026-09-22" in x_query and x_query.startswith("from:")
