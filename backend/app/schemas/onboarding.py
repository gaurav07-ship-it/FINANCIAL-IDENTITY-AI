"""Onboarding wizard DTOs — one per step so autosave can be per-step."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PersonalDetailsIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    dob: date | None = None
    phone: str | None = Field(None, pattern=r"^\+?\d{10,15}$")
    pan: str | None = Field(None, pattern=r"^[A-Z]{5}\d{4}[A-Z]$")
    city: str | None = None


class OccupationSelection(BaseModel):
    occupation: Literal["freelancer", "salaried", "gig", "seller", "investor", "landlord", "other"]
    annual_goal: int = Field(ge=0)


class IncomeSourceIn(BaseModel):
    name: str
    monthly_income: int = Field(ge=0)
    primary: bool = False


class BankAccountIn(BaseModel):
    bank_name: str
    account_last4: str = Field(min_length=4, max_length=4, pattern=r"^\d{4}$")
    is_primary: bool = False
    statement_uploaded_at: date | None = None


class UPIAppIn(BaseModel):
    provider: str  # matches UPIProvider catalog name


class GigPlatformIn(BaseModel):
    platform: str  # matches GigPlatform catalog name


class OnboardingProgress(BaseModel):
    """Returned after each step save — frontend knows what step to show next."""

    model_config = ConfigDict(from_attributes=True)

    last_step: int
    onboarded: bool
    next_step: int