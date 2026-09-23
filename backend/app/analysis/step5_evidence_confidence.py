"""
Step 5 -- Evidence + confidence.

Question: "What evidence supports the classification, and how confident are
we?" This step never re-classifies text -- it only aggregates what Steps
1-4 already produced.

evidence_quote must be an exact, verbatim passage from the normalized text.
confidence is an overall figure combining whichever component confidences
were actually produced by earlier steps (simple averaging over the
non-null ones, per spec) -- it is explicitly not a calibrated probability,
just an initial signal the architecture can recalibrate later against
human-labelled data.
"""

from __future__ import annotations

from app.analysis.step2_problem_evidence import extract_evidence_candidate
from app.schemas.analysis import (
    Step1Relevance,
    Step2ProblemEvidence,
    Step3Taxonomy,
    Step4Context,
    Step5Evidence,
)

DEFAULT_CONFIDENCE = 0.5


def build_evidence(
    text: str,
    step1: Step1Relevance,
    step2: Step2ProblemEvidence,
    step3: Step3Taxonomy,
    step4: Step4Context,
) -> Step5Evidence:
    evidence_quote = step2.evidence_candidate or extract_evidence_candidate(text, [])
    if not evidence_quote:
        evidence_quote = (text or "")[:300]

    components = {
        "rcm_confidence": step1.rcm_relevance_confidence,
        "problem_confidence": step2.problem_confidence,
        "category_confidence": step3.category_confidence,
        "payer_confidence": step3.payer_confidence,
        "procedure_confidence": step3.procedure_confidence,
        "speaker_confidence": step4.speaker_confidence,
        "stance_confidence": step4.stance_confidence,
        "seeking_confidence": step4.seeking_confidence,
    }
    used = {k: v for k, v in components.items() if v is not None}
    overall_confidence = round(sum(used.values()) / len(used), 4) if used else DEFAULT_CONFIDENCE

    return Step5Evidence(
        evidence_quote=evidence_quote,
        confidence=overall_confidence,
        **components,
    )
