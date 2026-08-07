"""Auth: register / login / logout / refresh / me."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.deps import get_current_user, require_refresh_token
from app.models import Identity, RefreshToken, User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.security import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    hash_password,
    issue_access_token,
    issue_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    common = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "domain": settings.cookie_domain,
        "path": "/",
    }
    response.set_cookie(ACCESS_COOKIE, access, max_age=settings.access_token_ttl_min * 60, **common)
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        max_age=settings.refresh_token_ttl_days * 24 * 3600,
        **common,
    )


def _clear_auth_cookies(response: Response) -> None:
    for name in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(name, path="/", domain=settings.cookie_domain)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    existing = await db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        is_active=True,
    )
    db.add(user)
    await db.flush()  # need user.id for the identity

    identity = Identity(
        user_id=user.id,
        name=body.name,
        email=body.email,
        onboarded=False,
        last_step=1,
        monthly_income=0,
        sources=[],
        gig_platforms=[],
        upi_apps=[],
        banks=[],
        goals=[],
        permissions={},
    )
    db.add(identity)
    await db.flush()

    # issue_access_token returns (token, jti, expires_at) — unpack all three
    access, _jti_a, _exp_a = issue_access_token(user.id)
    refresh, jti, exp = issue_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, jti=jti, expires_at=exp, revoked_at=None))

    user.last_login_at = datetime.now(tz=timezone.utc)
    await db.commit()

    _set_auth_cookies(response, access, refresh)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_ttl_min * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user = await db.scalar(select(User).where(User.email == body.email))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    access, _jti_a, _exp_a = issue_access_token(user.id)
    refresh, jti, exp = issue_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, jti=jti, expires_at=exp))

    user.last_login_at = datetime.now(tz=timezone.utc)
    await db.commit()

    _set_auth_cookies(response, access, refresh)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_ttl_min * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: str = Depends(require_refresh_token),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    # revoke the JTI so a stolen refresh token can't be replayed
    from app.security import decode_token

    payload = decode_token(refresh_token)
    jti = payload.get("jti")
    if jti:
        token_row = await db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
        if token_row and token_row.user_id == user.id and token_row.revoked_at is None:
            token_row.revoked_at = datetime.now(tz=timezone.utc)
    await db.commit()
    _clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    refresh_token: str = Depends(require_refresh_token),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    from app.security import decode_token

    payload = decode_token(refresh_token)
    jti = payload.get("jti")
    user_id_str = payload.get("sub")
    if not jti or not user_id_str:
        raise HTTPException(status_code=401, detail="Malformed refresh token")

    token_row = await db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    if token_row is None or token_row.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Refresh token revoked")

    user_uuid = uuid.UUID(user_id_str)
    if token_row.user_id != user_uuid:
        raise HTTPException(status_code=401, detail="Token subject mismatch")

    user = await db.get(User, user_uuid)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    # rotate: revoke old, issue new pair
    token_row.revoked_at = datetime.now(tz=timezone.utc)
    access, _jti_a, _exp_a = issue_access_token(user.id)  # pass UUID, not str
    new_refresh, new_jti, exp = issue_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, jti=new_jti, expires_at=exp))
    await db.commit()

    _set_auth_cookies(response, access, new_refresh)
    return TokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=settings.access_token_ttl_min * 60,
    )


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> User:
    return user