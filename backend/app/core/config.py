"""Application settings, loaded from environment / .env (pydantic-settings)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# The canonical .env lives at the repo root, but the backend is launched from
# ./backend. Resolve the root .env by absolute path, then also honour a local
# backend/.env if present (later files win).
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_ENV), ".env"),
        extra="ignore",
        case_sensitive=False,
    )

    # App
    app_name: str = "Data Skill Marketplace"
    api_v1_prefix: str = "/api/v1"
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Workspace storage — each workspace is a git-backed OKF bundle on disk.
    # Configurable; never hardcode a path elsewhere.
    workspaces_root: str = str(Path(__file__).resolve().parents[3] / "data" / "workspaces")

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://eakso:eakso@postgres:5432/eakso"

    # FalkorDB
    falkordb_host: str = "falkordb"
    falkordb_port: int = 6379
    falkordb_graph: str = "eakso"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # JWT
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_min: int = 15
    jwt_refresh_ttl_days: int = 7

    # Dev admin
    dev_admin_username: str = "admin"
    dev_admin_password: str = "admin"

    # LDAP
    ldap_enabled: bool = False
    ldap_uri: str = ""
    ldap_bind_dn: str = ""
    ldap_bind_password: str = ""
    ldap_user_base_dn: str = ""
    ldap_group_base_dn: str = ""
    ldap_group_role_map: dict[str, str] = {}

    # LLM provider — pluggable. "auto" (default) picks a configured provider from
    # the keys below (OpenRouter → Anthropic → OpenAI), else falls back to the
    # offline "local" provider (hash embeddings, rules-only evals). Set an explicit
    # value to pin it; "local" forces offline even when a key is present.
    llm_provider: str = "auto"  # auto | local | openrouter | anthropic | openai

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    embedding_model: str = "openai/text-embedding-3-small"
    embedding_dim: int = 1536
    chat_model: str = "openai/gpt-oss-120b:free"

    # Other providers (optional)
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("ldap_group_role_map", mode="before")
    @classmethod
    def _parse_map(cls, v: object) -> object:
        if isinstance(v, str) and v.strip():
            return json.loads(v)
        return v or {}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
