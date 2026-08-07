"""DEPRECATED shim — replaced by app/api/v1/cron.py + QStash."""
import warnings as _w

_w.warn(
    "app.tasks.worker.WorkerSettings is deprecated; use app.api.v1.cron "
    "+ Upstash QStash instead (Vercel serverless has no long-lived workers).",
    DeprecationWarning,
    stacklevel=2,
)


class WorkerSettings:  # pragma: no cover - deprecated stub
    """Legacy arq settings — kept only so old imports don't break at import time."""

    redis_settings = None
    functions: list = []
    on_startup = None
    on_shutdown = None
    cron_jobs: list = []
