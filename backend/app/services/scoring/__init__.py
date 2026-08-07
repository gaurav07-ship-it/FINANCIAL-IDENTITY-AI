"""Scoring engine — drop-in replacement later by swapping the engine binding.

Picks the engine based on ``settings.scoring_engine``:
- ``rules`` → deterministic rule-based (default; used by tests + AI fallback).
- ``ai``    → Claude-backed engine from ``ai_engine.py`` (gracefully degrades
              to rules if Anthropic is unreachable).
"""
from __future__ import annotations

from app.config import settings
from app.services.scoring.ai_engine import AIScoringEngine
from app.services.scoring.engine import RuleBasedScoringEngine, ScoringEngine
from app.services.scoring.rules import DerivedMetrics, derive

_engine: ScoringEngine | None = None


def _build_default() -> ScoringEngine:
    if settings.scoring_engine == "ai":
        return AIScoringEngine()
    return RuleBasedScoringEngine()


def get_scoring_engine() -> ScoringEngine:
    """FastAPI dependency. Module-level cache so the engine is reused across
    requests on a warm instance.
    """
    global _engine
    if _engine is None:
        _engine = _build_default()
    return _engine


def set_scoring_engine(engine: ScoringEngine) -> None:
    """Test hook: swap engine for a stub in unit tests."""
    global _engine
    _engine = engine


__all__ = [
    "get_scoring_engine",
    "set_scoring_engine",
    "ScoringEngine",
    "RuleBasedScoringEngine",
    "AIScoringEngine",
    "DerivedMetrics",
    "derive",
]
