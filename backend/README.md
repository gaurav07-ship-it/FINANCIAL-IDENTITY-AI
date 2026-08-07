# Financial Identity AI — Backend

FastAPI service that turns the static frontend into a real product. Owns auth,
DB, scoring, AA integration, lender offers, opportunity engine, and the work
queue that ties them together.

## Stack

- **API**: FastAPI 0.115 (async)
- **DB**: Postgres 16 via SQLAlchemy 2.0 async + asyncpg
- **Migrations**: Alembic
- **Cache / queue**: Redis 7 via arq
- **Auth**: JWT in HttpOnly Secure cookies, argon2id password hashing
- **Logging**: structlog (JSON in prod, pretty in dev)
- **Aggregators**: provider adapter (`mock` for dev, `setu` for prod)

## Quick start

```bash
cp .env.example .env
# tweak COOKIE_SECURE=false and JWT_SECRET for your machine

docker compose up -d              # postgres + redis
pip install -e .                  # or: uv pip install -r requirements
alembic upgrade head              # apply schema
python -m app.seed                # seed catalog + Arjun demo user
uvicorn app.main:app --reload --port 8000
arq app.tasks.worker.WorkerSettings   # in a second terminal
```

- API: <http://localhost:8000/docs> (dev only)
- API base: `/api/v1`
- Health: `GET /health`

## Demo user

After running `python -m app.seed`:

- email: `arjun@joshi.studio`
- password: `Arjun@2026`

Also seeded: 6 income sources, 6 gig platforms, 5 UPI apps, 5 banks, 8 lenders,
6 opportunities.

## Layout

```
app/
├── api/v1/            # FastAPI routers (thin)
├── models/            # SQLAlchemy 2.0 declarative models
├── schemas/           # Pydantic v2 DTOs (mirror STORE shape)
├── services/
│   ├── scoring/       # engine interface + rule-based impl + snapshots
│   ├── aggregators/   # provider adapter (mock / setu stubs)
│   ├── identity.py    # onboarding write helpers
│   ├── lenders.py     # offer computation
│   ├── twin.py        # what-if simulator
│   └── aggregation.py # AA → Transaction normaliser
├── tasks/             # arq jobs (pull, recompute)
├── config.py          # Pydantic Settings
├── db.py              # engine + SessionLocal
├── security.py        # JWT + argon2 + cookie helpers
├── deps.py            # FastAPI dependencies (current_user, current_identity)
├── logging_setup.py
├── main.py            # FastAPI app entry point
└── seed.py            # catalogues + demo user
```

## API surface

| Method | Path                              | Purpose                          |
|--------|-----------------------------------|----------------------------------|
| POST   | `/api/v1/auth/register`           | Create account + set cookies     |
| POST   | `/api/v1/auth/login`              | Issue access + refresh cookies   |
| POST   | `/api/v1/auth/refresh`            | Rotate the refresh token         |
| POST   | `/api/v1/auth/logout`             | Revoke the refresh token         |
| GET    | `/api/v1/auth/me`                 | Current user                     |
| GET    | `/api/v1/identity/me`             | STORE-shaped identity object     |
| POST   | `/api/v1/onboarding/{step}`       | Autosave per step                |
| GET    | `/api/v1/score/dna`               | Compute + persist DNA snapshot   |
| GET    | `/api/v1/score/income-quality`    | IQ + CV + YoY                    |
| GET    | `/api/v1/score/history`           | Last N snapshots                 |
| POST   | `/api/v1/score/twin/simulate`     | What-if cashflow                 |
| GET    | `/api/v1/lenders/offers`          | Live offers for the user         |
| POST   | `/api/v1/lenders/offer/{id}/persist` | Persist a pre-approval         |
| GET    | `/api/v1/opportunities`           | Personalised plays               |
| POST   | `/api/v1/aggregators/consent`     | Create AA consent                |
| POST   | `/api/v1/aggregators/consent/{id}/pull` | Pull FI data                  |
| GET    | `/api/v1/aggregators/consents`    | List consents                    |
| POST   | `/v1/webhooks/consent/...`        | Provider callbacks (no auth)     |
| GET    | `/api/v1/admin/{users,audit,scores}` | Admin views (is_admin required) |

All authenticated routes expect the `fia_access` HttpOnly cookie set by
`/auth/login`. CSRF isn't needed for the same-site flow; if you ever expose
the API to a different origin, swap to a CSRF token strategy.

## Scoring parity

The rule-based engine (`app/services/scoring/rules.py`) is a 1:1 port of the
formulas in `frontend/assets/store.js`. Parity tests live in
`tests/test_scoring.py` and assert identical numeric outputs for any given
input. When you swap to an ML model, implement the same `ScoringEngine`
protocol and run parity tests against the recorded labels.

## Production notes

- Set `ENV=prod`, `COOKIE_SECURE=true`, real `JWT_SECRET`.
- Swap `AGGREGATOR_PROVIDER=setu` and add credentials.
- Run `alembic upgrade head` instead of relying on the dev auto-create.
- Add a reverse proxy (nginx, Caddy) for TLS — the cookies are `Secure` in prod.
- Tune `pool_size` / `max_overflow` in `app/db.py` for your concurrency.
- Replace the auto-create branch in `app/main.py` lifespan with a no-op.

## Tests

```bash
pytest -q
```

`tests/test_scoring.py` is pure-Python (no DB) and runs in CI everywhere.
The rest use a Postgres + Redis test stack via `tests/conftest.py`.