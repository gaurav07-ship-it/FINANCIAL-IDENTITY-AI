"""Graph-backed read endpoints.

Backed by Neo4j (Aura in prod). Each endpoint is a thin Cypher wrapper
around the identity/counterparty/lender subgraphs.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.deps import get_current_identity
from app.models import Identity
from app.services.neo4j_client import neo4j_session

router = APIRouter(prefix="/graph", tags=["graph"])


def _require_neo4j() -> None:
    if not settings.neo4j_enabled:
        raise HTTPException(status_code=503, detail="Neo4j disabled")


@router.get("/identity/{identity_id}")
async def identity_neighbourhood(
    identity_id: str,
    hops: int = Query(default=2, ge=1, le=3),
    identity: Identity = Depends(get_current_identity),
) -> dict:
    _require_neo4j()
    try:
        uid = uuid.UUID(identity_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid identity id") from exc
    # Self-only or admin-of-self: a regular user can fetch their own id only.
    if uid != identity.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    cypher = """
    MATCH (i:Identity {id: $id})-[r*1..2]-(n)
    WITH i, r, n, relationships(r) AS rels
    RETURN i, collect({node: n, edges: rels}) AS neighbourhood
    LIMIT 200
    """
    async with neo4j_session() as session:
        result = await session.run(cypher, id=str(uid))
        record = await result.single()
        if not record:
            return {"nodes": [], "edges": []}
        return _format_graph(record)


@router.get("/clusters")
async def clusters() -> dict:
    _require_neo4j()
    cypher = """
    MATCH (i:Identity)-[:RECEIVED]->(c:Counterparty)
    WITH c, count(DISTINCT i) AS users
    WHERE users >= 2
    RETURN c.name AS name, c.kind AS kind, users
    ORDER BY users DESC
    LIMIT 50
    """
    async with neo4j_session() as session:
        result = await session.run(cypher)
        rows = [r.data() async for r in result]
    return {"clusters": rows}


@router.get("/counterparty/{name}")
async def counterparty(name: str) -> dict:
    _require_neo4j()
    cypher = """
    MATCH (c:Counterparty {name: $name})<-[r:RECEIVED]-(i:Identity)
    RETURN c.name AS name, i.id AS identity_id, count(r) AS txns,
           sum(r.amount) AS total, max(r.posted_at) AS last_seen
    ORDER BY total DESC LIMIT 100
    """
    async with neo4j_session() as session:
        result = await session.run(cypher, name=name)
        return {"name": name, "edges": [r.data() async for r in result]}


@router.get("/undeclared-platforms")
async def undeclared_platforms(
    identity: Identity = Depends(get_current_identity),
) -> dict:
    """Counterparties the user transacts with that aren't in their declared gigs."""
    _require_neo4j()
    cypher = """
    MATCH (c:Counterparty)<-[r:RECEIVED]-(i:Identity {id: $id})
    WITH c, sum(r.amount) AS total, count(r) AS txns
    WHERE NOT c.name IN $declared
    RETURN c.name AS name, total, txns
    ORDER BY total DESC LIMIT 25
    """
    declared = list(identity.gig_platforms or [])
    async with neo4j_session() as session:
        result = await session.run(cypher, id=str(identity.id), declared=declared)
        return {"undeclared": [r.data() async for r in result]}


def _format_graph(record) -> dict:
    """Serialise a Cypher result into vis-network-friendly nodes/edges."""
    nodes = []
    edges = []
    seen = set()

    i = record["i"]
    nodes.append({"id": i["id"], "label": i.get("name", i["id"]), "kind": "Identity"})
    seen.add(i["id"])

    for entry in record["neighbourhood"]:
        n = entry["node"]
        if n["id"] not in seen:
            nodes.append({"id": n["id"], "label": n.get("name", n["id"]), "kind": list(n.labels)[0] if hasattr(n, "labels") else "Node"})
            seen.add(n["id"])
        for e in entry["edges"]:
            edges.append({
                "source": e.start_node["id"],
                "target": e.end_node["id"],
                "type": e.type,
            })
    return {"nodes": nodes, "edges": edges}
