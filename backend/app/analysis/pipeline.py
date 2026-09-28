"""
Orchestrates the analysis stages for a single normalized record into one
AnalysisResult row (ANALYSIS_VERSION):

  1. RCM Relevance             -- rule gate (clearly_relevant | ambiguous);
                                  the LLM resolves only ambiguous records
  2. Semantic Problem & Intent -- one LLM call: problem evidence, first
                                  person, speaker, stance, seeking, quote
  3. Taxonomy                  -- deterministic entity extraction
  4. Evidence / Confidence     -- validates the quote, aggregates confidence
  5. Scoring                   -- ProbePS opportunity score: 65% LLM
                                  assessment + 20% RCM relevance + 15% Step 3
                                  specificity (scoring_opportunity.py)

Step 2's output is also projected onto the Step2ProblemEvidence /
Step4Context shapes that the evidence stage and the persisted row consume.
Scoring reads Step 1, the full semantic output (its per-field confidences
and the opportunity assessment) and the taxonomy. Nothing downstream
re-reads raw text where a structured field already answers the question.

The semantic output is persisted inside score_breakdown, so rescore_row()
can recompute a stored row's score without any LLM call.

parent_text is the parent post of a reply (context only); source is the
record's source name. Both are optional.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, NamedTuple, Optional

from app.analysis.step1_relevance import classify_rcm_relevance, scan_keywords
from app.analysis.step2_semantic import classify_semantics
from app.analysis.step3_taxonomy import classify_taxonomy
from app.analysis.step5_evidence_confidence import build_evidence
from app.analysis.scoring_opportunity import score_opportunity
from app.schemas.analysis import (
    ANALYSIS_VERSION,
    SCORING_VERSION,
    AnalysisResult,
    Step1Relevance,
    Step2ProblemEvidence,
    Step2Semantic,
    Step3Taxonomy,
    Step4Context,
    Step5Evidence,
    ScoreBreakdownOpportunity,
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


class Stages(NamedTuple):
    step1: Step1Relevance
    step2: Step2ProblemEvidence
    step3: Step3Taxonomy
    step4: Step4Context
    step5: Step5Evidence
    score: ScoreBreakdownOpportunity
    semantic: Optional[Step2Semantic]


def build_text(title: str | None, text: str | None) -> str:
    title = (title or "").strip()
    body = (text or "").strip()
    if not body or body == title:
        return title
    return f"{title}\n{body}".strip()


def _assemble(
    source_item_id: str,
    s: Stages,
    analysis_version: str = ANALYSIS_VERSION,
) -> AnalysisResult:
    return AnalysisResult(
        source_item_id=source_item_id,
        analysis_version=analysis_version,
        scoring_version=SCORING_VERSION,
        rcm_relevant=s.step1.rcm_relevant,
        rcm_relevance_confidence=s.step1.rcm_relevance_confidence,
        problem_evidence=s.step2.problem_evidence,
        first_person=s.step2.first_person,
        problem_confidence=s.step2.problem_confidence,
        problem_category=s.step3.problem_category,
        procedure_tags=s.step3.procedure_tags,
        payer_tags=s.step3.payer_tags,
        denial_reason_tags=s.step3.denial_reason_tags,
        specialty=s.step3.specialty,
        mentioned_organization=s.step3.mentioned_organization,
        cpt_hcpcs_codes=s.step3.cpt_hcpcs_codes,
        speaker_type=s.step4.speaker_type,
        content_stance=s.step4.content_stance,
        seeking_level=s.step4.seeking_level,
        evidence_quote=s.step5.evidence_quote,
        confidence=s.step5.confidence,
        score_breakdown=s.score.model_dump(),
        final_score=s.score.final_score,
    )


def _run_stages(
    full_text: str,
    matched_keywords: list[str] | None,
    on_stage: StageCallback = None,
    parent_text: str | None = None,
    source: str | None = None,
) -> Stages:
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
    # Reads only structured outputs: Step 1, the semantic analysis (None
    # when short-circuited, which scores 0) and the taxonomy.
    score = score_opportunity(step1, semantic, step3)

    return Stages(step1, step2, step3, step4, step5, score, semantic)


def _trace(s: Stages, parent_text: str | None) -> dict:
    """Per-stage outputs. step2_problem_evidence / step4_context keep their
    historical keys (the Pipeline/Debug page reads them); step2_semantic is
    the full semantic output they are derived from (None when Step 1
    short-circuited)."""
    return {
        "parent_text": parent_text,
        "step1_rcm_relevance": s.step1.model_dump(),
        "step2_semantic": s.semantic.model_dump() if s.semantic is not None else None,
        "step2_problem_evidence": s.step2.model_dump(),
        "step3_taxonomy": s.step3.model_dump(),
        "step4_context": s.step4.model_dump(),
        "step5_evidence_confidence": s.step5.model_dump(),
    }


def run_pipeline(
    source_item_id: str,
    title: str | None,
    text: str | None,
    created_at: datetime | None = None,
    matched_keywords: list[str] | None = None,
    on_stage: StageCallback = None,
    parent_text: str | None = None,
    source: str | None = None,
) -> AnalysisResult:
    """The analysis row for one record. created_at is accepted for call-site
    compatibility; opportunity scoring does not use recency."""
    s = _run_stages(build_text(title, text), matched_keywords, on_stage,
                    parent_text=parent_text, source=source)
    return _assemble(source_item_id, s)


def run_pipeline_traced(
    source_item_id: str,
    title: str | None,
    text: str | None,
    created_at: datetime | None = None,
    matched_keywords: list[str] | None = None,
    analysis_version: str = ANALYSIS_VERSION,
    parent_text: str | None = None,
    source: str | None = None,
) -> tuple[AnalysisResult, dict]:
    """run_pipeline plus the per-stage trace, under a caller-chosen
    analysis_version tag (so an evaluation run can be stored beside the
    production rows without overwriting them). The trace keeps what the
    merged row drops -- e.g. whether Step 1 was resolved by rules or the LLM,
    and whether Step 2 came from the LLM or the legacy fallback."""
    s = _run_stages(build_text(title, text), matched_keywords,
                    parent_text=parent_text, source=source)
    return _assemble(source_item_id, s, analysis_version), _trace(s, parent_text)


def explain_pipeline(
    title: str | None,
    text: str | None,
    created_at: datetime | None = None,
    matched_keywords: list[str] | None = None,
    parent_text: str | None = None,
    source: str | None = None,
) -> dict:
    """For the Pipeline/Debug tab: every stage's raw input/output, not just
    the merged final row."""
    full_text = build_text(title, text)
    s = _run_stages(full_text, matched_keywords, parent_text=parent_text, source=source)
    return {
        "input_text": full_text,
        **_trace(s, parent_text),
        "score_breakdown": s.score.model_dump(),
        "final_score": s.score.final_score,
        "analysis_version": ANALYSIS_VERSION,
        "scoring_version": SCORING_VERSION,
    }


def rescore_row(
    rcm_relevant: bool,
    rcm_relevance_confidence: float,
    score_breakdown: dict | None,
    taxonomy: Step3Taxonomy,
) -> ScoreBreakdownOpportunity | None:
    """Re-score a stored row from what it already holds -- Step 1 columns,
    the Step 3 taxonomy columns and score_breakdown["llm_assessment"] -- with
    NO LLM call. Returns None when the row cannot be re-scored offline: it
    is RCM-relevant but was stored without an llm_assessment (e.g. an older
    analysis version), so only a full re-analysis can score it."""
    step1 = Step1Relevance(rcm_relevant=rcm_relevant,
                           rcm_relevance_confidence=rcm_relevance_confidence)
    assessment = (score_breakdown or {}).get("llm_assessment")
    if not rcm_relevant:
        return score_opportunity(step1, None, Step3Taxonomy())
    if assessment is None:
        return None
    return score_opportunity(step1, Step2Semantic(**assessment), taxonomy)
