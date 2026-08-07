"""Persisted scoring snapshots — historical DNA/IQ/risk over time."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric
from app.models.types import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDPKMixin


class ScoreSnapshot(UUIDPKMixin, Base):
    """One snapshot per recompute. Powers 'DNA History · 6 months' chart."""

    __tablename__ = "score_snapshots"

    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        index=True,
    )
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dna_score: Mapped[int] = mapped_column(Integer, nullable=False)
    stability: Mapped[int] = mapped_column(Integer, nullable=False)
    discipline: Mapped[int] = mapped_column(Integer, nullable=False)
    growth: Mapped[int] = mapped_column(Integer, nullable=False)
    savings: Mapped[int] = mapped_column(Integer, nullable=False)
    diversification: Mapped[int] = mapped_column(Integer, nullable=False)
    risk: Mapped[int] = mapped_column(Integer, nullable=False)
    income_quality: Mapped[int] = mapped_column(Integer, nullable=False)
    top_client_share: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    monthly_income: Mapped[int] = mapped_column(Integer, nullable=False)
    yoy: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    cv: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    late_payouts: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    detail: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
