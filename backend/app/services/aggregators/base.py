"""Abstract provider interface. Implementations live in mock.py / setu.py."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Protocol


@dataclass
class ConsentRequest:
    identity_id: uuid.UUID
    fi_types: list[str]
    from_date: str | None = None  # ISO date
    to_date: str | None = None


@dataclass
class ConsentHandle:
    consent_id: str
    status: str  # PENDING | ACTIVE | REVOKED | EXPIRED
    redirect_url: str | None = None
    data_range_from: date | None = None
    data_range_to: date | None = None
    expires_at: datetime | None = None
    payload: dict = field(default_factory=dict)


class AggregatorProvider(Protocol):
    def name(self) -> str: ...

    async def create_consent(self, req: ConsentRequest) -> ConsentHandle: ...

    async def fetch_data(self, consent_id: str) -> dict: ...

    async def revoke_consent(self, consent_id: str) -> bool: ...
