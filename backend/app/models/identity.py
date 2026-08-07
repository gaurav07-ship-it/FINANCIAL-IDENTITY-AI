"""Identity profile — the 'personal' block + occupation + derived preferences.

JSONB denormalized columns (sources, gig_platforms, upi_apps, banks, goals,
monthly_income) are kept in sync by the service layer on every onboarding step.
The relational tables (SelectedIncomeSource, BankAccount, etc.) remain the
source of truth for detailed per-item data; the JSONB columns exist for fast
single-row reads used by the scoring engine and dashboard.

Note on relationship naming: the ORM relationships intentionally use different
names from the JSONB columns to avoid attribute conflicts:
  • income_sources  (relationship) vs sources     (JSONB list of names)
  • bank_accounts   (relationship) vs banks        (JSONB list of dicts)
  • upi_app_links   (relationship) vs upi_apps     (JSONB list of names)
  • gig_links       (relationship) vs gig_platforms(JSONB list of names)
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String
from app.models.types import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampedMixin, UUIDPKMixin

if TYPE_CHECKING:
    from .user import User


class Identity(UUIDPKMixin, TimestampedMixin, Base):
    __tablename__ = "identities"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    dob: Mapped[date | None] = mapped_column(Date)
    city: Mapped[str] = mapped_column(String(80), default="Mumbai", nullable=False)
    phone: Mapped[str] = mapped_column(String(15), default="", nullable=False)
    email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    pan: Mapped[str] = mapped_column(String(20), default="", nullable=False)

    occupation: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    annual_goal: Mapped[int] = mapped_column(Integer, default=1_500_000, nullable=False)

    # Derived monthly income — updated each time income sources are saved or
    # a new transaction pull arrives.
    monthly_income: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    onboarded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    permissions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Onboarding step the user reached (1-10).
    last_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Denormalized JSONB lists ──────────────────────────────────────────────
    # These mirror the relational join tables for fast reads. The service layer
    # keeps them in sync on every write.
    sources: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    gig_platforms: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    upi_apps: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # banks is a list of {"bank": str, "last4": str, "primary": bool} dicts
    banks: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    goals: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # ── Relationships (named to avoid collision with JSONB columns above) ─────
    user: Mapped["User"] = relationship("User", back_populates="identity")
    income_sources: Mapped[list["SelectedIncomeSource"]] = relationship(
        "SelectedIncomeSource", back_populates="identity", cascade="all, delete-orphan"
    )
    bank_accounts: Mapped[list["BankAccount"]] = relationship(
        "BankAccount", back_populates="identity", cascade="all, delete-orphan"
    )
    upi_app_links: Mapped[list["UPIApp"]] = relationship(
        "UPIApp", back_populates="identity", cascade="all, delete-orphan"
    )
    gig_links: Mapped[list["SelectedGigPlatform"]] = relationship(
        "SelectedGigPlatform", back_populates="identity", cascade="all, delete-orphan"
    )
