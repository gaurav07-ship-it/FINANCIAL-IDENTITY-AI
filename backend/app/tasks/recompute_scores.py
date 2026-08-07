"""DEPRECATED shim — recompute jobs are now under app/api/v1/cron.py."""
import warnings as _w

_w.warn(
    "app.tasks.recompute_scores.* is deprecated; "
    "use app.api.v1.cron.recompute_all / recompute_one.",
    DeprecationWarning,
    stacklevel=2,
)


async def recompute_score_for_identity(ctx, identity_id: str) -> dict:  # pragma: no cover
    raise NotImplementedError(
        "Moved to app.api.v1.cron.recompute_one (Vercel Cron + QStash)"
    )


async def recompute_all_scores(ctx) -> int:  # pragma: no cover
    raise NotImplementedError(
        "Moved to app.api.v1.cron.recompute_all (Vercel Cron)"
    )
