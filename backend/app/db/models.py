"""
SQLAlchemy models. Two tables, matching the required separation between
collection data and analysis/classification data:

  normalized_items  -- canonical, source-agnostic collection record.
                       One row per (source, source_item_id). Never carries
                       analysis fields.
  analysis_results  -- one row per (source_item_id, analysis_version).
                       References normalized_items.source_item_id. Re-running
                       the pipeline with a new analysis_version adds a new
                       row rather than overwriting history, so old scores
                       stay reproducible while the pipeline evolves.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NormalizedItem(Base):
    __tablename__ = "normalized_items"
    __table_args__ = (
        UniqueConstraint("source", "source_item_id", name="uq_source_item"),
        Index("ix_normalized_created_at", "created_at"),
        Index("ix_normalized_source", "source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    source: Mapped[str] = mapped_column(String, nullable=False)
    source_item_id: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    text: Mapped[str | None] = mapped_column(String, nullable=True)
    author_id: Mapped[str | None] = mapped_column(String, nullable=True)
    author_name: Mapped[str | None] = mapped_column(String, nullable=True)
    author_profile_url: Mapped[str | None] = mapped_column(String, nullable=True)
    author_role: Mapped[str | None] = mapped_column(String, nullable=True)
    organization_name: Mapped[str | None] = mapped_column(String, nullable=True)
    organization_url: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    engagement: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    parent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    source_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    inserted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    analyses: Mapped[list["AnalysisResult"]] = relationship(
        back_populates="item",
        primaryjoin="NormalizedItem.source_item_id==foreign(AnalysisResult.source_item_id)",
        viewonly=True,
    )


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    __table_args__ = (
        UniqueConstraint(
            "source_item_id", "analysis_version", name="uq_item_analysis_version"
        ),
        Index("ix_analysis_final_score", "final_score"),
        Index("ix_analysis_source_item_id", "source_item_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    source_item_id: Mapped[str] = mapped_column(
        String, ForeignKey("normalized_items.source_item_id"), nullable=False
    )
    analysis_version: Mapped[str] = mapped_column(String, nullable=False)
    scoring_version: Mapped[str] = mapped_column(String, nullable=False)

    # Step 1
    rcm_relevant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rcm_relevance_confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Step 2
    problem_evidence: Mapped[bool] = mapped_column(Boolean, nullable=False)
    first_person: Mapped[bool] = mapped_column(Boolean, nullable=False)
    problem_confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Step 3 (lists/optional -> JSON or nullable string)
    problem_category: Mapped[list] = mapped_column(JSON, default=list)
    procedure_tags: Mapped[list] = mapped_column(JSON, default=list)
    payer_tags: Mapped[list] = mapped_column(JSON, default=list)
    denial_reason_tags: Mapped[list] = mapped_column(JSON, default=list)
    specialty: Mapped[str | None] = mapped_column(String, nullable=True)
    mentioned_organization: Mapped[str | None] = mapped_column(String, nullable=True)
    cpt_hcpcs_codes: Mapped[list] = mapped_column(JSON, default=list)

    # Step 4
    speaker_type: Mapped[str] = mapped_column(String, default="unknown")
    content_stance: Mapped[str] = mapped_column(String, nullable=False)
    seeking_level: Mapped[str | None] = mapped_column(String, nullable=True)

    # Step 5
    evidence_quote: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Step 6/7
    score_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    item: Mapped["NormalizedItem"] = relationship(
        primaryjoin="foreign(AnalysisResult.source_item_id)==NormalizedItem.source_item_id",
        viewonly=True,
    )
