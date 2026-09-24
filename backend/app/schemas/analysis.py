"""
Analysis/classification schema -- kept strictly separate from the canonical
normalized record (backend/app/schemas/normalized.py). One AnalysisResult
row is produced per (source_item_id, analysis_version).

This module defines:
  - one pydantic model per pipeline stage (Step 1-5), documenting exactly
    what each stage outputs and nothing more
  - the combined AnalysisResult that a full pipeline run persists
  - the enums/allowed-value sets the spec fixes (problem categories,
    speaker types, stance, seeking level)

Steps are never re-derived by later stages: Step 6/7 scoring reads the
structured fields Steps 1-5 already produced and must not re-classify text.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict

ANALYSIS_VERSION = "sld-analysis-v1"
SCORING_VERSION = "sld-score-v1"

# v2 scoring is stored as its own row rather than replacing v1, so the two can
# be diffed per post. The unique key is (source_item_id, analysis_version) --
# scoring_version is NOT part of it -- so a second scorer needs its own
# analysis_version even though Steps 1-5 are identical for both.
ANALYSIS_VERSION_V2 = "sld-analysis-v2"
SCORING_VERSION_V2 = "sld-score-v2"

# ---------------------------------------------------------------------------
# Step 3 taxonomy -- fixed category set. Multi-label: a record can carry
# several of these at once.
# ---------------------------------------------------------------------------
ProblemCategory = Literal[
    "authorization_utilization_management",
    "denials_claims_friction",
    "coverage_policy",
    "documentation_medical_necessity",
    "reimbursement_payment",
    "procedure_device_access",
]

# ---------------------------------------------------------------------------
# Step 4 -- speaker / stance / seeking allowed values
# ---------------------------------------------------------------------------
SpeakerType = Literal[
    "practice_side",
    "patient",
    "payer_side",
    "vendor",
    "educator_media",
    "unknown",
]

ContentStance = Literal["seeking", "supplying", "neutral", "mixed"]

SeekingLevel = Literal["L0", "L1", "L2", "L3"]


RelevanceStatus = Literal["clearly_relevant", "ambiguous"]
RelevanceMethod = Literal["rules", "llm", "fallback"]


class Step1Relevance(BaseModel):
    """Is this RCM/healthcare-business-operations relevant at all?

    relevance_status is the rule gate's verdict and has only two values --
    there is deliberately no "clearly_irrelevant". An ambiguous record is
    resolved by the LLM (or, if the LLM is unavailable, the legacy NLI check);
    rcm_relevant carries that final answer. relevance_status/relevance_method
    are trace-only -- the DB stores rcm_relevant + confidence as before.
    """

    rcm_relevant: bool
    rcm_relevance_confidence: float
    relevance_status: RelevanceStatus = "clearly_relevant"
    relevance_method: RelevanceMethod = "rules"


class Step2ProblemEvidence(BaseModel):
    """Does the text contain evidence of an actual operational problem?"""

    problem_evidence: bool
    first_person: bool
    problem_confidence: float
    evidence_candidate: Optional[str] = None


class Step3Taxonomy(BaseModel):
    """What exactly is being discussed?"""

    problem_category: list[ProblemCategory] = []
    procedure_tags: list[str] = []
    payer_tags: list[str] = []
    denial_reason_tags: list[str] = []
    specialty: Optional[str] = None
    mentioned_organization: Optional[str] = None
    cpt_hcpcs_codes: list[str] = []
    category_confidence: Optional[float] = None
    payer_confidence: Optional[float] = None
    procedure_confidence: Optional[float] = None
    denial_reason_confidence: Optional[float] = None


class Step4Context(BaseModel):
    """Who is speaking, what is their stance, and what are they seeking?"""

    speaker_type: SpeakerType = "unknown"
    content_stance: ContentStance
    seeking_level: Optional[SeekingLevel] = None
    speaker_confidence: Optional[float] = None
    stance_confidence: Optional[float] = None
    seeking_confidence: Optional[float] = None
    # Which mechanism produced the final stance/seeking value: "rule", "nli",
    # or "llm" (fallback, only when NLI was ambiguous). Not persisted to the
    # DB/API today -- see backend/app/db/models.py, which only stores the
    # aggregate Step5 confidence -- but kept on the schema for debugging via
    # /pipeline/explain and for future traceability.
    stance_source: Optional[str] = None
    seeking_source: Optional[str] = None


class Step2Semantic(BaseModel):
    """Semantic Problem & Intent Analysis -- one LLM call that replaces the old
    separate Problem Evidence and Speaker/Stance/Seeking stages.

    Classifies the CURRENT post only; a parent post is context, never the
    source of evidence_quote. The adapters below project it back onto the
    Step2ProblemEvidence / Step4Context shapes that Step 5, v1/v2 scoring and
    the persisted row already consume, so nothing downstream changes.

    problem_current / problem_recurring / operational_impact are trace-only:
    scoring keeps reading its own lexicon markers for those.
    """

    problem_evidence: bool
    problem_current: bool = False
    problem_recurring: bool = False
    first_person: bool
    operational_impact: bool = False
    speaker_type: SpeakerType = "unknown"
    content_stance: ContentStance
    seeking_level: Optional[SeekingLevel] = None
    evidence_quote: Optional[str] = None
    problem_confidence: float
    speaker_confidence: Optional[float] = None
    stance_confidence: Optional[float] = None
    seeking_confidence: Optional[float] = None
    # "llm", or "fallback" when the LLM was unavailable / returned unusable
    # output and the legacy rule+NLI stages produced these values instead.
    semantic_source: Literal["llm", "fallback"]

    def to_problem_evidence(self) -> "Step2ProblemEvidence":
        return Step2ProblemEvidence(
            problem_evidence=self.problem_evidence,
            first_person=self.first_person,
            problem_confidence=self.problem_confidence,
            evidence_candidate=self.evidence_quote,
        )

    def to_context(self) -> "Step4Context":
        return Step4Context(
            speaker_type=self.speaker_type,
            content_stance=self.content_stance,
            seeking_level=self.seeking_level,
            speaker_confidence=self.speaker_confidence,
            stance_confidence=self.stance_confidence,
            seeking_confidence=self.seeking_confidence,
            stance_source=self.semantic_source,
            seeking_source=self.semantic_source if self.seeking_level is not None else None,
        )


class Step5Evidence(BaseModel):
    """Supporting evidence quote plus an overall, non-calibrated confidence."""

    evidence_quote: str
    confidence: float
    rcm_confidence: Optional[float] = None
    problem_confidence: Optional[float] = None
    category_confidence: Optional[float] = None
    payer_confidence: Optional[float] = None
    procedure_confidence: Optional[float] = None
    speaker_confidence: Optional[float] = None
    stance_confidence: Optional[float] = None
    seeking_confidence: Optional[float] = None


class ScoreBreakdown(BaseModel):
    """Step 6/7 scoring, fully explainable -- never store only final_score."""

    problem_strength: float
    market_relevance: float
    intent_strength: float
    specificity: float
    severity: float
    base_score: float
    confidence: float
    recency_factor: float
    final_score: float


class ScoreBreakdownV2(BaseModel):
    """Step 6/7 scoring, v2 -- additive components, then multiplicative factors.

    Every factor is stored even when it is 1.0, so a score can be reconstructed
    from the row without re-running the scorer. `signals` lists which detectors
    fired, which is the evidence trail for a given score.
    """

    # Additive
    problem_strength: float
    identity: float
    specificity: float
    intent_strength: float
    interaction_bonus: float
    base_score: float

    # Multiplicative -- 1.0 means "did not apply"
    relevance_factor: float
    domain_factor: float
    commentary_factor: float
    noise_factor: float
    offdomain_factor: float

    final_score: float
    signals: list[str] = []


class AnalysisResult(BaseModel):
    """The full row persisted to the analysis table for one pipeline run."""

    model_config = ConfigDict(extra="forbid")

    source_item_id: str
    analysis_version: str = ANALYSIS_VERSION
    scoring_version: str = SCORING_VERSION

    # Step 1
    rcm_relevant: bool
    rcm_relevance_confidence: float

    # Step 2
    problem_evidence: bool
    first_person: bool
    problem_confidence: float

    # Step 3
    problem_category: list[str] = []
    procedure_tags: list[str] = []
    payer_tags: list[str] = []
    denial_reason_tags: list[str] = []
    specialty: Optional[str] = None
    mentioned_organization: Optional[str] = None
    cpt_hcpcs_codes: list[str] = []

    # Step 4
    speaker_type: SpeakerType = "unknown"
    content_stance: ContentStance
    seeking_level: Optional[SeekingLevel] = None

    # Step 5
    evidence_quote: str
    confidence: float

    # Step 6/7
    score_breakdown: dict[str, Any]
    final_score: float

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
