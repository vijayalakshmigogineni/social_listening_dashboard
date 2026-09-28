"""
ProbePS opportunity score: 65% LLM + 20% RCM + 15% Step 3, each component
normalized to 0-100, two caps and nothing else. Pure functions over Step 1 /
Step 2 / Step 3 outputs -- no text, no LLM.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.analysis import pipeline as pipeline_module
from app.analysis import step2_semantic
from app.analysis.pipeline import rescore_row
from app.analysis.scoring_opportunity import (
    NO_PROBLEM_CAP,
    NON_OPPORTUNITY_LLM_CAP,
    SEEKING_POINTS,
    WEIGHTS,
    combine,
    llm_component,
    rcm_component,
    score_opportunity,
    step3_component,
)
from app.schemas.analysis import (
    ANALYSIS_VERSION,
    SCORING_VERSION,
    Step1Relevance,
    Step2Semantic,
    Step3Taxonomy,
)

RELEVANT = Step1Relevance(rcm_relevant=True, rcm_relevance_confidence=0.9)
NOT_RELEVANT = Step1Relevance(rcm_relevant=False, rcm_relevance_confidence=0.9)


def _sem(**kw) -> Step2Semantic:
    """'We keep getting UHC denials for RFA and our AR is increasing. Has
    anyone found a solution?' -- a strong, first-hand, recurring problem."""
    base = dict(
        problem_evidence=True, problem_current=True, problem_recurring=True,
        first_person=True, operational_impact=True,
        speaker_type="practice_side", content_stance="seeking", seeking_level="L2",
        evidence_quote="x", semantic_source="llm",
        problem_confidence=1.0, first_person_confidence=1.0, seeking_confidence=1.0,
        operational_impact_confidence=1.0, speaker_confidence=1.0, stance_confidence=1.0,
        pain_severity="high", business_impact="high", probeps_fit="high",
        opportunity_type="denial_management", opportunity_reasoning="r",
        pain_confidence=1.0, impact_confidence=1.0, fit_confidence=1.0,
    )
    base.update(kw)
    return Step2Semantic(**base)


def _cpt_question() -> Step2Semantic:
    """'Which CPT code should I use for this procedure?' -- RCM-relevant and
    specific, but not a problem and a weak opportunity."""
    return _sem(problem_evidence=False, problem_recurring=False, first_person=False,
                seeking_level="L1", seeking_confidence=0.9, business_impact="none",
                probeps_fit="low", fit_confidence=0.9, opportunity_type="informational_only")


DENIAL_TAXONOMY = Step3Taxonomy(
    problem_category=["denials_claims_friction"], payer_tags=["UHC"], procedure_tags=["RFA"],
)
RICH_TAXONOMY = Step3Taxonomy(
    problem_category=["denials_claims_friction", "coverage_policy"], payer_tags=["UHC", "Aetna"],
    procedure_tags=["RFA"], denial_reason_tags=["CO-50"], cpt_hcpcs_codes=["64633"],
    specialty="pain_management",
)


# ---------------------------------------------------------------------------
# The weighting itself
# ---------------------------------------------------------------------------
def test_weights_are_65_20_15_and_sum_to_one():
    assert WEIGHTS == {"llm": 0.65, "rcm": 0.20, "step3": 0.15}
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


def test_all_max_is_exactly_100_and_all_zero_is_0():
    assert combine(100, 100, 100, True)[0] == pytest.approx(100.0)
    assert combine(0, 0, 0, True)[0] == 0.0


def test_max_contributions_are_65_20_15():
    assert combine(100, 0, 0, True)[0] == pytest.approx(65.0)
    assert combine(0, 100, 0, True)[0] == pytest.approx(20.0)
    assert combine(0, 0, 100, True)[0] == pytest.approx(15.0)


# The five planning cases (component scores in, final score out).
CASES = {
    "strong_opportunity": ((90, 90, 80), 88.5),
    "high_rcm_weak_opportunity": ((25, 95, 90), 48.75),
    "strong_opportunity_thin_metadata": ((90, 60, 30), 75.0),
    "weak_signal": ((20, 40, 20), 24.0),
}


@pytest.mark.parametrize("name", CASES)
def test_planning_cases(name):
    (llm, rcm, s3), expected = CASES[name]
    assert combine(llm, rcm, s3, problem_evidence=True)[0] == pytest.approx(expected)


def test_planning_case_ordering():
    score = {name: combine(*inputs, True)[0] for name, (inputs, _) in CASES.items()}
    assert (score["strong_opportunity"] > score["strong_opportunity_thin_metadata"]
            > score["high_rcm_weak_opportunity"] > score["weak_signal"])
    # The point of the 65% weight: a strong human-judged opportunity with thin
    # metadata beats a highly RCM-relevant, highly specific weak one.
    assert score["strong_opportunity_thin_metadata"] - score["high_rcm_weak_opportunity"] > 20


def test_case5_specific_but_no_problem_is_capped():
    final, pre_cap, capped = combine(15, 90, 90, problem_evidence=False)
    assert pre_cap == pytest.approx(41.25)
    assert final == NO_PROBLEM_CAP and capped


def test_cap_never_raises_a_score():
    final, pre_cap, capped = combine(10, 20, 10, problem_evidence=False)
    assert final == pre_cap and not capped


# ---------------------------------------------------------------------------
# LLM component
# ---------------------------------------------------------------------------
def test_llm_component_maxes_at_100():
    score, points, capped = llm_component(_sem(seeking_level="L3"))
    assert score == 100.0 and not capped
    assert points.model_dump() == {"problem_evidence": 25, "first_person": 10, "seeking": 20,
                                   "business_impact": 15, "recurring": 5, "probeps_fit": 25}


@pytest.mark.parametrize("level,points", [("L0", 4), ("L1", 8), ("L2", 14), ("L3", 20), (None, 0)])
def test_seeking_points_are_confidence_weighted(level, points):
    _, pts, _ = llm_component(_sem(seeking_level=level, seeking_confidence=0.5))
    assert pts.seeking == points * 0.5


@pytest.mark.parametrize("grade,fit,impact", [
    ("none", 0, 0), ("low", 8, 5), ("moderate", 16, 10), ("high", 25, 15)])
def test_grade_points(grade, fit, impact):
    _, pts, _ = llm_component(_sem(probeps_fit=grade, business_impact=grade))
    assert (pts.probeps_fit, pts.business_impact) == (fit, impact)


def test_recurring_needs_a_problem():
    _, pts, _ = llm_component(_sem(problem_evidence=False, problem_recurring=True))
    assert pts.recurring == 0.0


def test_non_opportunity_type_caps_llm_score():
    score, _, capped = llm_component(_sem(opportunity_type="not_an_opportunity"))
    assert score == NON_OPPORTUNITY_LLM_CAP and capped


def test_fallback_semantics_score_no_opportunity_points():
    fallback = _sem(semantic_source="fallback", first_person_confidence=None,
                    pain_severity=None, business_impact=None, probeps_fit=None,
                    opportunity_type=None, impact_confidence=None, fit_confidence=None,
                    pain_confidence=None)
    _, pts, _ = llm_component(fallback)
    assert pts.first_person == pts.business_impact == pts.probeps_fit == 0.0


def test_pain_severity_and_speaker_have_no_direct_weight():
    a = llm_component(_sem(pain_severity="high", speaker_type="practice_side"))[0]
    b = llm_component(_sem(pain_severity="none", speaker_type="unknown"))[0]
    assert a == b


# ---------------------------------------------------------------------------
# RCM and Step 3 components
# ---------------------------------------------------------------------------
def test_rcm_component():
    score, pts = rcm_component(RELEVANT, DENIAL_TAXONOMY)
    assert (pts.relevance, pts.category_severity, pts.primary_problem_category) == (
        45.0, 50.0, "denials_claims_friction")
    assert score == 95.0


def test_rcm_component_uses_primary_category_only():
    tax = Step3Taxonomy(problem_category=["documentation_medical_necessity", "coverage_policy"])
    _, pts = rcm_component(RELEVANT, tax)
    assert pts.category_severity == pytest.approx(50 * 6 / 8)


def test_rcm_component_is_zero_when_not_relevant():
    assert rcm_component(NOT_RELEVANT, DENIAL_TAXONOMY)[0] == 0.0


def test_step3_component_counts_each_signal_once_and_maxes_at_100():
    score, pts = step3_component(RICH_TAXONOMY)
    assert (pts.category, pts.payer, pts.procedure, pts.denial_reason, pts.code, pts.specialty) == (
        7, 4, 3, 3, 2, 1)
    assert pts.total == 20 and score == 100.0
    assert step3_component(Step3Taxonomy())[0] == 0.0


# ---------------------------------------------------------------------------
# End to end: the RCM-relevance vs opportunity distinction
# ---------------------------------------------------------------------------
def test_real_problem_outranks_specific_cpt_question():
    problem = score_opportunity(RELEVANT, _sem(), DENIAL_TAXONOMY)
    question = score_opportunity(RELEVANT, _cpt_question(), RICH_TAXONOMY)
    # The question is at least as RCM-relevant and more specific...
    assert question.step3_score > problem.step3_score
    assert question.rcm_score >= problem.rcm_score - 0.01
    # ...yet it is a far weaker opportunity.
    assert problem.final_score > 80
    assert question.final_score <= NO_PROBLEM_CAP
    assert question.cap_applied


def test_breakdown_is_self_consistent():
    bd = score_opportunity(RELEVANT, _sem(problem_confidence=0.8), DENIAL_TAXONOMY)
    assert bd.llm_contribution == pytest.approx(0.65 * bd.llm_score)
    assert bd.rcm_contribution == pytest.approx(0.20 * bd.rcm_score)
    assert bd.step3_contribution == pytest.approx(0.15 * bd.step3_score)
    assert bd.final_score == pytest.approx(bd.llm_contribution + bd.rcm_contribution
                                           + bd.step3_contribution)
    assert bd.llm_score == pytest.approx(sum(bd.llm_points.model_dump().values()))
    assert bd.llm_assessment["probeps_fit"] == "high" and bd.llm_source == "llm"


def test_not_relevant_scores_zero_everywhere():
    bd = score_opportunity(NOT_RELEVANT, None, Step3Taxonomy())
    assert (bd.llm_score, bd.rcm_score, bd.step3_score, bd.final_score) == (0, 0, 0, 0)
    assert bd.llm_assessment is None


# ---------------------------------------------------------------------------
# Offline re-scoring
# ---------------------------------------------------------------------------
def test_rescore_row_reproduces_the_stored_score_without_llm():
    stored = score_opportunity(RELEVANT, _sem(seeking_confidence=0.7), DENIAL_TAXONOMY)
    with patch.object(step2_semantic, "analyze_semantics_llm") as llm:
        again = rescore_row(True, 0.9, stored.model_dump(), DENIAL_TAXONOMY)
    llm.assert_not_called()
    assert again.model_dump() == stored.model_dump()


def test_rescore_row_needs_llm_assessment_for_relevant_rows():
    assert rescore_row(True, 0.9, {"final_score": 50.0}, DENIAL_TAXONOMY) is None
    assert rescore_row(False, 0.9, None, Step3Taxonomy()).final_score == 0.0


def test_pipeline_emits_current_version_row():
    llm = {
        **{k: v for k, v in _sem().model_dump().items() if k != "semantic_source"},
        "evidence_quote": "We keep getting UHC denials for RFA.",
    }
    with patch.object(step2_semantic, "analyze_semantics_llm", return_value=llm):
        row = pipeline_module.run_pipeline(
            source_item_id="p1", title="",
            text="We keep getting UHC denials for RFA and our AR is increasing. Has anyone found a solution?",
            created_at=None)
    assert (row.analysis_version, row.scoring_version) == (ANALYSIS_VERSION, SCORING_VERSION)
    assert row.final_score == row.score_breakdown["final_score"]
    assert row.score_breakdown["weights"] == WEIGHTS
    assert row.score_breakdown["llm_points"]["seeking"] == SEEKING_POINTS["L2"]
    assert row.final_score > 80
