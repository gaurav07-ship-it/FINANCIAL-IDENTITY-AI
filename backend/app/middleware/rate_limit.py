"""Per-IP rate limiting middleware.

Two windows:
  - /auth/* routes: 30 requests / 60 s (brute-force guard).
  - everything else: 300 requests / 60 s.

In serverless we can't keep a global counter across invocations, so the
fallback is an in-process dict. On multi-instance deploys swap this for
Upstash Redis via ``app.services.qstash_client`` style adapter (already
free-tier-eligible).
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class _SlidingWindow:
    __slots__ = ("buckets",)

    def __init__(self) -> None:
        self.buckets: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, limit: int, window_s: int) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        now = time.monotonic()
        q = self.buckets[key]
        # evict expired
        while q and (now - q[0]) > window_s:
            q.popleft()
        if len(q) >= limit:
            retry = max(1, int(window_s - (now - q[0])))
            return False, retry
        q.append(now)
        return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-process sliding-window rate limiter."""

    WINDOW_S = 60
    AUTH_LIMIT = 30
    DEFAULT_LIMIT = 300

    def __init__(self, app) -> None:
        super().__init__(app)
        self._state = _SlidingWindow()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else "anon")
        )
        is_auth = "/auth/" in path
        limit = self.AUTH_LIMIT if is_auth else self.DEFAULT_LIMIT
        allowed, retry = self._state.hit(ip, limit, self.WINDOW_S)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded", "retry_after": retry},
                headers={"Retry-After": str(retry)},
            )
        response: Response = await call_next(request)
        response.headers.setdefault("X-RateLimit-Limit", str(limit))
        return response
