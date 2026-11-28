"""Leitura e gravação de fontes e sinais; nunca faz commit (o service controla)."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from valyra.alpha.models import Signal, Source


def get_source(session: Session, slug: str) -> Source | None:
    return session.scalar(select(Source).where(Source.slug == slug))


def add_source(session: Session, source: Source) -> Source:
    session.add(source)
    session.flush()
    return source


def latest_revision(session: Session, key: str) -> Signal | None:
    return session.scalar(
        select(Signal).where(Signal.signal_key == key).order_by(Signal.revision_id.desc()).limit(1)
    )


def add_signal(session: Session, signal: Signal) -> None:
    session.add(signal)
    session.flush()


def _like_prefix(prefix: str) -> str:
    # "_" e "%" são curingas no LIKE ("change_pct"); escapados, o prefixo é literal.
    escaped = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"{escaped}:%"


def list_visible(
    session: Session, prefix: str, as_of: datetime, limit: int
) -> list[tuple[Signal, Source]]:
    """Últimas `limit` observações de uma série, cada uma na revisão visível no corte.

    É a regra de `domain.visible_at` (modelagem 5.2) feita no banco com DISTINCT ON:
    revisões intradiárias e anos de histórico não chegam ao Python.
    """
    visible = (
        select(Signal)
        .where(
            Signal.published_at <= as_of,
            Signal.signal_key.like(_like_prefix(prefix), escape="\\"),
        )
        .distinct(Signal.signal_key)
        .order_by(Signal.signal_key, Signal.published_at.desc(), Signal.revision_id.desc())
        .subquery()
    )
    row = aliased(Signal, visible)
    rows = session.execute(
        select(row, Source)
        .join(Source, Source.id == row.source_id)
        .where(row.value.is_not(None))
        .order_by(row.observation_date.desc())
        .limit(limit)
    )
    return [(signal, source) for signal, source in rows]


def list_model_revisions(
    session: Session, prefix: str, as_of: datetime, limit: int
) -> list[Signal]:
    """Revisões dos últimos pontos: correções tardias não reescrevem features passadas."""
    keys = [row.signal_key for row, _ in list_visible(session, prefix, as_of, limit)]
    if not keys:
        return []
    return list(
        session.scalars(
            select(Signal)
            .where(Signal.signal_key.in_(keys), Signal.published_at <= as_of)
            .order_by(Signal.observation_date, Signal.published_at, Signal.revision_id)
        )
    )
