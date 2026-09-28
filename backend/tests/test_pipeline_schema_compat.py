"""
Schema/pipeline compatibility: AnalysisResult must still build and round-trip
through the DB model after the semantic refactor. Step 1's relevance_status /
relevance_method are trace-only, and Step 2's Step2Semantic is persisted only
inside score_breakdown["llm_assessment"] -- not as columns (see
backend/app/db/models.py) -- so the row's column list must be satisfiable
from AnalysisResult exactly as before.
"""

from __future__ import annotations

from unittest.mock import patch

from app.analysis import pipeline as pipeline_module
from app.analysis import step1_relevance, step2_semantic
from app.db.models import AnalysisResult as AnalysisResultRow
from app.schemas.analysis import AnalysisResult

SEMANTIC_L2 = {
    "problem_evidence": True, "problem_current": True, "problem_recurring": True,
    "first_person": True, "operational_impact": True,
    "speaker_type": "practice_side", "content_stance": "seeking", "seeking_level": "L2",
    "evidence_quote": "Is there a better way to manage our prior auth denials?",
    "problem_confidence": 0.9, "first_person_confidence": 0.9,
    "operational_impact_confidence": 0.8, "speaker_confidence": 0.8,
    "stance_confidence": 0.9, "seeking_confidence": 0.85,
    "pain_severity": "high", "business_impact": "high", "probeps_fit": "high",
    "opportunity_type": "prior_authorization",
    "opportunity_reasoning": "The practice is overwhelmed by prior-auth denials.",
    "pain_confidence": 0.8, "impact_confidence": 0.8, "fit_confidence": 0.8,
}


def test_run_pipeline_builds_valid_analysis_result():
    with patch.object(step2_semantic, "analyze_semantics_llm", return_value=SEMANTIC_L2):
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
    # pydantic model's fields -- confirms the refactor didn't break the
    # existing persisted contract.
    row_columns = {c.name for c in AnalysisResultRow.__table__.columns}
    payload = result.model_dump()
    missing = row_columns - set(payload.keys()) - {"id"}
    assert not missing, f"AnalysisResult is missing fields the DB row expects: {missing}"


def test_non_relevant_short_circuit_still_produces_valid_result():
    # Zero keyword hits -> ambiguous -> LLM says not relevant -> the short-
    # circuit builds Step4Context(content_stance="neutral") directly.
    with patch.object(step1_relevance, "classify_relevance_llm",
                      return_value={"relevant": False, "confidence": 0.9}):
        result = pipeline_module.run_pipeline(
            source_item_id="reddit:xyz789",
            title="",
            text="I love hiking on weekends.",
            created_at=None,
        )
    assert result.rcm_relevant is False
    assert result.content_stance == "neutral"
    assert result.seeking_level is None
