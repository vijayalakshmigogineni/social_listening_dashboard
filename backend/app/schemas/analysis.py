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

Steps are never re-derived by later stages: opportunity scoring reads the
structured fields the analysis stages already produced and never
re-classifies text.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict

# The current (and only) analysis/scoring lineage: the ProbePS opportunity
# score, 65% LLM assessment + 20% RCM relevance + 15% Step 3 specificity.
#   ANALYSIS_VERSION -- bump when the prompt or the analysis stages change
#                       (existing rows then need a full LLM re-run)
#   SCORING_VERSION  -- bump when only weights/points change (existing rows
#                       can be re-scored offline: scripts/rescore.py)
# The unique key is (source_item_id, analysis_version), so rows from an
# earlier analysis version (e.g. "sld-analysis-v3") stay untouched beside the
# new ones until they are deleted.
ANALYSIS_VERSION = "sld-analysis-opportunity-1"
SCORING_VERSION = "sld-score-opportunity-1"

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

# ---------------------------------------------------------------------------
# Step 2 -- LLM opportunity assessment allowed values
# ---------------------------------------------------------------------------
Grade = Literal["none", "low", "moderate", "high"]

# DRAFT list -- to be finalized with the business team. The last two mark
# posts that are not ProbePS opportunities and cap the LLM score.
OpportunityType = Literal[
    "denial_management",
    "prior_authorization",
    "ar_followup_cashflow",
    "coding_documentation",
    "payer_policy_reimbursement",
    "billing_operations_staffing",
    "informational_only",
    "not_an_opportunity",
]


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
    Step2ProblemEvidence / Step4Context shapes that Step 5 and the persisted
    row consume. Opportunity scoring reads this model directly (the LLM
    component); problem_current, operational_impact, pain_severity and
    opportunity_reasoning are analysis/display fields with no score weight.
    The whole model is persisted in score_breakdown["llm_assessment"] so a
    row can be re-scored without calling the LLM again.
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
    # Confidence-weight the LLM score's contributions; None when the legacy
    # fallback produced the record.
    first_person_confidence: Optional[float] = None
    operational_impact_confidence: Optional[float] = None
    speaker_confidence: Optional[float] = None
    stance_confidence: Optional[float] = None
    seeking_confidence: Optional[float] = None
    # ProbePS opportunity assessment. All None when the legacy fallback
    # produced the record (it cannot judge opportunity value), so they then
    # contribute 0 rather than an invented default.
    pain_severity: Optional[Grade] = None
    business_impact: Optional[Grade] = None
    probeps_fit: Optional[Grade] = None
    opportunity_type: Optional[OpportunityType] = None
    opportunity_reasoning: Optional[str] = None
    pain_confidence: Optional[float] = None
    impact_confidence: Optional[float] = None
    fit_confidence: Optional[float] = None
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


class LlmPoints(BaseModel):
    """Raw points behind the LLM component (sum = llm_score, max 100)."""

    problem_evidence: float
    first_person: float
    seeking: float
    business_impact: float
    recurring: float
    probeps_fit: float


class RcmPoints(BaseModel):
    """Raw points behind the RCM component (sum = rcm_score, max 100)."""

    relevance: float
    category_severity: float
    primary_problem_category: Optional[str] = None


class Step3Points(BaseModel):
    """Raw specificity points (max 20); step3_score = total / 20 * 100."""

    category: float
    payer: float
    procedure: float
    denial_reason: float
    code: float
    specialty: float
    total: float


class ScoreBreakdownOpportunity(BaseModel):
    """ProbePS opportunity score -- three normalized 0-100 components,
    combined by fixed weights (65% LLM, 20% RCM, 15% Step 3), no multipliers.

    Every intermediate value is stored so a score can be read -- and
    explained -- off the row without re-running anything. llm_assessment is
    the full Step 2 output (None when Step 1 short-circuited), which is what
    makes an offline re-score possible.
    """

    llm_score: float
    rcm_score: float
    step3_score: float

    weights: dict[str, float]
    llm_contribution: float
    rcm_contribution: float
    step3_contribution: float

    llm_points: LlmPoints
    rcm_points: RcmPoints
    step3_points: Step3Points

    # Caps (never bonuses). llm_cap_applied: the LLM called the post
    # informational / not an opportunity. cap_applied: no problem evidence.
    llm_cap_applied: bool
    cap_applied: bool
    cap_reason: Optional[str] = None
    pre_cap_score: float
    final_score: float

    llm_source: Optional[Literal["llm", "fallback"]] = None
    llm_assessment: Optional[dict[str, Any]] = None


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

    # Scoring (ScoreBreakdownOpportunity.model_dump())
    score_breakdown: dict[str, Any]
    final_score: float

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
