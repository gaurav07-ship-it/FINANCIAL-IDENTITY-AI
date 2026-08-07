"""Thin Anthropic Claude SDK wrapper.

Used by:
- ``AIScoringEngine`` (in scoring/ai_engine.py) for the DNA recompute path.
- ``/api/v1/ai/*`` routes for chat, explain, simulate, lender-reasons.

Design notes:
- All inputs are *structured features only* — never raw transaction text.
- Streaming chat uses Server-Sent Events so the frontend can render chunks.
- Failures degrade gracefully: callers should fall back to deterministic
  reason codes / static summaries.
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from app.config import settings


class AIClient:
    def __init__(self) -> None:
        self.enabled = bool(settings.anthropic_api_key) and settings.ai_enabled
        self._client = None

    def _ensure(self):
        if self._client is None and self.enabled:
            import anthropic

            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self._client

    async def complete(self, *, system: str, user: str, max_tokens: int = 300) -> str:
        """Single-shot completion. Returns the assistant text."""
        client = self._ensure()
        if client is None:
            return ""
        msg = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        # Content is a list of TextBlock / ToolUseBlock; we only emit text.
        return "".join(
            block.text for block in msg.content if getattr(block, "type", "") == "text"
        )

    async def stream_chat(self, *, message: str, context: dict) -> AsyncIterator[str]:
        """Stream chat tokens as they arrive. SSE-friendly.

        ``context`` is the structured feature bundle built by
        ``api/v1/ai.py::_grounding_context``. The assistant uses it as
        read-only context, never to invent data.
        """
        client = self._ensure()
        if client is None:
            yield "[AI disabled] Configure ANTHROPIC_API_KEY and AI_ENABLED=true."
            return

        system = (
            "You are FIA — the user's financial identity advisor. "
            "You may ONLY use the supplied JSON features. Never invent numbers, "
            "names, dates, or institutions. If something isn't in the features, "
            "say so. Reply concisely in plain English with at most 3 short paragraphs."
        )
        user = json.dumps({"features": context, "question": message}, default=str)

        async with client.messages.stream(
            model=settings.anthropic_model,
            max_tokens=400,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            async for text in stream.text_stream:
                yield text
                # tiny yield to keep the event loop responsive on the streaming
                # side; not strictly needed but cheap insurance.
                await asyncio.sleep(0)


ai_client = AIClient()
