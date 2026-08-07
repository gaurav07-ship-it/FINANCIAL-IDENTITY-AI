"""Application configuration loaded from environment / .env file."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    env: Literal["dev", "staging", "prod"] = "dev"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5500"])
    cron_secret: str = ""  # required in prod; gates /api/v1/cron/* routes

    # --- Database ---
    database_url: str = "postgresql+asyncpg://fia:fia_dev_only@localhost:5432/fia"
    database_url_sync: str = "postgresql://fia:fia_dev_only@localhost:5432/fia"

    # --- Redis (Upstash in prod; only used by rate-limiter) ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Auth ---
    jwt_secret: str = "dev-secret-change-me"
    jwt_alg: str = "HS256"
    access_token_ttl_min: int = 15
    refresh_token_ttl_days: int = 14
    cookie_secure: bool = False
    cookie_domain: str = ""

    # --- Aggregator providers ---
    aggregator_provider: Literal["mock", "setu", "finbox"] = "mock"
    setu_client_id: str = ""
    setu_client_secret: str = ""
    setu_base_url: str = "https://prod.setu.co"
    finbox_api_key: str = ""

    # --- Neo4j (Aura in prod) ---
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    neo4j_enabled: bool = False  # turn on via NEO4J_ENABLED=true in prod

    # --- AI / Anthropic ---
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"
    scoring_engine: Literal["rules", "ai"] = "rules"
    ai_enabled: bool = False

    # --- Upstash QStash (Vercel Cron fan-out) ---
    qstash_token: str = ""
    qstash_current_signing_key: str = ""
    qstash_next_signing_key: str = ""
    qstash_base_url: str = "https://qstash.upstash.io"

    # --- Monitoring ---
    sentry_dsn: str = ""

    # --- Seed ---
    seed_demo_user: bool = True
    seed_demo_email: str = "arjun@joshi.studio"
    seed_demo_password: str = "Arjun@2026"

    @computed_field  # type: ignore[misc]
    @property
    def is_dev(self) -> bool:
        return self.env == "dev"

    @computed_field  # type: ignore[misc]
    @property
    def is_prod(self) -> bool:
        return self.env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
