"""Casos de uso dos alertas (Issue #47); é a única porta de entrada para outros módulos."""

from datetime import date
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from valyra.alerts import repository
from valyra.alerts.domain import CASH_PRESSURE, WARNING, cash_dedup_key, cash_pressure_text
from valyra.alerts.models import Alert
from valyra.core.errors import AppError


def create_cash_pressure(
    session: Session,
    user_id: UUID,
    account_id: UUID,
    today: date,
    *,
    start_balance_cents: int,
    min_balance_cents: int,
    min_balance_date: date,
    days: int,
) -> bool:
    """Grava o alerta do mês se ainda não existe; devolve se criou.

    Não faz commit: roda dentro da transação da importação, e uma falha aqui a desfaz inteira.
    """
    title, message = cash_pressure_text(min_balance_cents, min_balance_date, days)
    return repository.insert_if_absent(
        session,
        {
            "user_id": user_id,
            "kind": CASH_PRESSURE,
            "severity": WARNING,
            "status": "new",
            "title": title,
            "message": message,
            # Dinheiro em centavos inteiros e datas ISO, como no restante da API.
            "evidence": {
                "days": days,
                "today": today.isoformat(),
                "start_balance_cents": start_balance_cents,
                "min_balance_cents": min_balance_cents,
                "min_balance_date": min_balance_date.isoformat(),
            },
            "account_id": account_id,
            "dedup_key": cash_dedup_key(account_id, today),
        },
    )


def list_alerts(
    session: Session, user_id: UUID, limit: int, offset: int
) -> tuple[list[Alert], int]:
    return repository.list_alerts(session, user_id, limit, offset)


def mark_read(session: Session, user_id: UUID, alert_id: UUID) -> Alert:
    """Marca como lido; repetir mantém o read_at da primeira leitura."""
    try:
        alert = repository.get_alert(session, user_id, alert_id)
        if alert is None:
            # Alerta de outro usuário responde igual a inexistente, sem revelar que existe.
            raise AppError("ALERT_NOT_FOUND", "Alerta não encontrado", 404)
        if alert.status != "read":
            alert.status = "read"
            # clock_timestamp marca o instante real; now() repetiria o início da transação.
            alert.read_at = func.clock_timestamp()
            session.flush()
            session.refresh(alert)
        session.commit()
        return alert
    except BaseException:
        session.rollback()
        raise
