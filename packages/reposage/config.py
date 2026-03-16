from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://reposage:reposage@postgres:5432/reposage"
    sync_database_url: str = "postgresql+psycopg://reposage:reposage@postgres:5432/reposage"
    redis_url: str = "redis://redis:6379/0"
    rq_queue_name: str = "reposage-index"

    openai_api_key: SecretStr | None = None
    openai_response_model: str = "gpt-5-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536

    github_token: SecretStr | None = None

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    storage_root: Path = Path("storage")
    max_repository_size_mb: int = 100
    max_file_size_kb: int = 256
    max_total_files: int = 5000
    chunk_max_chars: int = 2200
    chunk_overlap_lines: int = 10

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def max_repository_size_bytes(self) -> int:
        return self.max_repository_size_mb * 1024 * 1024

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_kb * 1024

    @property
    def uploads_dir(self) -> Path:
        return self.storage_root / "uploads"

    @property
    def workspaces_dir(self) -> Path:
        return self.storage_root / "workspaces"

    @property
    def temp_dir(self) -> Path:
        return self.storage_root / "tmp"

    def ensure_storage(self) -> None:
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_storage()
    return settings

