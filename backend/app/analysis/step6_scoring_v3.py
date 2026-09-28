"""
Step 6/7 -- Scoring, v3 (Experiment 2).

Three additive components and nothing else -- no multipliers, no separate
confidence factor, no speaker or stance points:

    Semantic Score   (0-50)  confidence-weighted Step 2 signals
    Problem Severity (0-30)  primary taxonomy problem category + recurring
    RCM Specificity  (0-20)  deterministic taxonomy signals, each counted once

    v3 = Semantic Score + Problem Severity + RCM Specificity

One business sanity rule: a post without problem_evidence cannot exceed 30,
so RCM vocabulary, payers, procedures or codes alone cannot make a generic
or informational post look like a strong opportunity.

Confidence is used ONLY inside the four semantic contributions (points x the
LLM's confidence for that field). It is never applied to the total.

Each variable is scored in exactly one place: payer and procedure only in
RCM Specificity; seeking_level only in Semantic Score (content_stance is not
scored -- seeking_level already carries the intent that matters);
speaker_type and problem_current are analysis fields with zero score weight.

Weights are the fixed Experiment 2 design and have NOT been fitted to the
gold set. Deterministic given (Step 2 semantic output, Step 3 taxonomy).
"""

from __future__ import annotations

from typing import Optional

from app.schemas.analysis import (
    SCORING_VERSION_V3,
    ScoreBreakdownV3,
    Step2Semantic,
    Step3Taxonomy,
)

# ---------------------------------------------------------------------------
# Semantic Score (max 15 + 8 + 17 + 10 = 50)
# ---------------------------------------------------------------------------
PROBLEM_EVIDENCE_MAX = 15.0
FIRST_PERSON_MAX = 8.0
OPERATIONAL_IMPACT_MAX = 10.0
SEEKING_POINTS = {"L0": 3.0, "L1": 8.0, "L2": 12.0, "L3": 17.0}

# ---------------------------------------------------------------------------
# Problem Severity -- PRIMARY category only (taxonomy is multi-label keyword
# matching and cannot tell whether two labels describe the same event, so
# summing them would double-count e.g. "denied for medical necessity").
# Coverage/policy and documentation/medical necessity are one spec group.
# procedure_device_access has no severity weight in the spec: it scores 0
# here (it still earns the category point in RCM Specificity).
# Ties (auth vs reimbursement, both 7) resolve by this list's order.
# ---------------------------------------------------------------------------
SEVERITY_BY_CATEGORY = [
    ("denials_claims_friction", 8.0),
    ("authorization_utilization_management", 7.0),
    ("reimbursement_payment", 7.0),
    ("coverage_policy", 6.0),
    ("documentation_medical_necessity", 6.0),
]
RECURRING_POINTS = 2.0

# ---------------------------------------------------------------------------
# RCM Specificity (max 7 + 4 + 3 + 3 + 2 + 1 = 20)
# ---------------------------------------------------------------------------
CATEGORY_POINTS = 7.0
PAYER_POINTS = 4.0
PROCEDURE_POINTS = 3.0
DENIAL_REASON_POINTS = 3.0
CODE_POINTS = 2.0
SPECIALTY_POINTS = 1.0

SANITY_CAP = 30.0  # applies when problem_evidence is false


def _weighted(fired: bool, points: float, confidence: Optional[float]) -> float:
    """points x confidence when the signal fired. A fired signal with no
    confidence (legacy-fallback records) contributes 0 rather than an
    invented default."""
    if not fired or confidence is None:
        return 0.0
    return round(points * confidence, 4)


def primary_problem_category(categories: list[str]) -> tuple[Optional[str], float]:
    for category, points in SEVERITY_BY_CATEGORY:
        if category in categories:
            return category, points
    return None, 0.0


def score_record_v3(semantic: Optional[Step2Semantic], step3: Step3Taxonomy) -> ScoreBreakdownV3:
    """semantic is None when Step 1 short-circuited (not RCM-relevant)."""
    # --- Semantic Score ---------------------------------------------------
    if semantic is None:
        problem_pts = fp_pts = seeking_pts = impact_pts = 0.0
        problem_evidence = recurring = False
    else:
        problem_evidence = semantic.problem_evidence
        recurring = semantic.problem_recurring
        problem_pts = _weighted(problem_evidence, PROBLEM_EVIDENCE_MAX, semantic.problem_confidence)
        fp_pts = _weighted(semantic.first_person, FIRST_PERSON_MAX, semantic.first_person_confidence)
        level = semantic.seeking_level
        seeking_pts = _weighted(level is not None, SEEKING_POINTS.get(level or "", 0.0),
                                semantic.seeking_confidence)
        impact_pts = _weighted(semantic.operational_impact, OPERATIONAL_IMPACT_MAX,
                               semantic.operational_impact_confidence)
    semantic_score = round(problem_pts + fp_pts + seeking_pts + impact_pts, 4)

    # --- Problem Severity -------------------------------------------------
    primary, primary_pts = primary_problem_category(step3.problem_category)
    recurring_pts = RECURRING_POINTS if recurring else 0.0
    problem_severity = primary_pts + recurring_pts

    # --- RCM Specificity --------------------------------------------------
    category_pts = CATEGORY_POINTS if step3.problem_category else 0.0
    payer_pts = PAYER_POINTS if step3.payer_tags else 0.0
    procedure_pts = PROCEDURE_POINTS if step3.procedure_tags else 0.0
    denial_pts = DENIAL_REASON_POINTS if step3.denial_reason_tags else 0.0
    code_pts = CODE_POINTS if step3.cpt_hcpcs_codes else 0.0
    specialty_pts = SPECIALTY_POINTS if step3.specialty else 0.0
    rcm_specificity = category_pts + payer_pts + procedure_pts + denial_pts + code_pts + specialty_pts

    base_score = round(semantic_score + problem_severity + rcm_specificity, 4)
    cap_applied = (not problem_evidence) and base_score > SANITY_CAP
    final_score = min(base_score, SANITY_CAP) if not problem_evidence else base_score

    return ScoreBreakdownV3(
        problem_evidence_points=problem_pts,
        first_person_points=fp_pts,
        seeking_points=seeking_pts,
        operational_impact_points=impact_pts,
        semantic_score=semantic_score,
        primary_problem_category=primary,
        primary_category_points=primary_pts,
        recurring_points=recurring_pts,
        problem_severity=problem_severity,
        category_points=category_pts,
        payer_points=payer_pts,
        procedure_points=procedure_pts,
        denial_reason_points=denial_pts,
        code_points=code_pts,
        specialty_points=specialty_pts,
        rcm_specificity=rcm_specificity,
        base_score=base_score,
        sanity_cap_applied=cap_applied,
        final_score=round(final_score, 4),
    )


__all__ = ["score_record_v3", "SCORING_VERSION_V3"]
