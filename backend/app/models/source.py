"""Income sources, banks, UPI apps, gig platforms — selectable catalog + per-user.

Per-user join tables now carry the extra fields the service layer writes
(monthly_income, primary, account_last4, provider, platform) so the relational
model stays in sync with the JSONB denormalized columns on Identity.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String
from app.models.types import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPKMixin

if TYPE_CHECKING:
    from .identity import Identity


# ---------------------------------------------------------------------------
# Catalog tables (immutable, loaded from seed)
# ---------------------------------------------------------------------------

class IncomeSource(UUIDPKMixin, Base):
    """Catalog of possible income source types — selected per identity."""

    __tablename__ = "income_sources_catalog"

    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    icon: Mapped[str] = mapped_column(String(8), default="", nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class GigPlatform(UUIDPKMixin, Base):
    """Catalog of gig platforms the user can choose from."""

    __tablename__ = "gig_platforms_catalog"

    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)


class UPIProvider(UUIDPKMixin, Base):
    """Catalog of UPI apps the user can connect."""

    __tablename__ = "upi_providers_catalog"

    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)


class Bank(UUIDPKMixin, Base):
    """Catalog of supported banks."""

    __tablename__ = "banks_catalog"

    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)


class Goal(UUIDPKMixin, Base):
    """Catalog of possible financial goals."""

    __tablename__ = "goals_catalog"

    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)


# ---------------------------------------------------------------------------
# Per-user selections
# ---------------------------------------------------------------------------

class SelectedIncomeSource(UUIDPKMixin, Base):
    """Normalised row per selected income source per identity.

    income_source_id links back to the catalog; monthly_income is the
    user-declared amount for that stream; primary flags the main source.
    """

    __tablename__ = "user_income_sources"

    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identities.id", ondelete="CASCADE"), index=True
    )
    income_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("income_sources_catalog.id", ondelete="CASCADE"),
        index=True,
    )
    # Denormalised name so queries don't need a join for display.
    source_name: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    monthly_income: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    identity: Mapped["Identity"] = relationship("Identity", back_populates="income_sources")


class BankAccount(UUIDPKMixin, Base):
    __tablename__ = "bank_accounts"

    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identities.id", ondelete="CASCADE"), index=True
    )
    bank_name: Mapped[str] = mapped_column(String(80), nullable=False)
    account_last4: Mapped[str] = mapped_column(String(4), default="", nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    statement_uploaded_at: Mapped[date | None] = mapped_column(Date)

    identity: Mapped["Identity"] = relationship("Identity", back_populates="bank_accounts")


class UPIApp(UUIDPKMixin, Base):
    __tablename__ = "upi_apps"

    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identities.id", ondelete="CASCADE"), index=True
    )
    # Named `provider` to match UPIProvider catalog and the service layer.
    provider: Mapped[str] = mapped_column(String(80), nullable=False)

    identity: Mapped["Identity"] = relationship("Identity", back_populates="upi_app_links")


class SelectedGigPlatform(UUIDPKMixin, Base):
    __tablename__ = "user_gig_platforms"

    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identities.id", ondelete="CASCADE"), index=True
    )
    # Named `platform` to match GigPlatform catalog and the service layer.
    platform: Mapped[str] = mapped_column(String(80), nullable=False)

    identity: Mapped["Identity"] = relationship("Identity", back_populates="gig_links")
