"""Database-agnostic type aliases for the ORM models.

`JSONB` (Postgres) becomes plain `JSON` on SQLite so the same model class
works for both production and tests. `UUID` is similarly remapped to
CHAR(36) on SQLite — we keep it as a Python uuid.UUID at the boundary.
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import JSON, CHAR, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB as _PG_JSONB, UUID as _PG_UUID


class _PortableJSONB(TypeDecorator):
    """JSONB on Postgres, JSON on everything else (SQLite for tests)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_PG_JSONB())
        return dialect.type_descriptor(JSON())


class _PortableUUID(TypeDecorator):
    """UUID column on Postgres, CHAR(36) elsewhere.

    Accepts the same constructor kwargs as Postgres's UUID (`as_uuid=True`)
    so call sites stay identical; we just ignore the kwarg on the SQLite
    branch since CHAR(36) always returns a string.
    """

    impl = CHAR
    cache_ok = True

    def __init__(self, *args, **kwargs) -> None:
        # Drop Postgres-only kwargs; everything else flows to the underlying impl.
        for pg_only in ("as_uuid",):
            kwargs.pop(pg_only, None)
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name != "postgresql":
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None or dialect.name == "postgresql":
            return value
        import uuid as _uuid

        return _uuid.UUID(value)


JSONB = _PortableJSONB
UUID = _PortableUUID


def stable_columns() -> list[sa.Index]:
    """Composite indexes that should exist on both backends."""
    # Kept here so the conftest can import them in one place if needed.
    return []
