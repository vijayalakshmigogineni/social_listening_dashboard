"""
Step 2 -- Problem evidence (LEGACY: now the fallback only).

The pipeline's Step 2 is step2_semantic.py (one LLM call). This module runs
only when that call is unavailable or returns unusable output, and
extract_evidence_candidate remains the deterministic quote fallback.

Question: "Does this content contain evidence of an actual operational/
business problem?"

first_person is NOT a hard gate: a useful problem can be described without
explicit first-person wording (e.g. a peer-directed question implies the
asker is living the problem even without saying "our practice").

Hybrid approach:
  1. Rule pass over lexicons.py marker lists (first-person, peer-question,
     pain, seeking, vendor self-promo, definitional-question patterns).
  2. Zero-shot NLI fallback for text that is ambiguous under the rules
     (no strong signal either way).
  3. Deterministic evidence-candidate extraction: the sentence with the
     most matched signal words, so a reviewer can see why without
     re-reading the whole post (Step 5 promotes/refines this later).
"""

from __future__ import annotations

import re

from app.analysis.lexicons import PAIN_MARKERS, SEEKING_MARKERS_BY_LEVEL, VENDOR_SELFPROMO_MARKERS
from app.analysis.model_registry import nli_confidence, run_zero_shot
from app.analysis.text_signals import (
    DEFINITIONAL_REGEX,
    PEER_QUESTION_REGEX,
    find_hits,
    is_first_person,
)
from app.schemas.analysis import Step2ProblemEvidence

ALL_SEEKING_MARKERS = [m for markers in SEEKING_MARKERS_BY_LEVEL.values() for m in markers]

PROBLEM_EVIDENCE_LABELS = {
    "problem_experience": (
        "The author is describing a real operational problem, error, or "
        "negative experience currently happening with medical billing, "
        "claims, coding, or reimbursement."
    ),
    "not_problem_experience": (
        "The author is not describing a real, current operational problem "
        "-- this is general discussion, education, news, or career talk."
    ),
}

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")

# Forum quote-reply artifacts ("wjbruton said:", "Click to expand...") are
# not content -- excluding them keeps evidence_quote from ever surfacing a
# quoting header instead of what the author actually wrote.
_QUOTE_ARTIFACT_RE = re.compile(r"^\s*(\S+\s+said:?|click to expand\.*)\s*$", re.IGNORECASE)


def _is_quote_artifact(sentence: str) -> bool:
    return bool(_QUOTE_ARTIFACT_RE.match(sentence)) or len(sentence) < 8


def extract_evidence_candidate(text: str, signal_words: list[str]) -> str | None:
    if not text:
        return None
    sentences = [
        s.strip()
        for s in _SENTENCE_SPLIT_RE.split(text)
        if s.strip() and not _is_quote_artifact(s.strip())
    ]
    if not sentences:
        return None
    if not signal_words:
        return sentences[0][:300]

    best_sentence, best_hits = sentences[0], -1
    for sentence in sentences:
        lowered = sentence.lower()
        hits = sum(1 for w in signal_words if w in lowered)
        if hits > best_hits:
            best_hits, best_sentence = hits, sentence
    return best_sentence[:300]


def classify_problem_evidence(text: str) -> Step2ProblemEvidence:
    text = text or ""
    text_lower = text.lower()

    first_person, fp_hits = is_first_person(text, text_lower)
    has_peer_question = bool(PEER_QUESTION_REGEX.search(text))
    pain_hits = find_hits(text_lower, PAIN_MARKERS)
    seeking_hits = find_hits(text_lower, ALL_SEEKING_MARKERS)
    vendor_promo_hits = find_hits(text_lower, VENDOR_SELFPROMO_MARKERS)
    is_definitional = bool(DEFINITIONAL_REGEX.search(text))

    all_signal_words = fp_hits + pain_hits + seeking_hits

    # Hard exclusion: vendor self-promotion without genuine pain language is
    # supply-side noise, not problem evidence.
    if vendor_promo_hits and not pain_hits:
        return Step2ProblemEvidence(
            problem_evidence=False,
            first_person=first_person,
            problem_confidence=0.8,
            evidence_candidate=None,
        )

    # Purely definitional/educational question with no first-person, peer-
    # question, or pain signal is "context_only" territory, not evidence.
    if is_definitional and not first_person and not has_peer_question and not pain_hits:
        return Step2ProblemEvidence(
            problem_evidence=False,
            first_person=first_person,
            problem_confidence=0.75,
            evidence_candidate=None,
        )

    # Strong rule signal: a peer-directed operational question or explicit
    # pain language is enough on its own -- first_person is corroborating,
    # never required (per spec: never a hard gate).
    strong_positive = bool(pain_hits) or has_peer_question

    if strong_positive:
        hit_count = len(pain_hits) + len(seeking_hits) + (1 if has_peer_question else 0)
        confidence = round(min(0.95, 0.65 + 0.05 * hit_count), 4)
        return Step2ProblemEvidence(
            problem_evidence=True,
            first_person=first_person,
            problem_confidence=confidence,
            evidence_candidate=extract_evidence_candidate(text, all_signal_words),
        )

    # No strong rule signal either way (a lone first-person marker, a lone
    # generic seeking word like "how do", or nothing at all) -- let the
    # semantic model decide rather than guessing from a weak keyword alone.
    if not text.strip():
        return Step2ProblemEvidence(
            problem_evidence=False, first_person=first_person, problem_confidence=0.7
        )

    result = run_zero_shot(text, PROBLEM_EVIDENCE_LABELS)
    is_problem = result["label"] == "problem_experience"
    confidence = nli_confidence(result["top_score"], result["margin"])
    return Step2ProblemEvidence(
        problem_evidence=is_problem,
        first_person=first_person,
        problem_confidence=confidence,
        evidence_candidate=extract_evidence_candidate(text, all_signal_words)
        if is_problem
        else None,
    )
