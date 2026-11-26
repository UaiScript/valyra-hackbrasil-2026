"""I/O dos alertas; nunca faz commit, quem controla a transação é o service chamador."""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from valyra.alerts.models import Alert


def insert_if_absent(session: Session, values: dict[str, Any]) -> bool:
    """Insere o alerta, ou nada se (user_id, dedup_key) já existe; devolve se criou."""
    statement = (
        insert(Alert)
        .values(**values)
        # ON CONFLICT evita a corrida entre ler e inserir; o índice único é a garantia.
        .on_conflict_do_nothing(index_elements=["user_id", "dedup_key"])
        .returning(Alert.id)
    )
    return session.execute(statement).scalar_one_or_none() is not None


def list_alerts(
    session: Session, user_id: UUID, limit: int, offset: int
) -> tuple[list[Alert], int]:
    where = Alert.user_id == user_id
    total = session.execute(select(func.count()).select_from(Alert).where(where)).scalar_one()
    items = session.scalars(
        select(Alert)
        .where(where)
        .order_by(Alert.created_at.desc(), Alert.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return list(items), total


def get_alert(session: Session, user_id: UUID, alert_id: UUID) -> Alert | None:
    return session.scalars(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == user_id)
    ).one_or_none()
