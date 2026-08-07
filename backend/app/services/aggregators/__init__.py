"""Aggregator provider factory — reads AGGREGATOR_PROVIDER from settings."""
from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.services.aggregators.base import AggregatorProvider, ConsentHandle, ConsentRequest


@lru_cache(maxsize=1)
def get_provider() -> AggregatorProvider:
    name = settings.aggregator_provider.lower()
    if name == "mock":
        from app.services.aggregators.mock import MockProvider

        return MockProvider()
    if name == "setu":
        from app.services.aggregators.setu import SetuProvider

        return SetuProvider()
    if name == "finbox":
        # Future: from app.services.aggregators.finbox import FinboxProvider
        raise NotImplementedError("finbox provider not yet implemented")
    raise ValueError(f"Unknown aggregator provider: {name}")


__all__ = ["AggregatorProvider", "ConsentHandle", "ConsentRequest", "get_provider"]
