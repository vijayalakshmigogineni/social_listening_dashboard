"""
Step 3 -- Taxonomy / entity extraction.

Question: "What exactly is being discussed?"

Rules + dictionaries + normalization/synonym mapping, per the project's
NLP hierarchy -- no ML needed here; the six problem categories, payers,
procedures, and denial reasons are closed, well-understood vocabularies.
Semantic fallback is deliberately NOT used for this step in V1: unlike
Steps 1-2 (open-ended relevance judgments), tag presence here is a
straightforward dictionary-membership question, and forcing every post
through a category/payer/procedure zero-shot pass would be slow for no
accuracy benefit until real output shows otherwise.

Do not force a tag the text does not support (a bare 5-digit number is not
a CPT code without billing/coding context -- see CPT_CODE_REGEX).
"""

from __future__ import annotations

import re

from app.analysis.lexicons import (
    CPT_CONTEXT_MARKERS,
    DENIAL_REASONS,
    PAYERS,
    PROBLEM_CATEGORY_KEYWORDS,
    PROCEDURES,
    SPECIALTY_KEYWORDS,
)
from app.schemas.analysis import Step3Taxonomy

CPT_CODE_REGEX = re.compile(r"\b\d{5}\b")

# A verifiable-artefact heuristic for organization mentions -- deliberately
# conservative (V1, no NER model): only fires on an explicit "practice/
# clinic/company" naming pattern with a whole-word suffix, never inferred
# from writing style or geography. Short suffixes like "PC"/"PA" are
# deliberately excluded -- they collide too easily with unrelated
# capitalized abbreviations (e.g. "CPC" certification).
ORG_MENTION_REGEX = re.compile(
    r"\b(?:at|for)\s+([A-Z][\w&'.-]*(?:\s+[A-Z][\w&'.-]*){0,3}\s+"
    r"(?:Health|Medical|Clinic|Practice|Hospital|Center|Centre|Group|Associates|"
    r"Billing|LLC|Inc))\b"
)


def _find_matches(text_lower: str, keyword_groups: dict[str, list[str]]) -> list[str]:
    matches = []
    for category, keywords in keyword_groups.items():
        if any(kw in text_lower for kw in keywords):
            matches.append(category)
    return matches


def _confidence_for(tags: list[str]) -> float | None:
    if not tags:
        return None
    return round(min(0.95, 0.7 + 0.05 * len(tags)), 4)


def extract_cpt_hcpcs_codes(text: str) -> list[str]:
    """Only treat a 5-digit number as a code if billing/coding context is present nearby."""
    text_lower = text.lower()
    if not any(marker in text_lower for marker in CPT_CONTEXT_MARKERS):
        return []
    return sorted(set(CPT_CODE_REGEX.findall(text)))


def extract_mentioned_organization(text: str) -> str | None:
    match = ORG_MENTION_REGEX.search(text)
    return match.group(1).strip() if match else None


def classify_taxonomy(text: str) -> Step3Taxonomy:
    text = text or ""
    text_lower = text.lower()

    problem_category = _find_matches(text_lower, PROBLEM_CATEGORY_KEYWORDS)
    payer_tags = _find_matches(text_lower, PAYERS)
    procedure_tags = _find_matches(text_lower, PROCEDURES)
    denial_reason_tags = _find_matches(text_lower, DENIAL_REASONS)
    specialty_matches = _find_matches(text_lower, SPECIALTY_KEYWORDS)
    specialty = specialty_matches[0] if specialty_matches else None

    return Step3Taxonomy(
        problem_category=problem_category,
        procedure_tags=procedure_tags,
        payer_tags=payer_tags,
        denial_reason_tags=denial_reason_tags,
        specialty=specialty,
        mentioned_organization=extract_mentioned_organization(text),
        cpt_hcpcs_codes=extract_cpt_hcpcs_codes(text),
        category_confidence=_confidence_for(problem_category),
        payer_confidence=_confidence_for(payer_tags),
        procedure_confidence=_confidence_for(procedure_tags),
        denial_reason_confidence=_confidence_for(denial_reason_tags),
    )
