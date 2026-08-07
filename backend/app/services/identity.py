"""Identity write helpers — keep router code declarative."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BankAccount,
    Identity,
    IncomeSource,
    SelectedGigPlatform,
    SelectedIncomeSource,
    UPIApp,
)
from app.schemas.identity import IdentityResponse, PermissionsResponse
from app.schemas.onboarding import (
    BankAccountIn,
    GigPlatformIn,
    IncomeSourceIn,
    PersonalDetailsIn,
    UPIAppIn,
    OccupationSelection,
)


def next_step_for(identity: Identity) -> int:
    """Heuristic: which step should the wizard show next."""
    if identity.onboarded:
        return 11  # sentinel "done"
    s = identity.last_step
    # bump at least one step past any that have no data
    if not identity.name:
        return 1
    if not identity.occupation:
        return 3
    if not identity.sources:
        return 4
    if not identity.banks:
        return 5
    if not identity.upi_apps:
        return 6
    if not identity.gig_platforms and "Gig Platforms" in identity.sources:
        return 7
    if not identity.permissions or not identity.permissions.get("push"):
        return 8
    return max(s, 9)


def set_personal(identity: Identity, body: PersonalDetailsIn) -> None:
    identity.name = body.name
    if body.dob is not None:
        identity.dob = body.dob
    if body.phone is not None:
        identity.phone = body.phone
    if body.pan is not None:
        identity.pan = body.pan.upper()
    if body.city is not None:
        identity.city = body.city


def set_occupation(identity: Identity, body: OccupationSelection) -> None:
    identity.occupation = body.occupation
    identity.annual_goal = body.annual_goal


def set_permissions(identity: Identity, body: PermissionsResponse) -> None:
    identity.permissions = {
        "push": body.push,
        "primary_bank": body.primary_bank,
        "aa_consent": body.aa_consent,
    }


async def add_income_sources(
    db: AsyncSession, identity: Identity, items: Iterable[IncomeSourceIn]
) -> None:
    # Replace semantics — frontend is the source of truth for the step list
    await db.execute(delete(SelectedIncomeSource).where(SelectedIncomeSource.identity_id == identity.id))
    names: list[str] = []
    for item in items:
        names.append(item.name)
        income = await db.scalar(select(IncomeSource).where(IncomeSource.name == item.name))
        if income is None:
            income = IncomeSource(name=item.name)
            db.add(income)
            await db.flush()
        db.add(
            SelectedIncomeSource(
                identity_id=identity.id,
                income_source_id=income.id,
                monthly_income=item.monthly_income,
                primary=item.primary,
            )
        )
    identity.sources = names
    # Recompute monthly income = sum of selected sources
    identity.monthly_income = sum(i.monthly_income for i in items)


async def add_banks(
    db: AsyncSession, identity: Identity, items: Iterable[BankAccountIn]
) -> None:
    await db.execute(delete(BankAccount).where(BankAccount.identity_id == identity.id))
    summaries: list[dict] = []
    for item in items:
        db.add(
            BankAccount(
                identity_id=identity.id,
                bank_name=item.bank_name,
                account_last4=item.account_last4,
                is_primary=item.is_primary,
                statement_uploaded_at=item.statement_uploaded_at,
            )
        )
        summaries.append(
            {
                "bank": item.bank_name,
                "last4": item.account_last4,
                "primary": item.is_primary,
            }
        )
    identity.banks = summaries
    if any(i.is_primary for i in items):
        identity.permissions = {
            **(identity.permissions or {}),
            "primary_bank": True,
        }


async def add_upi_apps(
    db: AsyncSession, identity: Identity, items: Iterable[UPIAppIn]
) -> None:
    await db.execute(delete(UPIApp).where(UPIApp.identity_id == identity.id))
    names: list[str] = []
    for item in items:
        names.append(item.provider)
        db.add(UPIApp(identity_id=identity.id, provider=item.provider))
    identity.upi_apps = names


async def add_gigs(
    db: AsyncSession, identity: Identity, items: Iterable[GigPlatformIn]
) -> None:
    await db.execute(delete(SelectedGigPlatform).where(SelectedGigPlatform.identity_id == identity.id))
    names: list[str] = []
    for item in items:
        names.append(item.platform)
        db.add(SelectedGigPlatform(identity_id=identity.id, platform=item.platform))
    identity.gig_platforms = names


async def to_response(db: AsyncSession, identity: Identity) -> IdentityResponse:
    """Compose the STORE-shaped response: a single object the frontend knows how to render."""
    from app.schemas.identity import IdentityResponse as IR

    perms = identity.permissions or {}
    return IR(
        name=identity.name or "",
        dob=identity.dob,
        city=identity.city,
        phone=identity.phone,
        email=identity.email,
        pan=identity.pan,
        occupation=identity.occupation,
        annual_goal=identity.annual_goal,
        onboarded=identity.onboarded,
        last_step=identity.last_step,
        monthly_income=identity.monthly_income,
        sources=identity.sources or [],
        gig_platforms=identity.gig_platforms or [],
        upi_apps=identity.upi_apps or [],
        banks=identity.banks or [],
        goals=identity.goals or [],
        permissions=PermissionsResponse(
            push=perms.get("push", False),
            primary_bank=perms.get("primary_bank", False),
            aa_consent=perms.get("aa_consent", False),
        ),
        updated_at=identity.updated_at,
    )