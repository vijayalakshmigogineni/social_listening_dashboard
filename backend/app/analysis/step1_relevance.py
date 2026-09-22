"""
Step 1 -- RCM relevance.

Question: "Is this post/article relevant to RCM or healthcare
practice/business operations?"

This is NOT the final SLD decision -- it is domain relevance, not
usefulness. "I am studying medical billing and looking for my first job"
is rcm_relevant=True; Steps 2-6 decide whether it is a useful signal.

Hybrid approach, cheapest-first per the project's NLP hierarchy (rules ->
traditional NLP -> pretrained semantic model -> LLM only if needed):

  1. Lexicon scan (app.analysis.lexicons.RCM_KEYWORDS) -- cheap, broad,
     high recall by design ("miss nothing; precision comes later").
     >=2 hits or 0 hits resolve the decision without a model call, because
     at those extremes the broad lexicon is already a reliable signal.
  2. Zero-shot NLI -- semantic fallback, invoked only for the ambiguous
     exactly-one-keyword-hit band, where the lexicon alone is unreliable.

Keywords are candidate evidence, never final truth by themselves -- the
1-hit band is exactly where that distinction matters.
"""

from __future__ import annotations

from app.analysis.lexicons import RCM_KEYWORDS
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

HIGH_CONFIDENCE_HIT_THRESHOLD = 2
ZERO_HIT_CONFIDENCE = 0.85


def scan_keywords(text: str) -> list[str]:
    if not text:
        return []
    lowered = text.lower()
    return [kw for kw in RCM_KEYWORDS if kw in lowered]


def classify_rcm_relevance(
    text: str, matched_keywords: list[str] | None = None
) -> Step1Relevance:
    text = text or ""
    matched_keywords = (
        matched_keywords if matched_keywords is not None else scan_keywords(text)
    )
    hits = len(matched_keywords)

    if hits == 0:
        return Step1Relevance(
            rcm_relevant=False, rcm_relevance_confidence=ZERO_HIT_CONFIDENCE
        )

    if hits >= HIGH_CONFIDENCE_HIT_THRESHOLD:
        confidence = round(min(0.95, 0.6 + 0.05 * hits), 4)
        return Step1Relevance(rcm_relevant=True, rcm_relevance_confidence=confidence)

    # Ambiguous band: exactly one broad keyword hit. Fall back to the
    # semantic model rather than trusting a single keyword match.
    if not text.strip():
        return Step1Relevance(rcm_relevant=False, rcm_relevance_confidence=ZERO_HIT_CONFIDENCE)

    result = run_zero_shot(text, RCM_RELEVANCE_LABELS)
    is_relevant = result["label"] == "rcm_relevant"
    confidence = nli_confidence(result["top_score"], result["margin"])
    return Step1Relevance(rcm_relevant=is_relevant, rcm_relevance_confidence=confidence)
