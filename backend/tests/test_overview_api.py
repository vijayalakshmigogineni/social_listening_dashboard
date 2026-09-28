"""
Overview API (/api/stats/overview) and its drill-down contract: every KPI
card and chart bucket carries an /api/posts filter, and that filter must
return exactly the count the card shows. Isolated in-memory DB only.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.analysis.scoring_opportunity import OPPORTUNITY_THRESHOLD
from app.api import opportunity
from app.db import models
from app.db.base import Base, get_db
from app.main import app
from app.schemas.analysis import ANALYSIS_VERSION, SCORING_VERSION

NOW = datetime.now(timezone.utc)


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


def _add(db, sid, *, source="reddit", score=None, problem=True, relevant=True,
         categories=("denials_claims_friction",), seeking="L2", created=None,
         inserted=None, opportunity_type="denial_management", version=ANALYSIS_VERSION):
    db.add(models.NormalizedItem(
        source=source, source_item_id=sid, title=f"post {sid}", text="t",
        collected_at=NOW, created_at=created or NOW - timedelta(days=40),
        inserted_at=inserted or NOW - timedelta(days=5), raw_data={},
    ))
    if score is not None:
        db.add(models.AnalysisResult(
            source_item_id=sid, analysis_version=version, scoring_version=SCORING_VERSION,
            rcm_relevant=relevant, rcm_relevance_confidence=0.9,
            problem_evidence=problem, first_person=problem, problem_confidence=0.9,
            problem_category=list(categories), payer_tags=[], procedure_tags=[],
            denial_reason_tags=[], cpt_hcpcs_codes=[], speaker_type="practice_side",
            content_stance="seeking", seeking_level=seeking, evidence_quote="q", confidence=0.8,
            score_breakdown={"llm_score": 80.0, "rcm_score": 90.0, "step3_score": 50.0,
                             "final_score": score,
                             "llm_assessment": {"opportunity_type": opportunity_type,
                                                "probeps_fit": "high",
                                                "opportunity_reasoning": "why"}},
            final_score=score,
        ))


@pytest.fixture
def seeded(db_factory):
    db = db_factory()
    # Opportunities
    _add(db, "a", score=88.0, inserted=NOW)  # collected now -> New Today
    _add(db, "b", score=72.0, source="aapc", seeking=None,
         categories=("authorization_utilization_management", "denials_claims_friction"),
         opportunity_type="prior_authorization")
    _add(db, "c", score=OPPORTUNITY_THRESHOLD, source="facebook", seeking="L1",
         created=NOW - timedelta(days=100))
    _add(db, "d", score=55.0, inserted=NOW)  # New Today
    # Not opportunities
    _add(db, "e", score=OPPORTUNITY_THRESHOLD - 0.1)                    # just under
    _add(db, "f", score=45.0, problem=False)                          # no problem evidence
    _add(db, "g", score=0.0, relevant=False, problem=False, categories=())
    _add(db, "h")                                                      # never analyzed
    _add(db, "i", score=95.0, version="sld-analysis-v3")               # old version only
    db.commit()
    db.close()


def _posts_total(client, filt: dict) -> int:
    params = {k: str(v).lower() if isinstance(v, bool) else v for k, v in filt.items()}
    resp = client.get("/api/posts", params={**params, "page_size": 100})
    assert resp.status_code == 200, resp.text
    return resp.json()["total"]


def test_kpis(client, seeded):
    body = client.get("/api/stats/overview").json()
    k = body["kpis"]
    assert k["total_opportunities"]["value"] == 4
    assert k["new_today"]["value"] == 2
    assert k["rcm_relevant"]["value"] == 6  # a-f; g is not relevant, h/i have no current row
    assert body["definitions"]["opportunity_threshold"] == OPPORTUNITY_THRESHOLD
    assert body["definitions"]["analysis_version"] == ANALYSIS_VERSION


def test_every_kpi_drills_down_to_the_same_count(client, seeded):
    kpis = client.get("/api/stats/overview").json()["kpis"]
    for name, card in kpis.items():
        assert _posts_total(client, card["filter"]) == card["value"], name


def test_every_chart_bucket_drills_down_to_the_same_count(client, seeded):
    series = client.get("/api/stats/overview", params={"bucket": "week"}).json()["series"]
    buckets = (series["opportunities_over_time"]["points"] + series["problem_category"]
               + series["source_contribution"] + series["seeking_level"])
    assert buckets
    for b in buckets:
        assert _posts_total(client, b["filter"]) == b["count"], b


def test_chart_series_content(client, seeded):
    s = client.get("/api/stats/overview").json()["series"]
    assert {b["key"]: b["count"] for b in s["source_contribution"]} == {
        "reddit": 2, "aapc": 1, "facebook": 1}
    cats = {b["key"]: b["count"] for b in s["problem_category"]}
    assert cats == {"denials_claims_friction": 4, "authorization_utilization_management": 1}
    assert {b["key"]: b["count"] for b in s["seeking_level"]} == {"L2": 2, "none": 1, "L1": 1}
    over_time = s["opportunities_over_time"]
    assert over_time["bucket"] == "month"
    assert len(over_time["points"]) == 12  # window ending at the current month
    assert sum(p["count"] for p in over_time["points"]) + over_time["earlier"] == 4
    assert over_time["undated"] == 0


def test_over_time_window_counts_old_posts_as_earlier(client, db_factory):
    db = db_factory()
    _add(db, "old", score=80.0, created=NOW - timedelta(days=365 * 10))
    _add(db, "new", score=80.0, created=NOW - timedelta(days=2))
    db.commit()
    db.close()
    for bucket, n in (("day", 30), ("week", 26), ("month", 12)):
        ot = client.get("/api/stats/overview", params={"bucket": bucket}).json()["series"]["opportunities_over_time"]
        assert len(ot["points"]) == n, bucket
        assert ot["earlier"] == 1 and sum(p["count"] for p in ot["points"]) == 1, bucket


def test_top_three_are_highest_opportunities(client, seeded):
    top = client.get("/api/stats/overview").json()["top"]
    assert [p["source_item_id"] for p in top] == ["a", "b", "d"]
    assert all(p["is_opportunity"] for p in top)
    assert top[0]["opportunity_type"] == "denial_management"
    assert top[0]["llm_score"] == 80.0


def test_new_today_boundary_uses_report_timezone(client, db_factory, monkeypatch):
    # 03:00 UTC is still "yesterday" in New York (UTC-4/-5), but today in UTC.
    now = datetime.now(timezone.utc)
    early_utc = now.replace(hour=3, minute=0, second=0, microsecond=0)
    if early_utc > now:
        early_utc -= timedelta(days=1)
    db = db_factory()
    _add(db, "x", score=90.0, inserted=early_utc)
    db.commit()
    db.close()

    for tz in ("UTC", "America/New_York", "Asia/Kolkata"):
        monkeypatch.setattr(opportunity, "REPORT_TZ", tz)
        body = client.get("/api/stats/overview").json()
        start = datetime.fromisoformat(body["definitions"]["today_start"])
        assert body["definitions"]["report_tz"] == tz
        assert (start.hour, start.minute) == (0, 0)
        expected = 1 if early_utc >= start else 0
        card = body["kpis"]["new_today"]
        assert card["value"] == expected, tz
        assert _posts_total(client, card["filter"]) == expected, tz


def test_posts_expose_score_components_and_opportunity_filters(client, seeded):
    body = client.get("/api/posts", params={"opportunity": "true", "sort": "score_desc"}).json()
    assert body["total"] == 4
    first = body["results"][0]
    assert (first["llm_score"], first["rcm_score"], first["step3_score"]) == (80.0, 90.0, 50.0)
    assert first["probeps_fit"] == "high" and first["is_opportunity"] is True
    assert _posts_total(client, {"opportunity": False}) == 5  # e, f, g, h, i (i has no current row)
    assert _posts_total(client, {"opportunity_type": "prior_authorization"}) == 1


def test_version_parameter_is_gone(client, seeded):
    # Only the current version is served; old-version rows are not joined.
    body = client.get("/api/posts/reddit/i").json()
    assert body["analyzed"] is False


def test_pipeline_debug_serves_the_stored_row_without_llm(client, seeded):
    from unittest.mock import patch

    from app.analysis import step2_semantic

    with patch.object(step2_semantic, "analyze_semantics_llm") as llm:
        body = client.get("/api/pipeline/reddit/a").json()
        missing = client.get("/api/pipeline/reddit/h").json()
    llm.assert_not_called()
    assert (body["mode"], body["analyzed"], body["final_score"]) == ("stored", True, 88.0)
    assert body["score_breakdown"]["llm_assessment"]["opportunity_type"] == "denial_management"
    assert body["raw_record"]["source_item_id"] == "a"
    assert (missing["mode"], missing["analyzed"], missing["score_breakdown"]) == ("stored", False, None)