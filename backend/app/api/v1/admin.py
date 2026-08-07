"""Admin endpoints — users, audit log, fraud signals, persisted offers. requires is_admin."""
from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import get_current_user
from app.models import AuditLog, LenderOffer, ScoreSnapshot, User
from app.services.analytics import detect_fraud_signals

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return user


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
    limit: int = 50,
) -> list[dict]:
    rows = list(
        (await db.scalars(select(User).order_by(User.created_at.desc()).limit(limit))).all()
    )
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "isActive": u.is_active,
            "isAdmin": u.is_admin,
            "lastLoginAt": u.last_login_at,
            "createdAt": u.created_at,
        }
        for u in rows
    ]


@router.get("/audit")
async def list_audit(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
    limit: int = 100,
) -> list[dict]:
    rows = list(
        (await db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))).all()
    )
    return [
        {
            "id": str(a.id),
            "actor": str(a.actor_user_id) if a.actor_user_id else None,
            "target": str(a.target_user_id) if a.target_user_id else None,
            "action": a.action,
            "detail": a.detail,
            "ip": a.ip,
            "userAgent": a.user_agent,
            "createdAt": a.created_at,
        }
        for a in rows
    ]


@router.get("/scores")
async def list_scores(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
    limit: int = 100,
) -> list[dict]:
    rows = list(
        (
            await db.scalars(
                select(ScoreSnapshot).order_by(ScoreSnapshot.computed_at.desc()).limit(limit)
            )
        ).all()
    )
    return [
        {
            "id": str(r.id),
            "identityId": str(r.identity_id),
            "computedAt": r.computed_at,
            "dnaScore": r.dna_score,
            "incomeQuality": r.income_quality,
        }
        for r in rows
    ]


@router.get("/fraud-signals")
async def fraud_signals(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    """Run fraud detection on a specific user's identity."""
    try:
        uid = _uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user id")
    user = await db.get(User, uid)
    if user is None or user.identity is None:
        raise HTTPException(status_code=404, detail="User or identity not found")
    result = await detect_fraud_signals(db, user.identity)
    db.add(
        AuditLog(
            actor_user_id=_.id,  # type: ignore[union-attr]
            target_user_id=user.id,
            action="admin_fraud_check",
            detail={"risk": result["risk"], "signals": len(result["signals"])},
        )
    )
    await db.commit()
    return {
        "userId": str(user.id),
        "email": user.email,
        **result,
    }


@router.get("/offers")
async def list_offers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
    limit: int = 100,
) -> list[dict]:
    """All persisted pre-approvals across users."""
    rows = list(
        (
            await db.scalars(
                select(LenderOffer).order_by(LenderOffer.computed_at.desc()).limit(limit)
            )
        ).all()
    )
    return [
        {
            "id": str(o.id),
            "identityId": str(o.identity_id),
            "lenderId": str(o.lender_id),
            "amountInr": o.amount_inr,
            "tenureMonths": o.tenure_months,
            "rateApr": float(o.rate_apr),
            "approvalPct": o.approval_pct,
            "emiInr": o.emi_inr,
            "disbursalHours": o.disbursal_hours,
            "reasonCodes": o.reason_codes,
            "computedAt": o.computed_at,
        }
        for o in rows
    ]


@router.post("/users/{user_id}/disable")
async def disable_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict:
    try:
        uid = _uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user id")
    target = await db.get(User, uid)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot disable yourself")
    target.is_active = False
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            target_user_id=target.id,
            action="disable_user",
            detail={"info": "admin disabled user"},
        )
    )
    await db.commit()
    return {"ok": True}
