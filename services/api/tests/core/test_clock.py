"""Data de "hoje" (ADR-0010, seção 2), sem PostgreSQL e sem depender do relógio real."""

from datetime import UTC, date, datetime

from valyra.core import clock
from valyra.core.config import Settings


def _settings(**extra) -> Settings:
    return Settings(database_url="postgresql+psycopg://127.0.0.1/unused", _env_file=None, **extra)


def test_demo_today_fixa_a_data(monkeypatch):
    monkeypatch.setattr(clock, "get_settings", lambda: _settings(demo_today="2026-11-07"))
    assert clock.get_today() == date(2026, 11, 7)


def test_sem_demo_today_usa_calendario_de_sao_paulo(monkeypatch):
    monkeypatch.delenv("DEMO_TODAY", raising=False)
    monkeypatch.setattr(clock, "get_settings", _settings)

    class RelogioFixo(datetime):
        @classmethod
        def now(cls, tz=None):
            # 02:00 UTC de 08/11 ainda é 23:00 de 07/11 em São Paulo (UTC-3).
            return datetime(2026, 11, 8, 2, 0, tzinfo=UTC).astimezone(tz)

    monkeypatch.setattr(clock, "datetime", RelogioFixo)
    assert clock.get_today() == date(2026, 11, 7)
