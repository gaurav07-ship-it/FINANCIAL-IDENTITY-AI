"""Argon2id password hashing + JWT issuance + verification."""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.config import settings

_ph = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=2)


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        _ph.verify(hashed, plain)
        return True
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _make_jti() -> str:
    return secrets.token_urlsafe(16)


def issue_access_token(user_id: uuid.UUID) -> tuple[str, str, datetime]:
    """Returns (token, jti, expires_at)."""
    jti = _make_jti()
    exp = _now() + timedelta(minutes=settings.access_token_ttl_min)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "jti": jti,
        "iat": int(_now().timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)
    return token, jti, exp


def issue_refresh_token(user_id: uuid.UUID) -> tuple[str, str, datetime]:
    jti = _make_jti()
    exp = _now() + timedelta(days=settings.refresh_token_ttl_days)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": jti,
        "iat": int(_now().timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)
    return token, jti, exp


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
    except JWTError as e:
        raise ValueError("invalid token") from e


# --- cookie helpers (FastAPI sets cookies via Response, but we centralize defaults) ---

ACCESS_COOKIE = "fia_access"
REFRESH_COOKIE = "fia_refresh"


def cookie_common() -> dict[str, Any]:
    return {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "domain": settings.cookie_domain or None,
        "path": "/",
    }
