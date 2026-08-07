"""v1 API package."""
from fastapi import APIRouter

from app.api.v1 import (
    admin,
    aggregators,
    ai,
    auth,
    cron,
    graph,
    identity,
    lenders,
    onboarding,
    opportunities,
    scoring,
    webhooks,
)

api_v1 = APIRouter(prefix="/v1")
api_v1.include_router(auth.router)
api_v1.include_router(onboarding.router)
api_v1.include_router(identity.router)
api_v1.include_router(scoring.router)
api_v1.include_router(lenders.router)
api_v1.include_router(opportunities.router)
api_v1.include_router(aggregators.router)
api_v1.include_router(ai.router)
api_v1.include_router(graph.router)
api_v1.include_router(webhooks.router)
api_v1.include_router(cron.router)
api_v1.include_router(admin.router)
