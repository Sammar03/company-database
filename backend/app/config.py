"""Application settings loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Secrets
    gemini_api_key: str = ""
    groq_api_key: str = ""
    # Shared secret for the API. When set, clients must send `X-API-Key`.
    # When empty, auth is disabled (local dev) — set it in production.
    api_key: str = ""

    # Vector store (Neon Postgres + pgvector)
    database_url: str = ""

    # Models
    embed_model: str = "gemini-embedding-2"
    embed_dims: int = 768
    gen_model: str = "llama-3.3-70b-versatile"

    # Chunking / retrieval
    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k: int = 5

    # Limits
    max_upload_mb: int = 25
    max_chunks_per_doc: int = 1000  # cap embedding calls/cost per uploaded file
    max_files_per_request: int = 20  # cap files per upload request
    max_history_turns: int = 6

    # CORS — comma-separated origins; the Vite dev origin by default.
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
