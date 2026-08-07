"""Account Aggregator consent artefacts — required for Setu/Finbox compliance."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String
from app.models.types import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampedMixin, UUIDPKMixin


class Consent(UUIDPKMixin, TimestampedMixin, Base):
    """One row per consent given to an aggregator.

    The raw consent artefact from Setu/Finbox is preserved in `payload` for
    audit.  `fi_types` is stored as a JSONB list so we avoid join-splitting a
    comma-separated String on every read.  `data_range_from/to` use Date (not
    DateTime) because aggregator APIs return ISO date strings, not datetimes.
    """

    __tablename__ = "consents"

    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    consent_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), default="PENDING", nullable=False)
    # Date range covered by this consent (not timezone-aware — aggregators use dates)
    data_range_from: Mapped[date | None] = mapped_column(Date)
    data_range_to: Mapped[date | None] = mapped_column(Date)
    # List of FI types e.g. ["DEPOSIT", "TERM_DEPOSIT"]
    fi_types: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
