"""Onboarding wizard — autosave per step."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_identity
from app.models import Identity
from app.schemas import (
    BankAccountIn,
    GigPlatformIn,
    IncomeSourceIn,
    OnboardingProgress,
    PersonalDetailsIn,
    UPIAppIn,
)
from app.schemas.identity import PermissionsResponse
from app.schemas.onboarding import OccupationSelection
from app.services.identity import (
    add_banks,
    add_gigs,
    add_income_sources,
    add_upi_apps,
    next_step_for,
    set_occupation,
    set_personal,
    set_permissions,
)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _progress(identity: Identity) -> OnboardingProgress:
    return OnboardingProgress(
        last_step=identity.last_step,
        onboarded=identity.onboarded,
        next_step=next_step_for(identity),
    )


@router.post("/personal", response_model=OnboardingProgress)
async def step_personal(
    body: PersonalDetailsIn,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> OnboardingProgress:
    set_personal(identity, body)
    identity.last_step = max(identity.last_step, 2)
    await db.commit()
    await db.refresh(identity)
    return _progress(identity)


@router.post("/occupation", response_model=OnboardingProgress)
async def step_occupation(
    body: OccupationSelection,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> OnboardingProgress:
    set_occupation(identity, body)
    identity.last_step = max(identity.last_step, 3)
    await db.commit()
    await db.refresh(identity)
    return _progress(identity)


@router.post("/income-sources", response_model=OnboardingProgress)
async def step_income_sources(
    body: list[IncomeSourceIn],
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> OnboardingProgress:
    await add_income_sources(db, identity, body)
    identity.last_step = max(identity.last_step, 4)
    await db.commit()
    await db.refresh(identity)
    return _progress(identity)


@router.post("/banks", response_model=OnboardingProgress)
async def step_banks(
    body: list[BankAccountIn],
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> OnboardingProgress:
    await add_banks(db, identity, body)
    identity.last_step = max(identity.last_step, 5)
    await db.commit()
    await db.refresh(identity)
    return _progress(identity)


@router.post("/upi", response_model=OnboardingProgress)
async def step_upi(
    body: list[UPIAppIn],
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> OnboardingProgress:
    await add_upi_apps(db, identity, body)
    identity.last_step = max(identity.last_step, 6)
    await db.commit()
    await db.refresh(identity)
    return _progress(identity)


@router.post("/gig", response_model=OnboardingProgress)
async def step_gig(
    body: list[GigPlatformIn],
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> OnboardingProgress:
    await add_gigs(db, identity, body)
    identity.last_step = max(identity.last_step, 7)
    await db.commit()
    await db.refresh(identity)
    return _progress(identity)


@router.post("/permissions", response_model=OnboardingProgress)
async def step_permissions(
    body: PermissionsResponse,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> OnboardingProgress:
    set_permissions(identity, body)
    identity.last_step = max(identity.last_step, 8)
    await db.commit()
    await db.refresh(identity)
    return _progress(identity)


@router.post("/finish", response_model=OnboardingProgress)
async def step_finish(
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> OnboardingProgress:
    identity.onboarded = True
    identity.last_step = 10
    await db.commit()
    await db.refresh(identity)
    return _progress(identity)