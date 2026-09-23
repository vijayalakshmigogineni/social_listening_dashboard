"""
Step 4 -- Speaker type, content stance, and seeking level (merged per spec:
content_type was explicitly removed from this architecture).

Question: "Who is speaking, what is their stance, and what are they
seeking?"

Defaults are deliberately conservative: speaker_type defaults to
"unknown" whenever evidence is missing rather than inferred from topic
(discussing prior auth does not make someone a biller). seeking_level is
never forced into L0-L3 -- supplying/educational content can legitimately
be null.

Speaker Type stays rule-based (unchanged). Content Stance and Seeking
Level are NLI-primary: zero-shot DeBERTa (model_registry.run_zero_shot,
shared with Step 1) runs first; its result is accepted when both top_score
and margin clear the confidence thresholds below, and only the ambiguous
remainder falls back to the local Ollama LLM (llm_fallback.py). SEEKING_MARKERS_BY_LEVEL
is intentionally no longer read here for the final L0-L3 decision -- it stays
in lexicons.py because Part 2 of testing/SLD-ROADMAP.md's rule-based relevance
gates may still reference it, but Step 4's decision is NLI/LLM now.
"""

from __future__ import annotations

import re

from app.analysis.lexicons import SEEKING_MARKERS_BY_LEVEL, VENDOR_SELFPROMO_MARKERS
from app.analysis.llm_fallback import classify_seeking_llm, classify_stance_llm
from app.analysis.model_registry import nli_confidence, run_zero_shot
from app.analysis.text_signals import (
    PATIENT_VOICE_REGEX,
    PEER_QUESTION_REGEX,
    SUPPLYING_REGEX,
    find_hits,
    is_first_person,
)
from app.schemas.analysis import Step4Context

PAYER_SIDE_REGEX = re.compile(
    r"\b(as a claims (examiner|adjuster)|i work for (the )?(insurance|payer)|"
    r"from the payer side|we process claims for)\b",
    re.IGNORECASE,
)

STANCE_LABELS = {
    "seeking": "The author is asking a question or requesting help, advice, or a solution.",
    "supplying": "The author is providing information, advice, or a solution to others.",
    "neutral": "The author is simply describing a situation without asking for or offering help.",
}

# multi_label=False forces a single winning label out of run_zero_shot, so
# zero-shot structurally cannot express "mixed" (both seeking and
# supplying) in one call. "mixed" is therefore still decided by a rule
# pre-check on the existing marker lists, before NLI ever runs -- the one
# deliberate exception to "NLI is primary".
SEEKING_LABELS = {
    "L0": "The author is describing a problem or venting without explicitly asking for help.",
    "L1": "The author is asking for help, information, or advice.",
    "L2": "The author is looking for a solution or a better way to handle the problem.",
    "L3": "The author is actively looking for a vendor, service, or outside provider to solve the problem.",
}

# Ambiguity gate: an NLI result is accepted only when it clears BOTH bars.
# DeBERTa-v3-zeroshot was already validated in this repo as more decisive
# than bart-large-mnli (see model_registry.py); testing/test_zero_shot.py's
# own prototype used margin < 0.10 as its ambiguity cutoff against the
# weaker bart model, so 0.15 here is a deliberately slightly more
# conservative starting point, not a calibrated value. Easy to retune.
STANCE_CONFIDENCE_THRESHOLD = 0.60
STANCE_MARGIN_THRESHOLD = 0.15
SEEKING_CONFIDENCE_THRESHOLD = 0.60
SEEKING_MARGIN_THRESHOLD = 0.15


def _speaker_type(text: str, text_lower: str, first_person: bool) -> tuple[str, float | None]:
    if find_hits(text_lower, VENDOR_SELFPROMO_MARKERS):
        return "vendor", 0.75
    if PAYER_SIDE_REGEX.search(text):
        return "payer_side", 0.7
    if first_person:
        return "practice_side", 0.75
    if PATIENT_VOICE_REGEX.search(text):
        return "patient", 0.7
    if SUPPLYING_REGEX.search(text):
        return "educator_media", 0.55
    return "unknown", None


def _content_stance(
    text: str, has_seeking_marker: bool, has_supplying_marker: bool
) -> tuple[str, float | None, str]:
    if has_seeking_marker and has_supplying_marker:
        return "mixed", None, "rule"

    result = run_zero_shot(text, STANCE_LABELS)
    confidence = nli_confidence(result["top_score"], result["margin"])
    if result["top_score"] >= STANCE_CONFIDENCE_THRESHOLD and result["margin"] >= STANCE_MARGIN_THRESHOLD:
        return result["label"], confidence, "nli"

    llm_result = classify_stance_llm(text)
    if llm_result is not None:
        return llm_result["label"], llm_result["confidence"], "llm"

    # LLM fallback disabled or failed -- keep the NLI result rather than
    # blocking the pipeline, but its low confidence/margin is preserved so
    # downstream consumers can see it was not a confident call.
    return result["label"], confidence, "nli"


def _seeking_level(text: str) -> tuple[str | None, float | None, str | None]:
    result = run_zero_shot(text, SEEKING_LABELS)
    confidence = nli_confidence(result["top_score"], result["margin"])
    if result["top_score"] >= SEEKING_CONFIDENCE_THRESHOLD and result["margin"] >= SEEKING_MARGIN_THRESHOLD:
        return result["label"], confidence, "nli"

    llm_result = classify_seeking_llm(text)
    if llm_result is not None:
        return llm_result["label"], llm_result["confidence"], "llm"

    return result["label"], confidence, "nli"


def classify_context(text: str) -> Step4Context:
    text = text or ""
    text_lower = text.lower()

    if not text.strip():
        return Step4Context(speaker_type="unknown", content_stance="neutral")

    first_person, _ = is_first_person(text, text_lower)
    has_peer_question = bool(PEER_QUESTION_REGEX.search(text))
    has_seeking_marker = has_peer_question or any(
        find_hits(text_lower, markers) for markers in SEEKING_MARKERS_BY_LEVEL.values()
    )
    has_supplying_marker = bool(SUPPLYING_REGEX.search(text))

    speaker_type, speaker_confidence = _speaker_type(text, text_lower, first_person)
    stance, stance_confidence, stance_source = _content_stance(
        text, has_seeking_marker, has_supplying_marker
    )

    # Preserves the existing contract that seeking_level is not gated on
    # content_stance == "seeking" (Step 6 reads seeking_level unconditionally)
    # -- it is only skipped for clearly "supplying" content, where asking an
    # L0-L3 seeking question makes no sense and would waste a model/LLM call.
    if stance == "supplying":
        seeking_level, seeking_confidence, seeking_source = None, None, None
    else:
        seeking_level, seeking_confidence, seeking_source = _seeking_level(text)

    return Step4Context(
        speaker_type=speaker_type,
        content_stance=stance,
        seeking_level=seeking_level,
        speaker_confidence=speaker_confidence,
        stance_confidence=stance_confidence,
        seeking_confidence=seeking_confidence,
        stance_source=stance_source,
        seeking_source=seeking_source,
    )
