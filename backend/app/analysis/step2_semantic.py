"""
Step 2 -- Semantic Problem & Intent Analysis.

Replaces the former separate Problem Evidence (step2_problem_evidence.py) and
Speaker / Stance / Seeking (step4_speaker_stance_seeking.py) stages with ONE
LLM call per relevant post (llm_fallback.analyze_semantics_llm).

Question: "What is this person actually saying?" -- is there a real
operational problem, is it their own, who are they, and what do they want?

Reply handling: the classified text is the CURRENT post only. Forum replies
embed the parent as a quote block ("X said: ... Click to expand..."); that
block is stripped from the current post (same regex v2 scoring uses) and, when
the parent row itself was not resolved, reused as parent context. The parent
is sent to the LLM as a separately labelled section and can never supply the
evidence quote: the quote is accepted only if it occurs in the current post.

Validation here covers what the LLM client cannot check structurally:
  - evidence_quote must be a verbatim passage of the current post (matched
    case- and whitespace-insensitively, then returned as the exact span);
    otherwise it is replaced deterministically from the current post
  - seeking_level is null for "supplying" content (the contract the old
    Step 4 had, which v1/v2 scoring rely on)

If the LLM is disabled, unreachable, or returns unusable output, the legacy
rule+NLI stages produce the same fields and semantic_source="fallback".
"""

from __future__ import annotations

import re

from app.analysis.llm_fallback import analyze_semantics_llm
from app.analysis.step2_problem_evidence import (
    classify_problem_evidence,
    extract_evidence_candidate,
)
from app.analysis.step4_speaker_stance_seeking import classify_context
from app.analysis.step6_scoring_v2 import QUOTE_BLOCK_RE, strip_quoted_parent
from app.schemas.analysis import Step2Semantic

_QUOTE_TRIM = " \t\r\n\"'“”‘’.…"


def split_current_post(full_text: str, parent_text: str | None) -> tuple[str, str | None]:
    """(current post text, parent context). The embedded quote block becomes
    the parent context only when no parent row was resolved."""
    post_text = strip_quoted_parent(full_text)
    if parent_text is None and post_text != full_text:
        match = QUOTE_BLOCK_RE.match(full_text)
        parent_text = match.group(0).strip() if match else None
    return post_text, parent_text


def verbatim_span(quote: str | None, text: str) -> str | None:
    """The exact passage of `text` that `quote` reproduces, or None when the
    quote is not really in `text` (paraphrased, or taken from the parent)."""
    exact = (quote or "").strip()
    if exact and exact in (text or ""):
        return exact[:300]
    words = exact.strip(_QUOTE_TRIM).split()
    if not words:
        return None
    pattern = r"\s+".join(re.escape(w) for w in words)
    match = re.search(pattern, text or "", re.IGNORECASE)
    return match.group(0)[:300] if match else None


def _from_llm(llm: dict, post_text: str) -> Step2Semantic:
    stance = llm["content_stance"]
    seeking_level = None if stance == "supplying" else llm["seeking_level"]
    quote = verbatim_span(llm["evidence_quote"], post_text) or extract_evidence_candidate(post_text, [])
    return Step2Semantic(
        problem_evidence=llm["problem_evidence"],
        problem_current=llm["problem_current"],
        problem_recurring=llm["problem_recurring"],
        first_person=llm["first_person"],
        operational_impact=llm["operational_impact"],
        speaker_type=llm["speaker_type"],
        content_stance=stance,
        seeking_level=seeking_level,
        evidence_quote=quote,
        problem_confidence=llm["problem_confidence"],
        speaker_confidence=llm["speaker_confidence"],
        stance_confidence=llm["stance_confidence"],
        seeking_confidence=llm["seeking_confidence"] if seeking_level is not None else None,
        semantic_source="llm",
    )


def _legacy(full_text: str) -> Step2Semantic:
    """The pre-refactor Steps 2 + 4, run on the same text they always saw."""
    problem = classify_problem_evidence(full_text)
    context = classify_context(full_text)
    return Step2Semantic(
        problem_evidence=problem.problem_evidence,
        first_person=problem.first_person,
        speaker_type=context.speaker_type,
        content_stance=context.content_stance,
        seeking_level=context.seeking_level,
        evidence_quote=problem.evidence_candidate,
        problem_confidence=problem.problem_confidence,
        speaker_confidence=context.speaker_confidence,
        stance_confidence=context.stance_confidence,
        seeking_confidence=context.seeking_confidence,
        semantic_source="fallback",
    )


def classify_semantics(
    full_text: str, parent_text: str | None = None, source: str | None = None
) -> Step2Semantic:
    full_text = full_text or ""
    post_text, parent_text = split_current_post(full_text, parent_text)
    if not post_text.strip():
        return _legacy(full_text)

    llm = analyze_semantics_llm(post_text, parent_text, source)
    if llm is None:
        return _legacy(full_text)
    return _from_llm(llm, post_text)
