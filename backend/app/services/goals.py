"""Goals write helpers — set / replace the user's financial goals list."""
from __future__ import annotations

from sqlalchemy import delete

from app.models import Goal, Identity


async def set_goals(db, identity: Identity, goals: list[str]) -> None:
    """Replace the user's goals with a de-duped list. Unknown goal strings
    are added to the catalog so they show up in autocomplete later.
    """
    # normalise
    seen: set[str] = set()
    cleaned: list[str] = []
    for g in goals:
        if not g:
            continue
        key = g.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        cleaned.append(key)

    # ensure each goal exists in the catalog
    for name in cleaned:
        existing = await db.scalar(Goal.__table__.select().where(Goal.name == name))
        if existing is None:
            db.add(Goal(name=name))

    identity.goals = cleaned


async def get_goals(db, identity: Identity) -> list[str]:
    return list(identity.goals or [])
