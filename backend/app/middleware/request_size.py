"""Reject oversized request bodies before they hit the route handlers."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds ``max_body_bytes``."""

    def __init__(self, app, max_body_bytes: int = 100 * 1024) -> None:
        super().__init__(app)
        self.max_body_bytes = max_body_bytes

    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > self.max_body_bytes:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body exceeds {self.max_body_bytes} bytes"},
            )
        return await call_next(request)
