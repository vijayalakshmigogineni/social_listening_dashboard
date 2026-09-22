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
"""

from __future__ import annotations

import re

from app.analysis.lexicons import PAIN_MARKERS, SEEKING_MARKERS_BY_LEVEL, VENDOR_SELFPROMO_MARKERS
from app.analysis.model_registry import run_zero_shot
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


def _seeking_level(
    text_lower: str, has_peer_question: bool, pain_hits: list[str]
) -> tuple[str | None, float | None]:
    if find_hits(text_lower, SEEKING_MARKERS_BY_LEVEL["L3"]):
        return "L3", 0.85
    if find_hits(text_lower, SEEKING_MARKERS_BY_LEVEL["L2"]):
        return "L2", 0.8
    if find_hits(text_lower, SEEKING_MARKERS_BY_LEVEL["L1"]) or has_peer_question:
        return "L1", 0.75
    if pain_hits:
        return "L0", 0.65
    return None, None


def classify_context(text: str) -> Step4Context:
    text = text or ""
    text_lower = text.lower()

    first_person, _ = is_first_person(text, text_lower)
    has_peer_question = bool(PEER_QUESTION_REGEX.search(text))
    pain_hits = find_hits(text_lower, PAIN_MARKERS)
    has_seeking_marker = has_peer_question or any(
        find_hits(text_lower, markers) for markers in SEEKING_MARKERS_BY_LEVEL.values()
    )
    has_supplying_marker = bool(SUPPLYING_REGEX.search(text))

    speaker_type, speaker_confidence = _speaker_type(text, text_lower, first_person)
    seeking_level, seeking_confidence = _seeking_level(text_lower, has_peer_question, pain_hits)

    if has_seeking_marker and has_supplying_marker:
        stance = "mixed"
    elif has_supplying_marker:
        stance = "supplying"
    elif has_seeking_marker:
        stance = "seeking"
    elif pain_hits:
        stance = "neutral"
    elif text.strip():
        # No rule signal at all -- ambiguous, fall back to the semantic model.
        result = run_zero_shot(text, STANCE_LABELS)
        stance = result["label"]
    else:
        stance = "neutral"

    return Step4Context(
        speaker_type=speaker_type,
        content_stance=stance,
        seeking_level=seeking_level,
        speaker_confidence=speaker_confidence,
        seeking_confidence=seeking_confidence,
    )
