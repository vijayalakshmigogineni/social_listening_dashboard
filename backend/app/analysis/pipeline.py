"""
Orchestrates Steps 1-6/7 for a single normalized record into one
AnalysisResult. Each step's output feeds the next; nothing downstream
re-reads raw text where a structured field already answers the question
(scoring in particular only touches step outputs + a few deterministic
severity markers, never re-classifies).
"""

from __future__ import annotations

from datetime import datetime

from app.analysis.step1_relevance import classify_rcm_relevance, scan_keywords
from app.analysis.step2_problem_evidence import classify_problem_evidence
from app.analysis.step3_taxonomy import classify_taxonomy
from app.analysis.step4_speaker_stance_seeking import classify_context
from app.analysis.step5_evidence_confidence import build_evidence
from app.analysis.step6_scoring import score_record
from app.analysis.step6_scoring_v2 import score_record_v2
from app.schemas.analysis import (
    ANALYSIS_VERSION,
    ANALYSIS_VERSION_V2,
    SCORING_VERSION,
    SCORING_VERSION_V2,
    AnalysisResult,
    Step1Relevance,
    Step2ProblemEvidence,
    Step3Taxonomy,
    Step4Context,
    Step5Evidence,
    ScoreBreakdown,
    ScoreBreakdownV2,
)


def build_text(title: str | None, text: str | None) -> str:
    title = (title or "").strip()
    body = (text or "").strip()
    if not body or body == title:
        return title
    return f"{title}\n{body}".strip()


def _assemble(
    source_item_id: str,
    step1: Step1Relevance,
    step2: Step2ProblemEvidence,
    step3: Step3Taxonomy,
    step4: Step4Context,
    step5: Step5Evidence,
    score: ScoreBreakdown | ScoreBreakdownV2,
    analysis_version: str = ANALYSIS_VERSION,
    scoring_version: str = SCORING_VERSION,
) -> AnalysisResult:
    """Steps 1-5 are shared between scoring versions; only the score and the
    two version strings differ, which is why the scorer is a parameter."""
    return AnalysisResult(
        source_item_id=source_item_id,
        analysis_version=analysis_version,
        scoring_version=scoring_version,
        rcm_relevant=step1.rcm_relevant,
        rcm_relevance_confidence=step1.rcm_relevance_confidence,
        problem_evidence=step2.problem_evidence,
        first_person=step2.first_person,
        problem_confidence=step2.problem_confidence,
        problem_category=step3.problem_category,
        procedure_tags=step3.procedure_tags,
        payer_tags=step3.payer_tags,
        denial_reason_tags=step3.denial_reason_tags,
        specialty=step3.specialty,
        mentioned_organization=step3.mentioned_organization,
        cpt_hcpcs_codes=step3.cpt_hcpcs_codes,
        speaker_type=step4.speaker_type,
        content_stance=step4.content_stance,
        seeking_level=step4.seeking_level,
        evidence_quote=step5.evidence_quote,
        confidence=step5.confidence,
        score_breakdown=score.model_dump(),
        final_score=score.final_score,
    )


def _run_stages(
    full_text: str,
    created_at: datetime | None,
    matched_keywords: list[str] | None,
) -> tuple[
    Step1Relevance, Step2ProblemEvidence, Step3Taxonomy, Step4Context, Step5Evidence,
    ScoreBreakdown, ScoreBreakdownV2,
]:
    step1 = classify_rcm_relevance(
        full_text, matched_keywords if matched_keywords is not None else scan_keywords(full_text)
    )

    if not step1.rcm_relevant:
        # Short-circuit: everything downstream assumes RCM relevance. A
        # non-relevant record still gets a full, schema-valid row (so it's
        # queryable/debuggable), just with neutral/empty downstream fields
        # and a final_score of 0 -- it will not surface in ranked views.
        step2 = Step2ProblemEvidence(
            problem_evidence=False,
            first_person=False,
            problem_confidence=step1.rcm_relevance_confidence,
        )
        step3 = Step3Taxonomy()
        step4 = Step4Context(content_stance="neutral")
    else:
        step2 = classify_problem_evidence(full_text)
        step3 = classify_taxonomy(full_text)
        step4 = classify_context(full_text)

    step5 = build_evidence(full_text, step1, step2, step3, step4)
    score = score_record(full_text, created_at, step1, step2, step3, step4, step5)
    # v2 scores every record, including non-relevant ones: its relevance floor
    # is graded rather than a gate, so the short-circuit above must not skip it.
    # It reads seeking_level from Step 4 (None for short-circuited records,
    # which maps to the default intent tier) plus the text itself.
    score_v2 = score_record_v2(full_text, step4.seeking_level)

    return step1, step2, step3, step4, step5, score, score_v2


def run_pipeline(
    source_item_id: str,
    title: str | None,
    text: str | None,
    created_at: datetime | None,
    matched_keywords: list[str] | None = None,
) -> AnalysisResult:
    """The v1 row. Unchanged behaviour -- existing callers are unaffected."""
    full_text = build_text(title, text)
    stages = _run_stages(full_text, created_at, matched_keywords)
    step1, step2, step3, step4, step5, score, _ = stages
    return _assemble(source_item_id, step1, step2, step3, step4, step5, score)


def run_pipeline_all_versions(
    source_item_id: str,
    title: str | None,
    text: str | None,
    created_at: datetime | None,
    matched_keywords: list[str] | None = None,
) -> list[AnalysisResult]:
    """Both scoring versions from a single pass over Steps 1-5.

    Steps 1-5 are by far the expensive part (two zero-shot classifications per
    relevant record), so scoring twice off one pass is what makes storing v1
    and v2 side by side affordable.
    """
    full_text = build_text(title, text)
    step1, step2, step3, step4, step5, score, score_v2 = _run_stages(
        full_text, created_at, matched_keywords
    )
    return [
        _assemble(source_item_id, step1, step2, step3, step4, step5, score),
        _assemble(
            source_item_id, step1, step2, step3, step4, step5, score_v2,
            analysis_version=ANALYSIS_VERSION_V2,
            scoring_version=SCORING_VERSION_V2,
        ),
    ]


def explain_pipeline(
    title: str | None,
    text: str | None,
    created_at: datetime | None,
    matched_keywords: list[str] | None = None,
) -> dict:
    """For the Pipeline/Debug tab: every stage's raw input/output, not just
    the merged final row."""
    full_text = build_text(title, text)
    step1, step2, step3, step4, step5, score, score_v2 = _run_stages(
        full_text, created_at, matched_keywords
    )

    return {
        "input_text": full_text,
        "step1_rcm_relevance": step1.model_dump(),
        "step2_problem_evidence": step2.model_dump(),
        "step3_taxonomy": step3.model_dump(),
        "step4_context": step4.model_dump(),
        "step5_evidence_confidence": step5.model_dump(),
        "step6_7_scoring": score.model_dump(),
        "step6_7_scoring_v2": score_v2.model_dump(),
        "analysis_version": ANALYSIS_VERSION,
        "scoring_version": SCORING_VERSION,
        "analysis_version_v2": ANALYSIS_VERSION_V2,
        "scoring_version_v2": SCORING_VERSION_V2,
    }
