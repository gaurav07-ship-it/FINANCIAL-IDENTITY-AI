"""Identity / dashboard DTOs. Mirrors the STORE shape so the frontend swap is trivial."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PermissionsResponse(BaseModel):
    push: bool
    primary_bank: bool
    aa_consent: bool


class IdentityResponse(BaseModel):
    """The single object the dashboard / DNA / Twin pages consume.

    Field names match STORE.get() exactly (camelCase) so the JS side
    can call `STORE.set(identity)` without remapping.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    name: str
    dob: date | None = None
    city: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    pan: str | None = None
    occupation: str | None = None
    annualGoal: int = Field(1_500_000, validation_alias="annual_goal")
    onboarded: bool = False
    lastStep: int = Field(0, validation_alias="last_step")
    monthlyIncome: int = Field(0, validation_alias="monthly_income")
    sources: list[str] = []
    gigPlatforms: list[str] = Field([], validation_alias="gig_platforms")
    upiApps: list[str] = Field([], validation_alias="upi_apps")
    banks: list[dict] = []
    goals: list[str] = []
    permissions: PermissionsResponse = PermissionsResponse(push=False, primary_bank=False, aa_consent=False)
    updatedAt: datetime | None = Field(None, validation_alias="updated_at")