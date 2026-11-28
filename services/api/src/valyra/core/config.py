"""Configuração mínima de persistência, compatível com a Issue #9."""

from datetime import date
from functools import lru_cache
from pathlib import Path
from uuid import UUID

from pydantic import Field, SecretStr, field_validator
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

    # Chaves ficam mascaradas no repr para não vazarem em diagnóstico de configuração.
    gemini_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")
    # Configurável porque o Google desativa versões do Gemini sem novo deploy de código:
    # trocar a variável no Render basta para seguir um modelo novo.
    gemini_model: str = Field(default="gemini-3.8-flash", min_length=1)
    llm_timeout_seconds: int = Field(default=30, ge=1, le=120)
    llm_max_attempts: int = Field(default=2, ge=1, le=3)
    # Nos modelos com raciocínio, os tokens de pensamento entram neste teto; 2048 deixava
    # pouco espaço para o JSON e a resposta podia ser cortada antes de terminar.
    llm_max_output_tokens: int = Field(default=4096, ge=128, le=8192)
    # Token gratuito da brapi (ADR-0012); vazio limita a coleta aos tickers liberados sem token.
    brapi_token: SecretStr = SecretStr("")

    @field_validator("gemini_api_key", "openai_api_key", mode="before")
    @classmethod
    def _trim_key(cls, value: str | SecretStr) -> str:
        raw = value.get_secret_value() if isinstance(value, SecretStr) else value
        return raw.strip()

    @property
    def gemini_enabled(self) -> bool:
        key = self.gemini_api_key.get_secret_value()
        return bool(key) and key != "sua-chave-aqui"

    @property
    def openai_fallback_enabled(self) -> bool:
        # A presença da chave habilita o fallback; o limite financeiro é externo à aplicação.
        return bool(self.openai_api_key.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    return Settings()
