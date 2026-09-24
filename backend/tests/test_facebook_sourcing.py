"""
Facebook source-selection tooling: pruning dropped groups, ingesting only
hand-selected posts, and the probe budget guard. No network (Apify mocked) and
an isolated in-memory DB throughout.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import ingest_facebook_selection as ingest  # noqa: E402
import probe_facebook_groups as probe_mod  # noqa: E402
import prune_facebook_groups as prune_mod  # noqa: E402

from app.collectors import facebook  # noqa: E402
from app.collectors.common import upsert_normalized_items  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.models import AnalysisResult, NormalizedItem  # noqa: E402


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def _raw(pid: str, text: str = "Aetna RFA denials for medical necessity. Anyone else?") -> dict:
    return {"facebookUrl": "https://www.facebook.com/groups/1",
            "url": f"https://www.facebook.com/groups/1/permalink/{pid}/",
            "time": "2026-09-01T00:00:00.000Z", "user": {"id": "u", "name": "n"},
            "text": text, "legacyId": pid, "facebookId": "1", "groupTitle": "G"}


def _analysis(sid: str, version: str) -> AnalysisResult:
    return AnalysisResult(source_item_id=sid, analysis_version=version, scoring_version="s",
                          rcm_relevant=True, rcm_relevance_confidence=0.9, problem_evidence=True,
                          first_person=False, problem_confidence=0.8, content_stance="neutral",
                          evidence_quote="q", confidence=0.7, score_breakdown={}, final_score=1.0)


def test_removed_groups_are_gone_from_collector():
    for key in ("medical_claims_tasks", "nemt_claims_denials_remittances", "usa_medical_billing"):
        assert key not in facebook.DEFAULT_GROUPS
    assert "pmr_interventional_pain_billing" in facebook.DEFAULT_GROUPS


def test_prune_deletes_only_matching_group_and_all_its_analysis_rows():
    db = _session()
    upsert_normalized_items(db, [facebook.normalize_post(_raw("a"), "drop_me"),
                                 facebook.normalize_post(_raw("b"), "keep_me")])
    for sid in ("a", "b"):
        for version in ("sld-analysis-v1", "exp-v1"):
            db.add(_analysis(sid, version))
    db.commit()

    dry = prune_mod.prune(db, {"drop_me"}, dry_run=True)
    assert dry["posts"] == 1 and dry["analysis_rows"] == 2
    assert db.query(NormalizedItem).count() == 2  # dry run deletes nothing

    prune_mod.prune(db, {"drop_me"})
    assert [r.source_item_id for r in db.query(NormalizedItem).all()] == ["b"]
    assert {r.source_item_id for r in db.query(AnalysisResult).all()} == {"b"}


def test_ingest_stores_only_selected_and_reports_unknown_ids():
    raw_index = ingest.index_raw([{"items": [_raw("1"), _raw("2"), _raw("3", text="  ")]}])
    selection = [{"post_id": "1", "group_key": "g"}, {"post_id": "3", "group_key": "g"},
                 {"post_id": "999", "group_key": "g"}]
    result = ingest.build_records(selection, raw_index, stored_ids=set())

    assert [r["source_item_id"] for r in result["records"]] == ["1"]  # "2" was not selected
    assert result["missing"] == ["999"]  # reported, not invented
    assert result["not_post"] == ["3"]
    assert result["records"][0]["source_metadata"]["group_key"] == "g"


def test_ingest_is_idempotent():
    raw_index = ingest.index_raw([{"items": [_raw("1")]}])
    selection = [{"post_id": "1", "group_key": "g"}]
    db = _session()
    first = ingest.build_records(selection, raw_index, stored_ids=set())
    upsert_normalized_items(db, first["records"])
    stored = {r.source_item_id for r in db.query(NormalizedItem).all()}
    second = ingest.build_records(selection, raw_index, stored_ids=stored)
    assert second["records"] == [] and second["already_stored"] == ["1"]


def test_probe_budget_guard_stops_before_exceeding_cap(tmp_path):
    ledger = probe_mod.Ledger(tmp_path / "spend.json", budget=0.07)
    calls = []

    def runner(actor, run_input, **kwargs):
        calls.append(run_input)
        return [_raw(str(i)) for i in range(10)]

    with pytest.raises(probe_mod.BudgetExceeded):
        probe_mod.probe(tmp_path, ["g1", "g2"], 10, ledger, runner=runner)
    assert len(calls) == 1  # second group refused before starting
    assert ledger.spent <= 0.07
