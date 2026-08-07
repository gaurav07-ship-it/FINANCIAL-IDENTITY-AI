"""Personalised opportunity recommendations."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from app.models.types import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampedMixin, UUIDPKMixin


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class Opportunity(UUIDPKMixin, TimestampedMixin, Base):
    __tablename__ = "opportunities"

    identity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        index=True,
        nullable=True,  # NULL = global (catalog) opportunity, not per-user
    )
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    ribbon: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    impact: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    price: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    cta: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    icon: Mapped[str] = mapped_column(String(8), default="", nullable=False)
    # When this opportunity was computed / seeded.
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
