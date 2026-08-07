"""Identity / dashboard read API. Returns STORE-shaped JSON for the frontend."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_identity
from app.models import Identity
from app.schemas import (
    GoalsRequest,
    GoalsResponse,
    IdentityResponse,
    PermissionsResponse,
)
from app.services.goals import get_goals, set_goals
from app.services.identity import to_response

router = APIRouter(prefix="/identity", tags=["identity"])


@router.get("/me", response_model=IdentityResponse)
async def get_me(
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> IdentityResponse:
    return await to_response(db, identity)


@router.get("/goals", response_model=GoalsResponse)
async def get_goals_endpoint(
    identity: Identity = Depends(get_current_identity),
) -> GoalsResponse:
    return GoalsResponse(goals=list(identity.goals or []))


@router.put("/goals", response_model=GoalsResponse)
async def put_goals(
    body: GoalsRequest,
    identity: Identity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> GoalsResponse:
    await set_goals(db, identity, body.goals)
    await db.commit()
    await db.refresh(identity)
    return GoalsResponse(goals=list(identity.goals or []))
