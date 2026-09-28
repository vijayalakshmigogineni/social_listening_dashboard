"""
Step 6/7 v3 scoring (Experiment 2): Semantic (0-50) + Problem Severity +
RCM Specificity (0-20), additive only, sanity cap of 30 without problem
evidence. Pure function over Step 2 + Step 3 outputs -- no text, no LLM.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.analysis import pipeline as pipeline_module
from app.analysis import step2_semantic
from app.analysis.step6_scoring_v3 import SANITY_CAP, score_record_v3
from app.schemas.analysis import (
    ANALYSIS_VERSION_V3,
    SCORING_VERSION_V3,
    Step2Semantic,
    Step3Taxonomy,
)


def _sem(**kw) -> Step2Semantic:
    base = dict(
        problem_evidence=True, problem_current=True, problem_recurring=True,
        first_person=True, operational_impact=True,
        speaker_type="practice_side", content_stance="seeking", seeking_level="L2",
        evidence_quote="x", semantic_source="llm",
        problem_confidence=0.95, first_person_confidence=0.97,
        seeking_confidence=0.90, operational_impact_confidence=0.92,
        speaker_confidence=0.9, stance_confidence=0.9,
    )
    base.update(kw)
    return Step2Semantic(**base)


SPEC_TAXONOMY = Step3Taxonomy(
    problem_category=["denials_claims_friction"], payer_tags=["Aetna"], procedure_tags=["Intracept"],
)


def test_spec_worked_example_scores_66_01():
    # "Our practice keeps getting Aetna denials for Intracept. We spend hours
    # every week fixing them. Has anyone found a better way?"
    bd = score_record_v3(_sem(), SPEC_TAXONOMY)
    assert bd.problem_evidence_points == 14.25
    assert bd.first_person_points == 7.76
    assert bd.seeking_points == 10.8
    assert bd.operational_impact_points == 9.2
    assert bd.semantic_score == pytest.approx(42.01)
    assert (bd.primary_problem_category, bd.primary_category_points, bd.recurring_points) == (
        "denials_claims_friction", 8.0, 2.0)
    assert bd.problem_severity == 10.0
    assert (bd.category_points, bd.payer_points, bd.procedure_points) == (7.0, 4.0, 3.0)
    assert bd.rcm_specificity == 14.0
    assert bd.final_score == pytest.approx(66.01)
    assert bd.base_score == bd.final_score and not bd.sanity_cap_applied


@pytest.mark.parametrize("level,points", [("L0", 3), ("L1", 8), ("L2", 12), ("L3", 17), (None, 0)])
def test_seeking_points_are_confidence_weighted(level, points):
    bd = score_record_v3(_sem(seeking_level=level, seeking_confidence=0.5), Step3Taxonomy())
    assert bd.seeking_points == points * 0.5


def test_semantic_score_maxes_at_50():
    bd = score_record_v3(_sem(seeking_level="L3", problem_confidence=1, first_person_confidence=1,
                              seeking_confidence=1, operational_impact_confidence=1), Step3Taxonomy())
    assert bd.semantic_score == 50.0


def test_rcm_specificity_counts_each_signal_once_and_maxes_at_20():
    tax = Step3Taxonomy(
        problem_category=["denials_claims_friction", "coverage_policy"],
        payer_tags=["Aetna", "Cigna", "UHC"], procedure_tags=["a", "b"], denial_reason_tags=["CO-50", "CO-16"],
        cpt_hcpcs_codes=["64628", "J3490"], specialty="pain_management",
    )
    bd = score_record_v3(_sem(), tax)
    assert (bd.category_points, bd.payer_points, bd.procedure_points,
            bd.denial_reason_points, bd.code_points, bd.specialty_points) == (7, 4, 3, 3, 2, 1)
    assert bd.rcm_specificity == 20.0


def test_payer_and_procedure_score_only_in_specificity():
    without = score_record_v3(_sem(), Step3Taxonomy(problem_category=["denials_claims_friction"]))
    with_both = score_record_v3(_sem(), SPEC_TAXONOMY)
    assert with_both.final_score - without.final_score == pytest.approx(4.0 + 3.0)
    assert with_both.semantic_score == without.semantic_score
    assert with_both.problem_severity == without.problem_severity


def test_severity_uses_primary_category_only():
    # "Aetna denials because of medical necessity": denial is primary; the
    # coverage/medical-necessity label is not added on top.
    tax = Step3Taxonomy(problem_category=["documentation_medical_necessity", "denials_claims_friction"])
    bd = score_record_v3(_sem(problem_recurring=False), tax)
    assert (bd.primary_problem_category, bd.problem_severity) == ("denials_claims_friction", 8.0)


@pytest.mark.parametrize("category,points", [
    ("denials_claims_friction", 8), ("authorization_utilization_management", 7),
    ("reimbursement_payment", 7), ("coverage_policy", 6), ("documentation_medical_necessity", 6),
    ("procedure_device_access", 0),
])
def test_severity_weights(category, points):
    bd = score_record_v3(_sem(problem_recurring=False), Step3Taxonomy(problem_category=[category]))
    assert bd.primary_category_points == points


def test_sanity_cap_without_problem_evidence():
    # A taxonomy-rich generic question cannot become a high opportunity.
    tax = Step3Taxonomy(problem_category=["denials_claims_friction"], payer_tags=["Aetna"],
                        procedure_tags=["x"], denial_reason_tags=["CO-50"], cpt_hcpcs_codes=["64628"],
                        specialty="pain")
    bd = score_record_v3(_sem(problem_evidence=False, seeking_level="L3"), tax)
    assert bd.base_score > SANITY_CAP
    assert bd.final_score == SANITY_CAP and bd.sanity_cap_applied


def test_no_speaker_or_stance_effect():
    a = score_record_v3(_sem(speaker_type="practice_side", content_stance="seeking"), SPEC_TAXONOMY)
    for speaker in ["vendor", "payer_side", "patient", "educator_media", "unknown"]:
        for stance in ["supplying", "neutral", "mixed"]:
            b = score_record_v3(_sem(speaker_type=speaker, content_stance=stance), SPEC_TAXONOMY)
            assert b.final_score == a.final_score


def test_problem_current_has_no_weight():
    assert (score_record_v3(_sem(problem_current=True), SPEC_TAXONOMY).final_score
            == score_record_v3(_sem(problem_current=False), SPEC_TAXONOMY).final_score)


def test_no_confidence_multiplier_on_total():
    # Lowering an unrelated (speaker/stance) confidence changes nothing; only
    # the four semantic fields' own confidences matter.
    a = score_record_v3(_sem(speaker_confidence=0.1, stance_confidence=0.1), SPEC_TAXONOMY)
    b = score_record_v3(_sem(speaker_confidence=1.0, stance_confidence=1.0), SPEC_TAXONOMY)
    assert a.final_score == b.final_score
    assert a.final_score == pytest.approx(a.semantic_score + a.problem_severity + a.rcm_specificity)


def test_not_relevant_scores_zero():
    bd = score_record_v3(None, Step3Taxonomy())
    assert bd.final_score == 0.0 and bd.semantic_score == 0.0


def test_missing_confidence_contributes_zero():
    bd = score_record_v3(_sem(semantic_source="fallback", first_person_confidence=None,
                              operational_impact_confidence=None), Step3Taxonomy())
    assert bd.first_person_points == 0.0 and bd.operational_impact_points == 0.0


def test_pipeline_emits_one_v3_row():
    llm = {
        "problem_evidence": True, "problem_current": True, "problem_recurring": True,
        "first_person": True, "operational_impact": True,
        "speaker_type": "practice_side", "content_stance": "seeking", "seeking_level": "L2",
        "evidence_quote": "We keep getting claim denials from Aetna.",
        "problem_confidence": 0.95, "first_person_confidence": 0.97,
        "operational_impact_confidence": 0.92, "speaker_confidence": 0.9,
        "stance_confidence": 0.9, "seeking_confidence": 0.9,
    }
    with patch.object(step2_semantic, "analyze_semantics_llm", return_value=llm):
        v3 = pipeline_module.run_pipeline(
            source_item_id="p1", title="", text="We keep getting claim denials from Aetna. Any advice?",
            created_at=None)
    assert v3.analysis_version == ANALYSIS_VERSION_V3
    assert v3.scoring_version == SCORING_VERSION_V3
    assert v3.final_score == v3.score_breakdown["final_score"]
    assert {"semantic_score", "problem_severity", "rcm_specificity", "base_score"} <= set(v3.score_breakdown)
    assert v3.seeking_level == "L2"
