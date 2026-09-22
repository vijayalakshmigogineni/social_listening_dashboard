"""
Canonical normalized-record schema for the ProbePS Social Listening Dashboard.

This schema is FIXED. Every source collector (Reddit, AAPC, LinkedIn, ...)
must normalize into exactly these fields. Do not add analysis/classification
fields here -- those live in the separate analysis table (see
backend/app/schemas/analysis.py and backend/app/db/models.py).

Field-for-field, this matches the schema validated in the existing research
codebase (testing/problem-intelligence/facebook-e2e-collection/fb_05_normalize.py
and testing/reddit/test_normalise_reddit.py), which is the closest thing to a
"schema of record" that already existed before this backend was built.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator

CANONICAL_FIELDS = [
    "source",
    "source_item_id",
    "url",
    "title",
    "text",
    "author_id",
    "author_name",
    "author_profile_url",
    "author_role",
    "organization_name",
    "organization_url",
    "location",
    "created_at",
    "collected_at",
    "engagement",
    "parent_id",
    "conversation_id",
    "media_type",
    "raw_data",
    "source_metadata",
]

# Fields that must NEVER appear on a normalized record. These are
# analysis/classification outputs and belong exclusively in the analysis
# table. Enforced by NormalizedItem's pydantic config (extra="forbid") plus
# this explicit list for defensive checks in collector code.
FORBIDDEN_ANALYSIS_FIELDS = {
    "rcm_relevant",
    "rcm_relevance_confidence",
    "problem_evidence",
    "first_person",
    "problem_confidence",
    "problem_category",
    "procedure_tags",
    "payer_tags",
    "denial_reason_tags",
    "specialty",
    "speaker_type",
    "content_stance",
    "seeking_level",
    "evidence_quote",
    "confidence",
    "final_score",
    "score_breakdown",
    "scoring_version",
    "analysis_version",
}

SOURCES = {"reddit", "aapc", "linkedin"}


class NormalizedItem(BaseModel):
    """One row of the canonical, immutable, source-agnostic collection record."""

    model_config = ConfigDict(extra="forbid")

    source: str
    source_item_id: str
    url: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    author_profile_url: Optional[str] = None
    author_role: Optional[str] = None
    organization_name: Optional[str] = None
    organization_url: Optional[str] = None
    location: Optional[str] = None
    created_at: Optional[datetime] = None
    collected_at: datetime
    engagement: Optional[dict[str, Any]] = None
    parent_id: Optional[str] = None
    conversation_id: Optional[str] = None
    media_type: Optional[str] = None
    raw_data: dict[str, Any]
    source_metadata: Optional[dict[str, Any]] = None

    @field_validator("source")
    @classmethod
    def _known_source(cls, v: str) -> str:
        if v not in SOURCES:
            raise ValueError(f"unknown source {v!r}; expected one of {sorted(SOURCES)}")
        return v

    @field_validator("source_item_id", "raw_data")
    @classmethod
    def _required_nonempty(cls, v):
        if v is None or v == "":
            raise ValueError("value is required and must not be empty")
        return v


def validate_no_analysis_fields(record: dict[str, Any]) -> None:
    """Defensive check for collector code building dicts before pydantic validation."""
    leaked = FORBIDDEN_ANALYSIS_FIELDS & record.keys()
    if leaked:
        raise ValueError(
            f"normalized record contains analysis fields, which must not be "
            f"mixed into collection data: {sorted(leaked)}"
        )
