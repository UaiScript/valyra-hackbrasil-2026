"""Configuração mínima de persistência, compatível com a Issue #9."""

from datetime import date
from functools import lru_cache
from pathlib import Path
from uuid import UUID

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[5]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Exigir o destino evita migrar ou semear um banco escolhido implicitamente.
    database_url: str
    cors_origin: str = "http://127.0.0.1:5173"
    demo_user_id: UUID = UUID("00000000-0000-0000-0000-000000000001")
    # Ausente: "hoje" vem do relógio em America/Sao_Paulo (core/clock.py).
    demo_today: date | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
