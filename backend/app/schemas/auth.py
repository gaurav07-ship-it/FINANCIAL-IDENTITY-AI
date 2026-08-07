"""Auth request / response shapes."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)


class TokenResponse(BaseModel):
    """Returned on login / refresh. Tokens also set as HttpOnly cookies."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID          # UUID, not str — Pydantic v2 serialises to str automatically
    email: EmailStr
    is_active: bool
    is_admin: bool
    last_login_at: datetime | None
    created_at: datetime