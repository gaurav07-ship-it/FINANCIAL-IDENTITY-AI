"""Seed an Arjun-shaped demo user so the showcase has data on first load."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.db import SessionLocal
from app.models import (
    Bank,
    GigPlatform,
    Identity,
    IncomeSource,
    Lender,
    Opportunity,
    SelectedGigPlatform,
    SelectedIncomeSource,
    UPIProvider,
    User,
)
from app.security import hash_password


CATALOG_INCOME_SOURCES = [
    ("Client Projects", "🧑‍💼", "Freelance / consulting engagements"),
    ("Salaried role", "💼", "Fixed monthly salary"),
    ("Gig Platforms", "🛵", "Zomato / Swiggy / Rapido etc."),
    ("Online Sales", "🛒", "Amazon / Flipkart / Etsy etc."),
    ("Investments", "📈", "Mutual funds, stocks, FDs"),
    ("Rental Income", "🏠", "Rental property tenants"),
]

CATALOG_GIGS = ["Zomato", "Swiggy", "Rapido", "Uber", "Ola", "Dunzo"]
CATALOG_UPI = ["PhonePe", "Google Pay", "Paytm", "BHIM", "Amazon Pay"]
CATALOG_BANKS = [
    ("HDFC Bank", "HDFC"),
    ("ICICI Bank", "ICIC"),
    ("SBI", "SBIN"),
    ("Axis Bank", "UTIB"),
    ("Kotak Mahindra Bank", "KKBK"),
]

CATALOG_OPPORTUNITIES = [
    {
        "category": "diversification",
        "ribbon": "DNA Fix",
        "title": "Add a 2nd income stream",
        "description": "Diversify across gigs to lower your top-client share below 50%.",
        "impact": "+12 DNA",
        "price": "Free",
        "cta": "Browse gigs",
        "priority": 90,
        "icon": "🧬",
    },
    {
        "category": "savings",
        "ribbon": "Boost",
        "title": "Open a Liquid Mutual Fund",
        "description": "Earn 7.2% p.a. on idle cash, fully liquid, no exit load.",
        "impact": "+6% APY",
        "price": "₹0 AMC",
        "cta": "Open in 3 min",
        "priority": 80,
        "icon": "💧",
    },
    {
        "category": "growth",
        "ribbon": "Upskill",
        "title": "Tax-saving ELSS fund",
        "description": "Save up to ₹46,800 under 80C while compounding on equity.",
        "impact": "+₹46,800/yr",
        "price": "₹500 min",
        "cta": "Start SIP",
        "priority": 70,
        "icon": "🌱",
    },
    {
        "category": "risk",
        "ribbon": "Protect",
        "title": "Term Insurance — 1 Cr",
        "description": "Guaranteed acceptance for non-smokers, no medical.",
        "impact": "1 Cr cover",
        "price": "₹850/mo",
        "cta": "Get quote",
        "priority": 60,
        "icon": "🛡️",
    },
    {
        "category": "income_quality",
        "ribbon": "Habit",
        "title": "Set up auto-sweep to RD",
        "description": "Round off every UPI credit into a recurring deposit.",
        "impact": "+9 IQ",
        "price": "₹100 min",
        "cta": "Set up",
        "priority": 50,
        "icon": "🏦",
    },
    {
        "category": "stability",
        "ribbon": "Stabilise",
        "title": "Client contract review",
        "description": "Get your retainer agreement reviewed in 24h.",
        "impact": "−12% volatility",
        "price": "₹499",
        "cta": "Book review",
        "priority": 40,
        "icon": "📄",
    },
]


CATALOG_LENDERS = [
    {
        "name": "DhanSaarthi",
        "logo_gradient": "linear-gradient(135deg,#22c55e,#15803d)",
        "min_amount_inr": 50_000,
        "max_amount_inr": 1_500_000,
        "min_tenure_months": 6,
        "max_tenure_months": 36,
        "rate_min": 12.0,
        "rate_max": 24.0,
        "active": True,
        "notes": {"type": "NBFC", "turnaround": "24h"},
    },
    {
        "name": "QuickFund",
        "logo_gradient": "linear-gradient(135deg,#3b82f6,#1d4ed8)",
        "min_amount_inr": 25_000,
        "max_amount_inr": 500_000,
        "min_tenure_months": 3,
        "max_tenure_months": 24,
        "rate_min": 14.5,
        "rate_max": 28.0,
        "active": True,
        "notes": {"type": "Fintech", "turnaround": "6h"},
    },
    {
        "name": "BharatCredit",
        "logo_gradient": "linear-gradient(135deg,#f59e0b,#b45309)",
        "min_amount_inr": 100_000,
        "max_amount_inr": 2_000_000,
        "min_tenure_months": 12,
        "max_tenure_months": 48,
        "rate_min": 10.5,
        "rate_max": 18.0,
        "active": True,
        "notes": {"type": "Bank", "turnaround": "48h"},
    },
    {
        "name": "Aarambh Loans",
        "logo_gradient": "linear-gradient(135deg,#a855f7,#7e22ce)",
        "min_amount_inr": 10_000,
        "max_amount_inr": 200_000,
        "min_tenure_months": 1,
        "max_tenure_months": 12,
        "rate_min": 16.0,
        "rate_max": 32.0,
        "active": True,
        "notes": {"type": "Micro-finance", "turnaround": "12h"},
    },
    {
        "name": "NiveshLine",
        "logo_gradient": "linear-gradient(135deg,#06b6d4,#0e7490)",
        "min_amount_inr": 75_000,
        "max_amount_inr": 1_000_000,
        "min_tenure_months": 6,
        "max_tenure_months": 36,
        "rate_min": 11.0,
        "rate_max": 20.0,
        "active": True,
        "notes": {"type": "NBFC", "turnaround": "36h"},
    },
    {
        "name": "RupeeGo",
        "logo_gradient": "linear-gradient(135deg,#ef4444,#991b1b)",
        "min_amount_inr": 5_000,
        "max_amount_inr": 100_000,
        "min_tenure_months": 1,
        "max_tenure_months": 6,
        "rate_min": 18.0,
        "rate_max": 36.0,
        "active": True,
        "notes": {"type": "PayLater", "turnaround": "1h"},
    },
    {
        "name": "GigMate Capital",
        "logo_gradient": "linear-gradient(135deg,#10b981,#047857)",
        "min_amount_inr": 20_000,
        "max_amount_inr": 300_000,
        "min_tenure_months": 3,
        "max_tenure_months": 18,
        "rate_min": 14.0,
        "rate_max": 26.0,
        "active": True,
        "notes": {"type": "Gig-specialised", "turnaround": "8h"},
    },
    {
        "name": "Samriddhi Bank",
        "logo_gradient": "linear-gradient(135deg,#6366f1,#3730a3)",
        "min_amount_inr": 200_000,
        "max_amount_inr": 5_000_000,
        "min_tenure_months": 12,
        "max_tenure_months": 60,
        "rate_min": 9.5,
        "rate_max": 14.5,
        "active": True,
        "notes": {"type": "Public-sector bank", "turnaround": "72h"},
    },
]


async def _seed_catalogs(db) -> None:
    for name, icon, desc in CATALOG_INCOME_SOURCES:
        existing = await db.scalar(select(IncomeSource).where(IncomeSource.name == name))
        if existing is None:
            db.add(IncomeSource(name=name, icon=icon, description=desc))
    for name in CATALOG_GIGS:
        existing = await db.scalar(select(GigPlatform).where(GigPlatform.name == name))
        if existing is None:
            db.add(GigPlatform(name=name))
    for name in CATALOG_UPI:
        existing = await db.scalar(select(UPIProvider).where(UPIProvider.name == name))
        if existing is None:
            db.add(UPIProvider(name=name))
    for name, _ifsc in CATALOG_BANKS:
        existing = await db.scalar(select(Bank).where(Bank.name == name))
        if existing is None:
            db.add(Bank(name=name))
    for opp in CATALOG_OPPORTUNITIES:
        existing = await db.scalar(select(Opportunity).where(Opportunity.title == opp["title"]))
        if existing is None:
            db.add(Opportunity(**opp))
    for l in CATALOG_LENDERS:
        existing = await db.scalar(select(Lender).where(Lender.name == l["name"]))
        if existing is None:
            db.add(Lender(**l))
    await db.commit()


async def _seed_demo_user(db) -> None:
    from app.config import settings

    if not settings.seed_demo_user:
        return
    user = await db.scalar(select(User).where(User.email == settings.seed_demo_email))
    if user is not None:
        return

    user = User(
        email=settings.seed_demo_email,
        password_hash=hash_password(settings.seed_demo_password),
        is_active=True,
        is_admin=False,
    )
    db.add(user)
    await db.flush()

    identity = Identity(
        user_id=user.id,
        name="Arjun Joshi",
        email=settings.seed_demo_email,
        phone="+919876543210",
        city="Bengaluru",
        occupation="freelancer",
        annual_goal=2_400_000,
        onboarded=True,
        last_step=10,
        monthly_income=185_000,
        sources=["Client Projects", "Salaried role", "Gig Platforms", "Investments"],
        gig_platforms=["Zomato", "Swiggy"],
        upi_apps=["PhonePe", "Google Pay"],
        banks=[
            {"bank": "HDFC Bank", "last4": "6789", "primary": True},
            {"bank": "ICICI Bank", "last4": "1234", "primary": False},
        ],
        goals=["Buy a house", "Retire at 50"],
        permissions={
            "push": True,
            "primary_bank": True,
            "aa_consent": True,
        },
    )
    db.add(identity)
    await db.flush()

    # Pick sources from the catalog
    for src_name, monthly, primary in [
        ("Client Projects", 95_000, True),
        ("Salaried role", 60_000, False),
        ("Gig Platforms", 20_000, False),
        ("Investments", 10_000, False),
    ]:
        src = await db.scalar(select(IncomeSource).where(IncomeSource.name == src_name))
        if src:
            db.add(
                SelectedIncomeSource(
                    identity_id=identity.id,
                    income_source_id=src.id,
                    monthly_income=monthly,
                    primary=primary,
                )
            )
    for g in ["Zomato", "Swiggy"]:
        db.add(SelectedGigPlatform(identity_id=identity.id, platform=g))
    await db.commit()


async def main() -> None:
    from app.db import engine
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        await _seed_catalogs(db)
        await _seed_demo_user(db)
    print("[OK] seed complete")


if __name__ == "__main__":
    asyncio.run(main())
