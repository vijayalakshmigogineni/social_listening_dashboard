"""
Step 6/7 -- Scoring.

The scoring engine, not any single stage, decides whether a record is worth
surfacing AND how it ranks. There is deliberately no hard formula like
"SLD_candidate = RCM_relevant AND seeking_level" -- a supplying/L0 record
(e.g. a meaningful payer policy update) can still score well.

Every component score is computed from OBSERVABLE FEATURES that Steps 1-5
already extracted -- this stage never re-reads or re-classifies the raw
text itself, it only looks at the structured outputs and, for severity
markers, the text (for deterministic keyword presence only, not judgment).

Weights below are ROUGH V1 VALUES, explicitly provisional, and are kept in
one place (this module's top-level constants) so they are easy to find and
recalibrate once real pipeline output has been reviewed.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.analysis.lexicons import (
    DURATION_MARKERS,
    FINANCIAL_IMPACT_MARKERS,
    OPERATIONAL_IMPACT_MARKERS,
    REPETITION_MARKERS,
    VOLUME_MARKERS,
)
from app.analysis.text_signals import find_hits
from app.schemas.analysis import (
    SCORING_VERSION,
    ScoreBreakdown,
    Step1Relevance,
    Step2ProblemEvidence,
    Step3Taxonomy,
    Step4Context,
    Step5Evidence,
)

# ---------------------------------------------------------------------------
# Rough V1 weights -- see module docstring. Normalize-to-100 left as a
# frontend/display concern; the raw base score max is 95 by design.
# ---------------------------------------------------------------------------
PROBLEM_STRENGTH_MAX = 20
MARKET_RELEVANCE_MAX = 20
INTENT_STRENGTH_MAX = 30
SPECIFICITY_MAX = 15
SEVERITY_MAX = 10

INTENT_STRENGTH_BY_LEVEL = {"L0": 5, "L1": 10, "L2": 20, "L3": 30, None: 0}

# Recency half-life (days) by seeking level -- policy/coverage-type signals
# (no seeking level, i.e. supplying content) are treated like L1/L0: useful
# for longer than an active L3 vendor-seeking post, which goes stale fast.
RECENCY_HALF_LIFE_DAYS = {"L3": 45, "L2": 90, "L1": 180, "L0": 180, None: 180}
RECENCY_FLOOR = 0.15


def _has_any(text_lower: str, markers: list[str]) -> bool:
    return bool(find_hits(text_lower, markers))


def compute_problem_strength(
    text_lower: str, step2: Step2ProblemEvidence, step3: Step3Taxonomy
) -> float:
    if not step2.problem_evidence:
        return 0.0

    score = 5.0  # clear_problem_evidence
    if step2.first_person:
        score += 3.0
    if step3.problem_category or step3.payer_tags or step3.procedure_tags:
        score += 3.0  # specific_problem: it names a concrete category/payer/procedure
    if _has_any(text_lower, REPETITION_MARKERS):
        score += 4.0
    if _has_any(text_lower, OPERATIONAL_IMPACT_MARKERS):
        score += 5.0
    return min(score, PROBLEM_STRENGTH_MAX)


def compute_market_relevance(step1: Step1Relevance, step3: Step3Taxonomy) -> float:
    if not step1.rcm_relevant:
        return 0.0

    score = 5.0  # RCM relevance itself
    if step3.mentioned_organization or step3.specialty:
        score += 5.0  # practice/business operational context
    if step3.problem_category or step3.payer_tags or step3.denial_reason_tags:
        score += 5.0  # specific RCM issue named
    if step3.problem_category and (step3.payer_tags or step3.denial_reason_tags):
        score += 5.0  # a clear, concrete RCM business need, not just topic-adjacent
    return min(score, MARKET_RELEVANCE_MAX)


def compute_intent_strength(step4: Step4Context) -> float:
    return float(INTENT_STRENGTH_BY_LEVEL.get(step4.seeking_level, 0))


def compute_specificity(step3: Step3Taxonomy) -> float:
    score = 0.0
    if step3.problem_category:
        score += 3.0
    if step3.payer_tags:
        score += 2.0
    if step3.procedure_tags:
        score += 2.0
    if step3.denial_reason_tags:
        score += 3.0
    if step3.cpt_hcpcs_codes:
        score += 2.0
    if step3.mentioned_organization:
        score += 2.0
    if step3.specialty:
        score += 1.0
    return min(score, SPECIFICITY_MAX)


def compute_severity(text_lower: str) -> float:
    score = 0.0
    if _has_any(text_lower, REPETITION_MARKERS):
        score += 2.0
    if _has_any(text_lower, DURATION_MARKERS):
        score += 2.0
    if _has_any(text_lower, VOLUME_MARKERS):
        score += 2.0
    if _has_any(text_lower, FINANCIAL_IMPACT_MARKERS):
        score += 2.0
    if _has_any(text_lower, OPERATIONAL_IMPACT_MARKERS):
        score += 2.0
    return min(score, SEVERITY_MAX)


def compute_recency_factor(created_at: datetime | None, seeking_level: str | None) -> float:
    if created_at is None:
        return RECENCY_FLOOR
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (datetime.now(timezone.utc) - created_at).total_seconds() / 86400)
    half_life = RECENCY_HALF_LIFE_DAYS.get(seeking_level, 180)
    factor = 0.5 ** (age_days / half_life)
    return round(max(RECENCY_FLOOR, factor), 4)


def score_record(
    text: str,
    created_at: datetime | None,
    step1: Step1Relevance,
    step2: Step2ProblemEvidence,
    step3: Step3Taxonomy,
    step4: Step4Context,
    step5: Step5Evidence,
) -> ScoreBreakdown:
    text_lower = (text or "").lower()

    problem_strength = compute_problem_strength(text_lower, step2, step3)
    market_relevance = compute_market_relevance(step1, step3)
    intent_strength = compute_intent_strength(step4)
    specificity = compute_specificity(step3)
    severity = compute_severity(text_lower)

    base_score = problem_strength + market_relevance + intent_strength + specificity + severity
    recency_factor = compute_recency_factor(created_at, step4.seeking_level)

    final_score = round(base_score * step5.confidence * recency_factor, 4)

    return ScoreBreakdown(
        problem_strength=problem_strength,
        market_relevance=market_relevance,
        intent_strength=intent_strength,
        specificity=specificity,
        severity=severity,
        base_score=round(base_score, 4),
        confidence=step5.confidence,
        recency_factor=recency_factor,
        final_score=final_score,
    )


__all__ = ["score_record", "SCORING_VERSION"]
