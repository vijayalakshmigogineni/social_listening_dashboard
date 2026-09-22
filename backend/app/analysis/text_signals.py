"""
Shared low-level text-signal detectors used by more than one analysis stage
(Steps 2 and 4 both need "is this first-person" / "is this a peer-directed
question", so the logic lives here once rather than being redefined per
stage).
"""

from __future__ import annotations

import re

from app.analysis.lexicons import FIRST_PERSON_MARKERS

FIRST_PERSON_REGEX = re.compile(
    r"\b(i'?m the (biller|coder|manager|owner)|we'?re a \d+-?provider|we bill|"
    r"we submit|we'?re hiring|at our clinic)\b",
    re.IGNORECASE,
)

DEFINITIONAL_REGEX = re.compile(
    r"\b(what is|what does .* mean|can someone explain|does anyone know what)\b",
    re.IGNORECASE,
)

# Peer-directed question about handling a live operational process, phrased
# flexibly rather than as fixed phrases -- "How do you actually rework a
# CO-16 claim" must match just as well as "how do you handle CO-16 claims".
PEER_QUESTION_REGEX = re.compile(
    r"\bhow do(es)? (you|others|other practices|we)\b"
    r"|\bhas anyone\b|\bdoes anyone\b"
    r"|\banyone else (seeing|getting|having)\b"
    r"|\bwhat are you (all )?doing about\b"
    r"|\bam i the only one\b",
    re.IGNORECASE,
)

PATIENT_VOICE_REGEX = re.compile(
    r"\b(my insurance|my claim|my doctor|my surgery|my copay|my deductible)\b",
    re.IGNORECASE,
)

SUPPLYING_REGEX = re.compile(
    r"\b(\d+\s+(ways|tips|steps|reasons)\b|top\s+\d+|here'?s how|we solved|"
    r"here is how)\b",
    re.IGNORECASE,
)


def find_hits(text_lower: str, markers: list[str]) -> list[str]:
    return [m for m in markers if m in text_lower]


def is_first_person(text: str, text_lower: str) -> tuple[bool, list[str]]:
    hits = find_hits(text_lower, FIRST_PERSON_MARKERS)
    if FIRST_PERSON_REGEX.search(text):
        hits.append("first_person_regex")
    return bool(hits), hits
