"""
Editable source units (Data Collection page) and live per-source stats.
Isolated in-memory DB; no collector or network is called.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models
from app.db.base import Base, get_db
from app.main import app
from app.schemas.analysis import ANALYSIS_VERSION, SCORING_VERSION
from app.services import jobs, source_settings
from app.services.collection_sources import ADAPTERS, FetchPlan

NOW = datetime.now(timezone.utc)


@pytest.fixture(autouse=True)
def _clean_overrides(monkeypatch):
    monkeypatch.setattr(source_settings, "OVERRIDES", {})


@pytest.fixture
def db_factory():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture
def client(db_factory):
    def override():
        db = db_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)  # no `with`: skip lifespan, which touches the real DB
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("source,units", [
    ("reddit", [{"value": "r/MedicalCoding"}, {"value": "CodingandBilling"}]),
    ("x", [{"value": "@DrBruggeman"}]),
    ("aapc", [{"name": "billing", "value": "https://www.aapc.com/discuss/forums/billing-reimbursement.583/index.rss"}]),
    ("facebook", [{"name": "pain_billing", "value": "https://www.facebook.com/groups/290657479460430"}]),
    ("linkedin", [{"name": "denials", "value": '"prior authorization" OR "denied claim"'}]),
])
def test_valid_units_are_cleaned(source, units):
    cleaned = source_settings.validate(source, units)
    assert len(cleaned) == len(units)
    if source == "reddit":
        assert cleaned[0] == {"name": "MedicalCoding", "value": "MedicalCoding"}
    if source == "x":
        assert cleaned[0]["value"] == "DrBruggeman"


@pytest.mark.parametrize("source,units,reason", [
    ("reddit", [], "at least one"),
    ("reddit", [{"value": "bad name!"}], "subreddit"),
    ("reddit", [{"value": "Coding"}, {"value": "coding"}], "duplicate"),
    ("x", [{"value": "this_handle_is_far_too_long"}], "account"),
    ("aapc", [{"name": "x1", "value": "https://evil.example.com/rss"}], "forum rss url"),
    ("facebook", [{"name": "Bad Name", "value": "https://www.facebook.com/groups/1"}], "name"),
    ("linkedin", [{"name": "q", "value": "prior auth denials"}], "name"),
    ("linkedin", [{"name": "denials", "value": "ab"}], "search query"),
    ("reddit", [{"value": f"sub{i:02d}"} for i in range(source_settings.MAX_UNITS + 1)], "at most"),
    ("youtube", [{"value": "x"}], "no editable units"),
])
def test_invalid_units_are_rejected(source, units, reason):
    with pytest.raises(source_settings.InvalidUnits, match=f"(?i){reason}"):
        source_settings.validate(source, units)


# ---------------------------------------------------------------------------
# Adapters honor the saved list; reset restores the default
# ---------------------------------------------------------------------------
def test_saved_units_drive_the_adapter_and_reset_restores_default(db_factory):
    adapter = ADAPTERS["reddit"]
    default = adapter.units()
    db = db_factory()
    source_settings.save(db, "reddit", [{"value": "MedicalCoding"}, {"value": "PrivatePractice"}])
    assert adapter.units() == {"r/MedicalCoding": "MedicalCoding", "r/PrivatePractice": "PrivatePractice"}
    assert adapter.describe()["customized"] is True
    # depth planning divides by the (new) unit count
    assert adapter.depth_for(FetchPlan(mode="latest_n", limit=10)) == 5
    source_settings.reset(db, "reddit")
    assert adapter.units() == default and adapter.describe()["customized"] is False
    db.close()


def test_default_unit_values_round_trip_through_validation():
    # The page shows default units as editable rows; saving them unchanged
    # must be valid for every source.
    for key, adapter in ADAPTERS.items():
        rows = adapter.unit_values()
        assert source_settings.units_dict(key, source_settings.validate(key, rows)) == adapter.default_units(), key


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def test_api_save_and_reset_units(client):
    body = client.put("/api/collection/sources/x/units", json={"units": [{"value": "@EdGainesIII"}]})
    assert body.status_code == 200, body.text
    assert body.json()["units"] == ["@EdGainesIII"] and body.json()["customized"] is True
    listed = {s["key"]: s for s in client.get("/api/collection/sources").json()["sources"]}
    assert listed["x"]["units"] == ["@EdGainesIII"]
    assert listed["x"]["unit_rule"]["named"] is False
    reset = client.delete("/api/collection/sources/x/units").json()
    assert reset["customized"] is False and len(reset["units"]) > 1


def test_api_rejects_invalid_units_and_edits_while_a_job_runs(client, monkeypatch):
    bad = client.put("/api/collection/sources/reddit/units", json={"units": [{"value": "no spaces"}]})
    assert bad.status_code == 400 and "subreddit" in bad.json()["detail"]
    assert client.put("/api/collection/sources/nope/units", json={"units": []}).status_code == 404
    monkeypatch.setattr(jobs, "_active", {"kind": "collection", "id": 7})
    busy = client.put("/api/collection/sources/reddit/units", json={"units": [{"value": "MedicalCoding"}]})
    assert busy.status_code == 409


def test_api_source_stats(client, db_factory):
    db = db_factory()
    for sid, source, score, problem, inserted in [
        ("a", "reddit", 80.0, True, NOW),
        ("b", "reddit", 20.0, False, NOW - timedelta(days=2)),
        ("c", "reddit", None, None, NOW - timedelta(days=30)),
        ("d", "aapc", 55.0, True, NOW - timedelta(days=1)),
    ]:
        db.add(models.NormalizedItem(source=source, source_item_id=sid, title="t", text="t",
                                     collected_at=inserted, inserted_at=inserted,
                                     created_at=inserted - timedelta(hours=1), raw_data={}))
        if score is not None:
            db.add(models.AnalysisResult(
                source_item_id=sid, analysis_version=ANALYSIS_VERSION, scoring_version=SCORING_VERSION,
                rcm_relevant=True, rcm_relevance_confidence=0.9, problem_evidence=problem,
                first_person=problem, problem_confidence=0.9, speaker_type="practice_side",
                content_stance="seeking", evidence_quote="q", confidence=0.8,
                score_breakdown={}, final_score=score))
    db.commit()
    db.close()

    body = client.get("/api/collection/source-stats").json()
    assert len(body["days"]) == 14
    r = body["sources"]["reddit"]
    assert (r["posts"], r["analyzed"], r["pending"], r["rcm_relevant"], r["opportunities"]) == (3, 2, 1, 2, 1)
    assert sum(r["collected_per_day"]) == 2  # the 30-day-old post is outside the window
    assert r["collected_per_day"][-1] == 1  # collected today
    assert body["sources"]["aapc"]["opportunities"] == 1
    # every collectable source is present, even with no posts yet
    assert set(ADAPTERS) <= set(body["sources"])
    assert body["sources"]["linkedin"]["posts"] == 0
