"""
Step 6 -- ProbePS Opportunity Score.

Three components, each normalized to 0-100, combined by fixed weights:

    LLM Score   (65%)  human-like opportunity assessment from the Step 2 LLM
                       call: real problem, own experience, what they seek,
                       business impact, recurrence, ProbePS fit
    RCM Score   (20%)  Step 1 relevance confidence + severity of the primary
                       problem category
    Step3 Score (15%)  deterministic payer / procedure / code specificity

    final = 0.65 * LLM + 0.20 * RCM + 0.15 * Step3          (0-100)

The weights encode the product goal: a post can be highly RCM-relevant and
specific ("Which CPT code do I use for RFA?") yet a weak ProbePS opportunity;
only the LLM component can tell that apart from "We keep getting UHC denials
for RFA and our AR is climbing -- anyone found a fix?". No multipliers and no
bonuses -- only two explicit caps:

  - LLM cap:   opportunity_type informational_only / not_an_opportunity
               caps the LLM score at NON_OPPORTUNITY_LLM_CAP
  - final cap: a post without problem_evidence cannot exceed NO_PROBLEM_CAP,
               so RCM vocabulary and taxonomy hits alone never make a
               generic post look like a strong opportunity

A post that Step 1 found not RCM-relevant scores 0 on every component.

Confidence is used only inside the LLM component (points x the LLM's
confidence for that field). Each signal is scored in exactly one component:
problem_recurring only in LLM, category severity only in RCM, payer /
procedure only in Step 3.

The point values are an initial design, NOT fitted to data; validate them
against the gold set before trusting the ranking. Deterministic given
(Step 1, Step 2 semantic output, Step 3 taxonomy).
"""

from __future__ import annotations

from typing import Optional

from app.schemas.analysis import (
    LlmPoints,
    RcmPoints,
    ScoreBreakdownOpportunity,
    Step1Relevance,
    Step2Semantic,
    Step3Points,
    Step3Taxonomy,
)

WEIGHTS = {"llm": 0.65, "rcm": 0.20, "step3": 0.15}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

# ---------------------------------------------------------------------------
# LLM component (max 25 + 10 + 20 + 15 + 5 + 25 = 100)
# ---------------------------------------------------------------------------
PROBLEM_EVIDENCE_MAX = 25.0
FIRST_PERSON_MAX = 10.0
SEEKING_POINTS = {"L0": 4.0, "L1": 8.0, "L2": 14.0, "L3": 20.0}
BUSINESS_IMPACT_POINTS = {"none": 0.0, "low": 5.0, "moderate": 10.0, "high": 15.0}
RECURRING_POINTS = 5.0
PROBEPS_FIT_POINTS = {"none": 0.0, "low": 8.0, "moderate": 16.0, "high": 25.0}
LLM_MAX = (PROBLEM_EVIDENCE_MAX + FIRST_PERSON_MAX + max(SEEKING_POINTS.values())
           + max(BUSINESS_IMPACT_POINTS.values()) + RECURRING_POINTS
           + max(PROBEPS_FIT_POINTS.values()))
assert LLM_MAX == 100.0

NON_OPPORTUNITY_TYPES = {"informational_only", "not_an_opportunity"}
NON_OPPORTUNITY_LLM_CAP = 30.0

# ---------------------------------------------------------------------------
# RCM component (max 50 + 50 = 100)
# ---------------------------------------------------------------------------
RELEVANCE_MAX = 50.0
CATEGORY_SEVERITY_MAX = 50.0
# PRIMARY category only (taxonomy is multi-label keyword matching and cannot
# tell whether two labels describe the same event). procedure_device_access
# has no severity weight. Ties resolve by list order.
SEVERITY_BY_CATEGORY = [
    ("denials_claims_friction", 8.0),
    ("authorization_utilization_management", 7.0),
    ("reimbursement_payment", 7.0),
    ("coverage_policy", 6.0),
    ("documentation_medical_necessity", 6.0),
]
SEVERITY_TOP = max(points for _, points in SEVERITY_BY_CATEGORY)

# ---------------------------------------------------------------------------
# Step 3 component (raw max 7 + 4 + 3 + 3 + 2 + 1 = 20, scaled to 100)
# ---------------------------------------------------------------------------
CATEGORY_POINTS = 7.0
PAYER_POINTS = 4.0
PROCEDURE_POINTS = 3.0
DENIAL_REASON_POINTS = 3.0
CODE_POINTS = 2.0
SPECIALTY_POINTS = 1.0
SPECIFICITY_MAX = 20.0

NO_PROBLEM_CAP = 30.0  # final-score cap when problem_evidence is false

# ---------------------------------------------------------------------------
# Opportunity definition (Overview KPIs + the Explorer "opportunity" filter
# both use exactly this). PROVISIONAL: set from the real score distribution
# and the gold set before relying on the KPI.
# ---------------------------------------------------------------------------
OPPORTUNITY_THRESHOLD = 40.0


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


def llm_component(semantic: Optional[Step2Semantic]) -> tuple[float, LlmPoints, bool]:
    """(llm_score 0-100, its points, whether the non-opportunity cap applied)."""
    if semantic is None:
        return 0.0, LlmPoints(problem_evidence=0, first_person=0, seeking=0,
                              business_impact=0, recurring=0, probeps_fit=0), False
    level = semantic.seeking_level
    points = LlmPoints(
        problem_evidence=_weighted(semantic.problem_evidence, PROBLEM_EVIDENCE_MAX,
                                   semantic.problem_confidence),
        first_person=_weighted(semantic.first_person, FIRST_PERSON_MAX,
                               semantic.first_person_confidence),
        seeking=_weighted(level is not None, SEEKING_POINTS.get(level or "", 0.0),
                          semantic.seeking_confidence),
        business_impact=_weighted(semantic.business_impact is not None,
                                  BUSINESS_IMPACT_POINTS.get(semantic.business_impact or "", 0.0),
                                  semantic.impact_confidence),
        # A recurring *problem* needs a problem to recur.
        recurring=RECURRING_POINTS if (semantic.problem_recurring and semantic.problem_evidence) else 0.0,
        probeps_fit=_weighted(semantic.probeps_fit is not None,
                              PROBEPS_FIT_POINTS.get(semantic.probeps_fit or "", 0.0),
                              semantic.fit_confidence),
    )
    score = round(sum(points.model_dump().values()), 4)
    capped = semantic.opportunity_type in NON_OPPORTUNITY_TYPES and score > NON_OPPORTUNITY_LLM_CAP
    return (NON_OPPORTUNITY_LLM_CAP if capped else score), points, capped


def rcm_component(step1: Step1Relevance, step3: Step3Taxonomy) -> tuple[float, RcmPoints]:
    primary, severity = primary_problem_category(step3.problem_category)
    if not step1.rcm_relevant:
        return 0.0, RcmPoints(relevance=0, category_severity=0, primary_problem_category=primary)
    points = RcmPoints(
        relevance=round(RELEVANCE_MAX * step1.rcm_relevance_confidence, 4),
        category_severity=round(CATEGORY_SEVERITY_MAX * severity / SEVERITY_TOP, 4),
        primary_problem_category=primary,
    )
    return round(points.relevance + points.category_severity, 4), points


def step3_component(step3: Step3Taxonomy) -> tuple[float, Step3Points]:
    parts = dict(
        category=CATEGORY_POINTS if step3.problem_category else 0.0,
        payer=PAYER_POINTS if step3.payer_tags else 0.0,
        procedure=PROCEDURE_POINTS if step3.procedure_tags else 0.0,
        denial_reason=DENIAL_REASON_POINTS if step3.denial_reason_tags else 0.0,
        code=CODE_POINTS if step3.cpt_hcpcs_codes else 0.0,
        specialty=SPECIALTY_POINTS if step3.specialty else 0.0,
    )
    total = sum(parts.values())
    return round(total / SPECIFICITY_MAX * 100, 4), Step3Points(**parts, total=total)


def combine(llm_score: float, rcm_score: float, step3_score: float,
            problem_evidence: bool) -> tuple[float, float, bool]:
    """(final, pre_cap, cap_applied) -- the 65/20/15 weighting plus the
    no-problem-evidence cap. Pure arithmetic; every input is 0-100."""
    pre_cap = round(WEIGHTS["llm"] * llm_score + WEIGHTS["rcm"] * rcm_score
                    + WEIGHTS["step3"] * step3_score, 4)
    capped = (not problem_evidence) and pre_cap > NO_PROBLEM_CAP
    return (NO_PROBLEM_CAP if capped else pre_cap), pre_cap, capped


def score_opportunity(
    step1: Step1Relevance, semantic: Optional[Step2Semantic], step3: Step3Taxonomy
) -> ScoreBreakdownOpportunity:
    """semantic is None when Step 1 short-circuited (not RCM-relevant)."""
    llm_score, llm_points, llm_capped = llm_component(semantic)
    rcm_score, rcm_points = rcm_component(step1, step3)
    step3_score, step3_points = step3_component(step3)
    if not step1.rcm_relevant:
        llm_score = rcm_score = step3_score = 0.0

    problem_evidence = bool(semantic and semantic.problem_evidence)
    final, pre_cap, capped = combine(llm_score, rcm_score, step3_score, problem_evidence)

    reasons = []
    if llm_capped:
        reasons.append(f"LLM classified the post as {semantic.opportunity_type}: "
                       f"LLM score capped at {NON_OPPORTUNITY_LLM_CAP:g}")
    if capped:
        reasons.append(f"no problem evidence: final score capped at {NO_PROBLEM_CAP:g}")

    return ScoreBreakdownOpportunity(
        llm_score=llm_score,
        rcm_score=rcm_score,
        step3_score=step3_score,
        weights=dict(WEIGHTS),
        llm_contribution=round(WEIGHTS["llm"] * llm_score, 4),
        rcm_contribution=round(WEIGHTS["rcm"] * rcm_score, 4),
        step3_contribution=round(WEIGHTS["step3"] * step3_score, 4),
        llm_points=llm_points,
        rcm_points=rcm_points,
        step3_points=step3_points,
        llm_cap_applied=llm_capped,
        cap_applied=capped,
        cap_reason="; ".join(reasons) or None,
        pre_cap_score=pre_cap,
        final_score=final,
        llm_source=semantic.semantic_source if semantic is not None else None,
        llm_assessment=semantic.model_dump() if semantic is not None else None,
    )


def is_opportunity(final_score: Optional[float], problem_evidence: Optional[bool]) -> bool:
    """Python mirror of the SQL predicate in app/api/opportunity.py."""
    return bool(problem_evidence) and final_score is not None and final_score >= OPPORTUNITY_THRESHOLD
