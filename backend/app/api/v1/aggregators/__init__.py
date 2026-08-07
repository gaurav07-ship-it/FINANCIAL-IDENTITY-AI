"""Re-export the aggregators router under the package namespace."""
from app.api.v1.aggregators.router import router

__all__ = ["router"]
