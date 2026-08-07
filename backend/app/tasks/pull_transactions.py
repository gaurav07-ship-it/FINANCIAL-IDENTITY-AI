"""DEPRECATED shim — pull_consent_data is now inline in app/api/v1/aggregators/router.py."""
import warnings as _w

_w.warn(
    "app.tasks.pull_transactions.pull_consent_data is deprecated; "
    "AA pulls are synchronous in the request handler.",
    DeprecationWarning,
    stacklevel=2,
)


async def pull_consent_data(ctx, identity_id: str, consent_id: str) -> int:  # pragma: no cover
    raise NotImplementedError(
        "pull_consent_data has moved to app.api.v1.aggregators.router.pull_data"
    )
