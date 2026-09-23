"""
Schema/pipeline compatibility after adding stance_confidence/stance_source/
seeking_source to Step4Context and Step5Evidence: AnalysisResult must still
build and round-trip through the DB model with the new fields absent from
its column list (they are Pydantic-only, not persisted -- see
backend/app/db/models.py, which stores only the aggregate Step5 confidence).
"""

from __future__ import annotations

from unittest.mock import patch

from app.analysis import pipeline as pipeline_module
from app.analysis import step4_speaker_stance_seeking as step4
from app.db.models import AnalysisResult as AnalysisResultRow
from app.schemas.analysis import AnalysisResult
from tests.test_step4 import _nli_result, fake_run_zero_shot_factory


def test_run_pipeline_builds_valid_analysis_result_with_new_step4_fields():
    stance = _nli_result("seeking", 0.9, 0.5)
    seeking = _nli_result("L2", 0.9, 0.5)
    with patch.object(step4, "run_zero_shot", fake_run_zero_shot_factory(stance, seeking)):
        result = pipeline_module.run_pipeline(
            source_item_id="reddit:abc123",
            title="Denials keep piling up",
            text="Is there a better way to manage our prior auth denials? We're drowning.",
            created_at=None,
        )

    assert isinstance(result, AnalysisResult)
    assert result.content_stance == "seeking"
    assert result.seeking_level == "L2"

    # Every DB column AnalysisResult maps to must be satisfiable from the
    # pydantic model's fields -- confirms the new optional fields didn't
    # break the existing persisted contract.
    row_columns = {c.name for c in AnalysisResultRow.__table__.columns}
    payload = result.model_dump()
    missing = row_columns - set(payload.keys()) - {"id"}
    assert not missing, f"AnalysisResult is missing fields the DB row expects: {missing}"


def test_non_relevant_short_circuit_still_produces_valid_result():
    # Step1 rcm_relevant=False path builds Step4Context(content_stance="neutral")
    # directly, without calling classify_context at all -- must still validate.
    result = pipeline_module.run_pipeline(
        source_item_id="reddit:xyz789",
        title="",
        text="I love hiking on weekends.",
        created_at=None,
    )
    assert result.rcm_relevant is False
    assert result.content_stance == "neutral"
    assert result.seeking_level is None
