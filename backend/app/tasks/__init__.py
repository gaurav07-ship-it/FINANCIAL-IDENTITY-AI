"""DEPRECATED — arq-based worker.

Vercel serverless has no long-running worker process. Nightly recompute
and AA pull jobs now live in:

- ``app/api/v1/cron.py``     — /cron/recompute-all, /cron/recompute-one
- ``app/services/qstash_client.py`` — Upstash QStash fan-out

The legacy module imports below are kept as no-ops so the rest of the
codebase can still ``from app.tasks.worker import WorkerSettings`` if
something references it. New code MUST NOT import from this package.
"""
