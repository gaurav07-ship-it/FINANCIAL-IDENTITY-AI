"""Lender catalog and per-user pre-approved offers."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from app.models.types import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampedMixin, UUIDPKMixin


class Lender(TimestampedMixin, UUIDPKMixin, Base):
    __tablename__ = "lenders"

    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    logo_gradient: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    min_amount_inr: Mapped[int] = mapped_column(Integer, default=50_000, nullable=False)
    max_amount_inr: Mapped[int] = mapped_column(Integer, default=2_000_000, nullable=False)
    min_tenure_months: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    max_tenure_months: Mapped[int] = mapped_column(Integer, default=84, nullable=False)
    rate_min: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    rate_max: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class LenderOffer(UUIDPKMixin, Base):
    """A computed offer for a specific user at a specific time."""

    __tablename__ = "lender_offers"

    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        index=True,
    )
    lender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lenders.id", ondelete="CASCADE"), index=True
    )
    amount_inr: Mapped[int] = mapped_column(Integer, nullable=False)
    tenure_months: Mapped[int] = mapped_column(Integer, nullable=False)
    rate_apr: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    approval_pct: Mapped[int] = mapped_column(Integer, nullable=False)
    emi_inr: Mapped[int] = mapped_column(Integer, nullable=False)
    disbursal_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
