"""Common FastAPI dependencies."""
from __future__ import annotations

import uuid

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Identity, User
from app.security import ACCESS_COOKIE, REFRESH_COOKIE, decode_token


class AuthError(HTTPException):
    def __init__(self, detail: str = "Not authenticated") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    access_token: str | None = Cookie(default=None, alias=ACCESS_COOKIE),
) -> User:
    if not access_token:
        raise AuthError("Missing access cookie")
    try:
        payload = decode_token(access_token)
    except ValueError as exc:
        raise AuthError(str(exc)) from exc
    if payload.get("type") != "access":
        raise AuthError("Wrong token type")
    user_id = payload.get("sub")
    if not user_id:
        raise AuthError("Missing subject claim")

    user = await db.get(User, uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise AuthError("User not found or disabled")
    return user


async def get_current_identity(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Identity:
    """Return the Identity for the current user.

    Uses an explicit SELECT rather than accessing `user.identity` via the lazy
    relationship, which would trigger a synchronous load and raise a
    MissingGreenlet error in async SQLAlchemy.
    """
    identity = await db.scalar(select(Identity).where(Identity.user_id == user.id))
    if identity is None:
        raise HTTPException(status_code=404, detail="Identity profile not set up")
    return identity


async def require_refresh_token(
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
) -> str:
    if not refresh_token:
        raise AuthError("Missing refresh cookie")
    try:
        payload = decode_token(refresh_token)
    except ValueError as exc:
        raise AuthError(str(exc)) from exc
    if payload.get("type") != "refresh":
        raise AuthError("Wrong token type")
    return refresh_token