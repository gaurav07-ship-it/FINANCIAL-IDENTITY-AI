"""Mock provider — generates fake bank/UPI data so the dev experience is real.

This is what runs when AGGREGATOR_PROVIDER=mock. Swap to setu.py in prod.
"""
from __future__ import annotations

import asyncio
import random
import uuid
from datetime import date, datetime, timedelta, timezone

from app.services.aggregators.base import (
    AggregatorProvider,
    ConsentHandle,
    ConsentRequest,
)


class MockProvider:
    def name(self) -> str:
        return "mock"

    async def create_consent(self, req: ConsentRequest) -> ConsentHandle:
        # Simulate a network round-trip
        await asyncio.sleep(0.05)
        consent_id = f"mock-{uuid.uuid4().hex[:12]}"
        today = date.today()
        return ConsentHandle(
            consent_id=consent_id,
            status="ACTIVE",  # in dev we auto-approve; the real provider would be PENDING
            redirect_url=f"https://mock.local/approve/{consent_id}",
            data_range_from=date.fromisoformat(req.from_date) if req.from_date else today - timedelta(days=365),
            data_range_to=date.fromisoformat(req.to_date) if req.to_date else today,
            expires_at=datetime.now(tz=timezone.utc) + timedelta(days=90),
            payload={"mock": True, "fi_types": req.fi_types},
        )

    async def fetch_data(self, consent_id: str) -> dict:
        await asyncio.sleep(0.1)
        return _generate_fake_payload(consent_id)

    async def revoke_consent(self, consent_id: str) -> bool:
        await asyncio.sleep(0.02)
        return True


def _generate_fake_payload(consent_id: str) -> dict:
    """Build a realistic-looking FI payload for the last 90 days."""
    today = date.today()
    accounts: list[dict] = []
    transactions: list[dict] = []

    banks = [
        ("HDFC Bank", "HDFC0001234", "50100123456789"),
        ("ICICI Bank", "ICIC0005678", "602901234567"),
    ]
    for bank_name, ifsc, acct in banks:
        accounts.append(
            {
                "fi_type": "DEPOSIT",
                "bank": bank_name,
                "ifsc": ifsc,
                "account_last4": acct[-4:],
                "balance": random.uniform(20_000, 250_000),
                "masked_account": f"XXXXXX{acct[-4:]}",
            }
        )

    # 60 days of transactions
    rng = random.Random(consent_id)
    counterparties = [
        ("Client A Pvt Ltd", "client_payment"),
        ("Zomato", "gig_payout"),
        ("Swiggy", "gig_payout"),
        ("Salary / Employer", "salary"),
        ("Amazon Marketplace", "sales"),
        ("Mutual Fund SIP", "investment_income"),
        ("Tenant — Flat 12B", "rental"),
    ]
    expense_parties = [
        ("HDFC Credit Card", "emi"),
        ("BESCOM", "utility"),
        ("Airtel Broadband", "utility"),
        ("Swiggy — Personal", "other"),
    ]

    for d_offset in range(60):
        day = today - timedelta(days=d_offset)
        if day.weekday() < 5 and rng.random() < 0.7:
            # salary credit on 1st
            if day.day == 1:
                transactions.append(
                    {
                        "posted_at": day.isoformat(),
                        "amount": 85_000.0,
                        "direction": "credit",
                        "category": "salary",
                        "counterparty": "Salary / Employer",
                        "source": "HDFC Bank",
                    }
                )
        for cp, cat in counterparties:
            if rng.random() < 0.45:
                amt = rng.uniform(800, 22_000)
                transactions.append(
                    {
                        "posted_at": day.isoformat(),
                        "amount": round(amt, 2),
                        "direction": "credit",
                        "category": cat,
                        "counterparty": cp,
                        "source": "HDFC Bank",
                    }
                )
        for cp, cat in expense_parties:
            if rng.random() < 0.3:
                amt = rng.uniform(120, 4_500)
                transactions.append(
                    {
                        "posted_at": day.isoformat(),
                        "amount": round(amt, 2),
                        "direction": "debit",
                        "category": cat,
                        "counterparty": cp,
                        "source": "HDFC Bank",
                    }
                )

    return {
        "consent_id": consent_id,
        "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
        "accounts": accounts,
        "transactions": transactions,
    }
