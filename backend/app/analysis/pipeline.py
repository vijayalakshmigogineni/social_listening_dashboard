"""
Orchestrates the analysis stages for a single normalized record into one
AnalysisResult per scoring version:

  1. RCM Relevance             -- rule gate (clearly_relevant | ambiguous);
                                  the LLM resolves only ambiguous records
  2. Semantic Problem & Intent -- one LLM call: problem evidence, first
                                  person, speaker, stance, seeking, quote
  3. Taxonomy                  -- deterministic entity extraction (unchanged)
  4. Evidence / Confidence     -- validates the quote, aggregates confidence
  5. Scoring                   -- existing v1 and v2 scorers (unchanged)

Step 2's output is projected onto the Step2ProblemEvidence / Step4Context
shapes that the evidence stage, the scorers and the persisted row have always
consumed, so none of them changed. Nothing downstream re-reads raw text
where a structured field already answers the question (scoring only touches
step outputs + a few deterministic severity markers, never re-classifies).

parent_text is the parent post of a reply (context only); source is the
record's source name. Both are optional so older call sites keep working.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from app.analysis.step1_relevance import classify_rcm_relevance, scan_keywords
from app.analysis.step2_semantic import classify_semantics
from app.analysis.step3_taxonomy import classify_taxonomy
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
    Step2Semantic,
    Step3Taxonomy,
    Step4Context,
    Step5Evidence,
    ScoreBreakdown,
    ScoreBreakdownV2,
)


# Progress hook for long runs (the dashboard's analysis job). Called with the
# 1-based stage number as each stage starts; it never influences results.
StageCallback = Optional[Callable[[int], None]]

STAGE_NAMES = (
    "RCM Relevance",
    "Semantic Problem & Intent",
    "Taxonomy",
    "Evidence / Confidence",
    "Scoring",
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
    """The analysis stages are shared between scoring versions; only the score
    and the two version strings differ, which is why the scorer is a parameter."""
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
    on_stage: StageCallback = None,
    parent_text: str | None = None,
    source: str | None = None,
) -> tuple[
    Step1Relevance, Step2ProblemEvidence, Step3Taxonomy, Step4Context, Step5Evidence,
    ScoreBreakdown, ScoreBreakdownV2, Optional[Step2Semantic],
]:
    stage = on_stage or (lambda _n: None)
    stage(1)
    step1 = classify_rcm_relevance(
        full_text,
        matched_keywords if matched_keywords is not None else scan_keywords(full_text),
        parent_text=parent_text,
        source=source,
    )

    semantic: Optional[Step2Semantic] = None
    if not step1.rcm_relevant:
        # Short-circuit: everything downstream assumes RCM relevance. A
        # non-relevant record still gets a full, schema-valid row (so it is
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
        stage(2)
        semantic = classify_semantics(full_text, parent_text=parent_text, source=source)
        step2 = semantic.to_problem_evidence()
        step4 = semantic.to_context()
        stage(3)
        step3 = classify_taxonomy(full_text)

    stage(4)
    step5 = build_evidence(full_text, step1, step2, step3, step4)
    stage(5)
    score = score_record(full_text, created_at, step1, step2, step3, step4, step5)
    # v2 scores every record, including non-relevant ones: its relevance floor
    # is graded rather than a gate, so the short-circuit above must not skip it.
    # It reads seeking_level (None for short-circuited records, which maps to
    # the default intent tier) plus the text itself.
    score_v2 = score_record_v2(full_text, step4.seeking_level)

    return step1, step2, step3, step4, step5, score, score_v2, semantic


def _trace(step1, step2, step3, step4, step5, semantic, parent_text) -> dict:
    """Per-stage outputs. step2_problem_evidence / step4_context keep their
    historical keys (the Pipeline/Debug page reads them); step2_semantic is
    the full semantic output they are derived from (None when Step 1
    short-circuited)."""
    return {
        "parent_text": parent_text,
        "step1_rcm_relevance": step1.model_dump(),
        "step2_semantic": semantic.model_dump() if semantic is not None else None,
        "step2_problem_evidence": step2.model_dump(),
        "step3_taxonomy": step3.model_dump(),
        "step4_context": step4.model_dump(),
        "step5_evidence_confidence": step5.model_dump(),
    }


def run_pipeline(
    source_item_id: str,
    title: str | None,
    text: str | None,
    created_at: datetime | None,
    matched_keywords: list[str] | None = None,
    parent_text: str | None = None,
    source: str | None = None,
) -> AnalysisResult:
    """The v1 row only."""
    full_text = build_text(title, text)
    stages = _run_stages(full_text, created_at, matched_keywords,
                         parent_text=parent_text, source=source)
    step1, step2, step3, step4, step5, score, _, _ = stages
    return _assemble(source_item_id, step1, step2, step3, step4, step5, score)


def run_pipeline_all_versions(
    source_item_id: str,
    title: str | None,
    text: str | None,
    created_at: datetime | None,
    matched_keywords: list[str] | None = None,
    on_stage: StageCallback = None,
    parent_text: str | None = None,
    source: str | None = None,
) -> list[AnalysisResult]:
    """Both scoring versions from a single pass over the analysis stages.

    The stages are by far the expensive part (LLM calls), so scoring twice off
    one pass is what makes storing v1 and v2 side by side affordable.
    """
    full_text = build_text(title, text)
    step1, step2, step3, step4, step5, score, score_v2, _ = _run_stages(
        full_text, created_at, matched_keywords, on_stage,
        parent_text=parent_text, source=source,
    )
    return [
        _assemble(source_item_id, step1, step2, step3, step4, step5, score),
        _assemble(
            source_item_id, step1, step2, step3, step4, step5, score_v2,
            analysis_version=ANALYSIS_VERSION_V2,
            scoring_version=SCORING_VERSION_V2,
        ),
    ]


def run_pipeline_traced(
    source_item_id: str,
    title: str | None,
    text: str | None,
    created_at: datetime | None,
    matched_keywords: list[str] | None = None,
    analysis_version_v1: str = ANALYSIS_VERSION,
    analysis_version_v2: str = ANALYSIS_VERSION_V2,
    parent_text: str | None = None,
    source: str | None = None,
) -> tuple[list[AnalysisResult], dict]:
    """run_pipeline_all_versions plus the per-stage trace, under caller-chosen
    analysis_version tags.

    For experiments: rows can be stored beside the production v1/v2 rows
    without overwriting them (the unique key is source_item_id +
    analysis_version), and the trace keeps what the merged row drops -- e.g.
    whether Step 1 was resolved by rules or the LLM, and whether Step 2 came
    from the LLM or the legacy fallback.
    """
    full_text = build_text(title, text)
    step1, step2, step3, step4, step5, score, score_v2, semantic = _run_stages(
        full_text, created_at, matched_keywords,
        parent_text=parent_text, source=source,
    )
    results = [
        _assemble(source_item_id, step1, step2, step3, step4, step5, score,
                  analysis_version=analysis_version_v1),
        _assemble(source_item_id, step1, step2, step3, step4, step5, score_v2,
                  analysis_version=analysis_version_v2,
                  scoring_version=SCORING_VERSION_V2),
    ]
    return results, _trace(step1, step2, step3, step4, step5, semantic, parent_text)


def explain_pipeline(
    title: str | None,
    text: str | None,
    created_at: datetime | None,
    matched_keywords: list[str] | None = None,
    parent_text: str | None = None,
    source: str | None = None,
) -> dict:
    """For the Pipeline/Debug tab: every stage's raw input/output, not just
    the merged final row."""
    full_text = build_text(title, text)
    step1, step2, step3, step4, step5, score, score_v2, semantic = _run_stages(
        full_text, created_at, matched_keywords,
        parent_text=parent_text, source=source,
    )

    return {
        "input_text": full_text,
        **_trace(step1, step2, step3, step4, step5, semantic, parent_text),
        "step6_7_scoring": score.model_dump(),
        "step6_7_scoring_v2": score_v2.model_dump(),
        "analysis_version": ANALYSIS_VERSION,
        "scoring_version": SCORING_VERSION,
        "analysis_version_v2": ANALYSIS_VERSION_V2,
        "scoring_version_v2": SCORING_VERSION_V2,
    }
