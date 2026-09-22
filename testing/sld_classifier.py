"""
Hierarchical zero-shot classifier for the Social Listening Dashboard (SLD).

WHY THE OLD APPROACH FAILED
----------------------------
The old pipeline gave the zero-shot model exactly 5 choices:
    L0  "the author is describing a problem they are experiencing"
    L1  "the author is asking for information"
    L2  "the author is looking for a solution to a problem"
    L3  "the author is looking for a vendor or service provider"
    NONE "the post does not express a specific request or problem-solving intent"

These labels only describe the *speech act* (is this a complaint, a
question, a request?) -- they say nothing about the *topic* (is this
about an operational RCM issue, or about a career/certification/job?).
A post like "Any coders work for Carle Health?" IS structurally a
question, so it legitimately out-scores the vague NONE catch-all under
"asking for information" even though it has nothing to do with an
operational billing problem. The model isn't wrong about the speech
act -- the label set just never asked about topic, so there was no
correct answer available for career/education/job content.

THE FIX
-------
Stage 1 (RCM domain relevance) and stage 2 (content type) below give the
model competing hypotheses that are equally specific about topic, e.g.
"asking about a billing process they handle at work" (information_request)
vs "asking about a certification exam or training program" (certification_
training) vs "looking for a job or hiring lead" (job_search). Now career/
education/job posts have a hypothesis that actually describes them, so
they stop losing by default to the operational categories.

ARCHITECTURE
------------
Stage 1 - RCM domain relevance (binary zero-shot NLI gate)
    Is this post about the medical billing / coding / RCM field AT ALL?
    Career and education posts about RCM are still domain-relevant here;
    this stage does not yet decide operational vs non-operational.

Stage 2 - Content type (multi-class zero-shot NLI, single winner)
    A flat, mutually exclusive set of categories covering BOTH
    operational types (problem_experience, information_request,
    solution_request, vendor_request) and non-operational types
    (career, job_search, education, certification_training,
    general_discussion, news, other).

Stage 3 - Deterministic rules (no model call)
    content_type -> intent_level (L0-L3, or None for non-operational)
    content_type -> problem_evidence / opportunity_evidence
    -> sld_candidate = problem_evidence OR opportunity_evidence

CONFIDENCE IS NOT A CALIBRATED PROBABILITY
-------------------------------------------
Zero-shot NLI scores are a softmax over the entailment scores of the
candidate hypotheses YOU supplied -- they measure "how much better did
this label do than the alternatives I offered", not "how likely is this
the correct real-world label". A 0.9 score does not mean a 90% chance of
correctness. Because of that we never expose a raw score as "confidence"
by itself: we combine top1 score with the margin over the runner-up into
a 3-tier confidence label (high/medium/low) and flag anything short of
"high" for human/LLM review (see compute_confidence).
"""

from dataclasses import dataclass
from typing import Optional
import re

CLASSIFIER_VERSION = "sld-classifier-v2.0"

# ---------------------------------------------------------------------
# Stage 1: RCM domain relevance labels
# ---------------------------------------------------------------------

RCM_RELEVANCE_LABELS = {
    "rcm_relevant": (
        "This text is about the medical billing, medical coding, claims, "
        "insurance reimbursement, prior authorization, or healthcare "
        "revenue cycle management field, whether as a career, an "
        "operational issue, or general discussion."
    ),
    "not_rcm_relevant": (
        "This text is not related to medical billing, medical coding, "
        "claims, or healthcare revenue cycle management in any way."
    ),
}

# ---------------------------------------------------------------------
# Stage 2: content type labels (flat, mutually exclusive)
# ---------------------------------------------------------------------

CONTENT_TYPE_LABELS = {
    "problem_experience": (
        "The author is describing a real operational problem, error, or "
        "negative experience currently happening with medical billing, "
        "claims, coding, or reimbursement."
    ),
    "information_request": (
        "The author is asking how to handle, understand, or resolve a "
        "specific medical billing, claims, coding, or payer process they "
        "are dealing with in their job."
    ),
    "solution_request": (
        "The author is asking for a better method, tool, or "
        "recommendation to solve an ongoing medical billing, claims, or "
        "reimbursement operational problem they are experiencing."
    ),
    "vendor_request": (
        "The author is looking to hire, contract, or get a "
        "recommendation for a company, vendor, consultant, or outsourced "
        "service to handle medical billing or revenue cycle management "
        "for their practice or business."
    ),
    "career": (
        "The author is talking about their own career, job satisfaction, "
        "or personal work experience as a medical billing or coding "
        "employee."
    ),
    "job_search": (
        "The author is looking for a job, hiring lead, or employer in "
        "medical billing, coding, or revenue cycle management, or is an "
        "employer posting a job opening."
    ),
    "education": (
        "The author is asking how to learn medical billing or coding, or "
        "how to start a career in the field."
    ),
    "certification_training": (
        "The author is asking about a certification exam, training "
        "program, course, or study materials for medical billing or "
        "coding."
    ),
    "general_discussion": (
        "The author is making a general comment, opinion, or discussion "
        "post about the medical billing or coding field without "
        "describing a specific operational issue or request."
    ),
    "news": (
        "The author is sharing news, a policy change, or industry "
        "information rather than a personal operational issue."
    ),
    "other": (
        "The post does not clearly fit any other category."
    ),
}

OPERATIONAL_CONTENT_TYPES = {
    "problem_experience",
    "information_request",
    "solution_request",
    "vendor_request",
}

CONTENT_TYPE_TO_INTENT = {
    "problem_experience": "L0",
    "information_request": "L1",
    "solution_request": "L2",
    "vendor_request": "L3",
}

# information_request counts as problem evidence too: someone asking how
# to handle a live operational process is, in practice, reporting that
# the process is a real day-to-day challenge worth capturing.
PROBLEM_EVIDENCE_TYPES = {"problem_experience", "information_request"}
OPPORTUNITY_EVIDENCE_TYPES = {"solution_request", "vendor_request"}


@dataclass
class StageResult:
    label: str
    top_score: float
    second_label: str
    second_score: float
    margin: float
    all_scores: dict


def _run_zero_shot(classifier, text: str, labels: dict) -> StageResult:
    names = list(labels.keys())
    hypotheses = [labels[n] for n in names]
    hyp_to_name = {labels[n]: n for n in names}

    # hypothesis_template="{}" is essential here: our candidate "labels"
    # are already complete NLI hypothesis sentences (e.g. "The author is
    # describing a real operational problem..."), not short label words.
    # The pipeline's default template ("This example is {}.") would wrap
    # them into an ungrammatical hypothesis and quietly degrade accuracy.
    result = classifier(
        text, hypotheses, hypothesis_template="{}", multi_label=False
    )

    ranked = list(zip(result["labels"], result["scores"]))
    top_hyp, top_score = ranked[0]
    second_hyp, second_score = ranked[1] if len(ranked) > 1 else (top_hyp, 0.0)

    all_scores = {hyp_to_name[h]: s for h, s in ranked}

    return StageResult(
        label=hyp_to_name[top_hyp],
        top_score=top_score,
        second_label=hyp_to_name[second_hyp],
        second_score=second_score,
        margin=top_score - second_score,
        all_scores=all_scores,
    )


def classify_rcm_relevance(classifier, text: str) -> StageResult:
    """Stage 1: is this post about the RCM/medical billing domain at all?"""
    return _run_zero_shot(classifier, text, RCM_RELEVANCE_LABELS)


def classify_content_type(classifier, text: str) -> StageResult:
    """Stage 2: which single content type best describes this post?"""
    return _run_zero_shot(classifier, text, CONTENT_TYPE_LABELS)


def map_intent_level(content_type: str) -> Optional[str]:
    """Stage 3a (deterministic, no model call).

    Only operational content types get an intent level. Career/education/
    job_search/general_discussion/news/other -> None.
    """
    return CONTENT_TYPE_TO_INTENT.get(content_type)


def compute_evidence_flags(content_type: str):
    """Stage 3b (deterministic, no model call): problem/opportunity evidence."""
    problem_evidence = content_type in PROBLEM_EVIDENCE_TYPES
    opportunity_evidence = content_type in OPPORTUNITY_EVIDENCE_TYPES
    return problem_evidence, opportunity_evidence


def compute_confidence(margin: float, top_score: float):
    """
    Combine margin + top score into a 3-tier confidence label and an
    ambiguity flag. See module docstring: raw NLI scores are not
    calibrated probabilities, so we never surface top_score alone.
    """
    if top_score >= 0.55 and margin >= 0.20:
        tier = "high"
    elif top_score >= 0.40 and margin >= 0.10:
        tier = "medium"
    else:
        tier = "low"

    needs_review = tier != "high"
    return tier, needs_review


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def extract_evidence_quote(text: str, matched_keywords) -> str:
    """
    Cheap, deterministic evidence extraction (no extra model call): return
    the sentence containing the most matched RCM keywords, so a reviewer
    can see *why* the post was flagged without re-reading the whole post.
    Falls back to the first sentence / first 200 chars.
    """
    matched_keywords = matched_keywords or []
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]

    if not sentences:
        return text[:200]

    if not matched_keywords:
        return sentences[0][:300]

    best_sentence = sentences[0]
    best_hits = -1

    for sentence in sentences:
        lowered = sentence.lower()
        hits = sum(1 for kw in matched_keywords if kw in lowered)
        if hits > best_hits:
            best_hits = hits
            best_sentence = sentence

    return best_sentence[:300]
