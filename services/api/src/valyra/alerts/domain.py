"""Regras puras dos alertas: chave de deduplicação e templates (sem banco, HTTP ou LLM)."""

from datetime import date
from uuid import UUID

CASH_PRESSURE = "cash_pressure"
WARNING = "warning"


def cash_dedup_key(account_id: UUID, today: date) -> str:
    # O mês de hoje (ADR-0010, seção 6) limita a um alerta por conta por mês.
    return f"cash:{account_id}:{today.year:04d}-{today.month:02d}"


def format_brl(cents: int) -> str:
    """Centavos inteiros em reais no padrão brasileiro, sem passar por float."""
    sign = "-" if cents < 0 else ""
    reais, centavos = divmod(abs(cents), 100)
    return f"{sign}R$ {reais:,}".replace(",", ".") + f",{centavos:02d}"


def cash_pressure_text(
    min_balance_cents: int, min_balance_date: date, days: int
) -> tuple[str, str]:
    """Título e mensagem do alerta; só números calculados pela projeção entram no texto."""
    title = "Saldo previsto negativo"
    message = (
        f"A projeção dos próximos {days} dias indica saldo mínimo de "
        f"{format_brl(min_balance_cents)} em {min_balance_date:%d/%m/%Y}."
    )
    return title, message
