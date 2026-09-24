"""
Step 1 -- RCM relevance.

Question: "Is this post/article relevant to RCM or healthcare
practice/business operations?"

This is NOT the final SLD decision -- it is domain relevance, not
usefulness. "I am studying medical billing and looking for my first job"
is rcm_relevant=True; Steps 2-6 decide whether it is a useful signal.

Rule gate + LLM resolution. The rule gate has exactly TWO outcomes --
there is deliberately no "clearly irrelevant" verdict:

  1. clearly_relevant -- the lexicon (app.analysis.lexicons.RCM_KEYWORDS)
     has >=1 hit. Accepted without any model call.
  2. ambiguous        -- zero hits. The rules cannot tell whether the post is
     in the RCM domain (it may use vocabulary the lexicon lacks), so the LLM
     (llm_fallback.classify_relevance_llm) decides whether it continues.
     relevance_status stays "ambiguous"; rcm_relevant carries the answer.

If the LLM is disabled or fails, the legacy zero-shot NLI check decides
instead and relevance_method records "fallback".
"""

from __future__ import annotations

from app.analysis.lexicons import RCM_KEYWORDS
from app.analysis.llm_fallback import classify_relevance_llm
from app.analysis.model_registry import nli_confidence, run_zero_shot
from app.schemas.analysis import Step1Relevance

RCM_RELEVANCE_LABELS = {
    "rcm_relevant": (
        "This text is about the medical billing, medical coding, claims, "
        "insurance reimbursement, prior authorization, or healthcare revenue "
        "cycle management field, whether as a career, an operational issue, "
        "or general discussion."
    ),
    "not_rcm_relevant": (
        "This text is not related to medical billing, medical coding, "
        "claims, or healthcare revenue cycle management in any way."
    ),
}

CLEARLY_RELEVANT_HIT_THRESHOLD = 1
EMPTY_TEXT_CONFIDENCE = 0.85


def scan_keywords(text: str) -> list[str]:
    if not text:
        return []
    lowered = text.lower()
    return [kw for kw in RCM_KEYWORDS if kw in lowered]


def classify_rcm_relevance(
    text: str,
    matched_keywords: list[str] | None = None,
    parent_text: str | None = None,
    source: str | None = None,
) -> Step1Relevance:
    text = text or ""
    matched_keywords = (
        matched_keywords if matched_keywords is not None else scan_keywords(text)
    )
    hits = len(matched_keywords)

    if hits >= CLEARLY_RELEVANT_HIT_THRESHOLD:
        confidence = round(min(0.95, 0.6 + 0.05 * hits), 4)
        return Step1Relevance(
            rcm_relevant=True,
            rcm_relevance_confidence=confidence,
            relevance_status="clearly_relevant",
            relevance_method="rules",
        )

    # Ambiguous: no lexicon evidence either way. Nothing to classify in an
    # empty post, so no model call is spent on it.
    if not text.strip():
        return Step1Relevance(
            rcm_relevant=False,
            rcm_relevance_confidence=EMPTY_TEXT_CONFIDENCE,
            relevance_status="ambiguous",
            relevance_method="rules",
        )

    llm = classify_relevance_llm(text, parent_text, source)
    if llm is not None:
        return Step1Relevance(
            rcm_relevant=llm["relevant"],
            rcm_relevance_confidence=llm["confidence"],
            relevance_status="ambiguous",
            relevance_method="llm",
        )

    # LLM disabled/failed -- the legacy semantic check resolves it instead.
    result = run_zero_shot(text, RCM_RELEVANCE_LABELS)
    return Step1Relevance(
        rcm_relevant=result["label"] == "rcm_relevant",
        rcm_relevance_confidence=nli_confidence(result["top_score"], result["margin"]),
        relevance_status="ambiguous",
        relevance_method="fallback",
    )
