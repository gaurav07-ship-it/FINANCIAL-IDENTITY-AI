"""Synchronise the Neo4j graph from the Postgres system of record.

We rebuild in three places:

- After any ``Identity`` or ``Transaction`` insert (post-commit hook).
- After a webhook ingest from the AA provider.
- On demand via ``rebuild_graph()`` (admin-only cron endpoint).

Pattern: the graph is a *derived* cache. If it's missing or stale, we
walk the truth in Postgres and replay it. Never write to Neo4j without
a corresponding Postgres row.
"""
from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models import Identity, Transaction
from app.services.neo4j_client import neo4j_session


SCHEMA_CYPHER = [
    "CREATE CONSTRAINT identity_id IF NOT EXISTS FOR (i:Identity) REQUIRE i.id IS UNIQUE",
    "CREATE CONSTRAINT counterparty_id IF NOT EXISTS FOR (c:Counterparty) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT lender_id IF NOT EXISTS FOR (l:Lender) REQUIRE l.id IS UNIQUE",
    "CREATE INDEX tx_posted_at IF NOT EXISTS FOR ()-[r:RECEIVED]-() ON (r.posted_at)",
]


async def ensure_schema() -> None:
    """Idempotent: create constraints + indexes. Call once at startup."""
    async with neo4j_session() as session:
        for stmt in SCHEMA_CYPHER:
            await session.run(stmt)


async def upsert_identity(identity: Identity) -> None:
    async with neo4j_session() as session:
        await session.run(
            """
            MERGE (i:Identity {id: $id})
            SET i.name = $name,
                i.occupation = $occupation,
                i.monthly_income = $monthly_income,
                i.dna_score = $dna_score,
                i.onboarded = $onboarded
            """,
            id=str(identity.id),
            name=identity.name or "",
            occupation=identity.occupation or "",
            monthly_income=identity.monthly_income,
            dna_score=_latest_dna_score(identity),
            onboarded=bool(identity.onboarded),
        )


async def upsert_transaction(tx: Transaction) -> None:
    async with neo4j_session() as session:
        await session.run(
            """
            MERGE (i:Identity {id: $identity_id})
            MERGE (c:Counterparty {id: $cp_id})
              ON CREATE SET c.name = $cp_name
              ON MATCH  SET c.name = $cp_name
            MERGE (i)-[r:RECEIVED {posted_at: $posted_at, amount: $amount}]->(c)
              ON CREATE SET r.category = $category,
                            r.direction = $direction,
                            r.source = $source
            """,
            identity_id=str(tx.identity_id),
            cp_id=f"{tx.identity_id}:{tx.counterparty}",
            cp_name=tx.counterparty or "unknown",
            posted_at=tx.posted_at.isoformat(),
            amount=float(tx.amount_inr),
            category=tx.category.value,
            direction=tx.direction.value,
            source=tx.source or "",
        )


async def rebuild_graph(batch: int = 200) -> dict:
    """Walk every identity and transaction in Postgres, replay into Neo4j."""
    await ensure_schema()
    counts = {"identities": 0, "transactions": 0}

    async with SessionLocal() as db:
        identities: Iterable[Identity] = (await db.scalars(select(Identity))).all()
        for ident in identities:
            await upsert_identity(ident)
            counts["identities"] += 1

        transactions: Iterable[Transaction] = (await db.scalars(select(Transaction))).all()
        for tx in transactions:
            await upsert_transaction(tx)
            counts["transactions"] += 1

    return counts


def _latest_dna_score(identity: Identity) -> int:
    """Pulled from the in-memory relationship; gracefully 0 if not loaded."""
    try:
        snap = identity.score_snapshots[0] if getattr(identity, "score_snapshots", None) else None
        return int(snap.dna_score) if snap else 0
    except Exception:
        return 0
