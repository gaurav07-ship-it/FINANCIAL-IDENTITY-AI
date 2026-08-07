"""Normalized transactions — single source of truth for all income/expense data.

In production these arrive via Account Aggregator pulls. In dev the MockProvider
seeds them. The scoring engine reads ONLY from this table.
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Numeric, String
from app.models.types import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDPKMixin


class TxnDirection(str, enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class TxnCategory(str, enum.Enum):
    CLIENT_PAYMENT = "client_payment"
    SALARY = "salary"
    GIG_PAYOUT = "gig_payout"
    SALES = "sales"
    INVESTMENT_INCOME = "investment_income"
    RENTAL = "rental"
    EMI = "emi"
    UTILITY = "utility"
    OTHER = "other"


class Transaction(UUIDPKMixin, Base):
    __tablename__ = "transactions"

    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        index=True,
    )
    posted_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount_inr: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    direction: Mapped[TxnDirection] = mapped_column(
        Enum(TxnDirection, name="txn_direction"), nullable=False
    )
    category: Mapped[TxnCategory] = mapped_column(
        Enum(TxnCategory, name="txn_category"), nullable=False
    )
    counterparty: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    source: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    raw: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("ix_tx_identity_date", Transaction.identity_id, Transaction.posted_at)
