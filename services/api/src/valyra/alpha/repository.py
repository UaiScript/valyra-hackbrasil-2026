"""Leitura e gravação de fontes e sinais; nunca faz commit (o service controla)."""

from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

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


def list_revisions(
    session: Session, prefixes: list[str], as_of: datetime
) -> list[tuple[Signal, Source]]:
    """Revisões publicadas até o corte das séries pedidas; a escolha final é do domínio."""
    if not prefixes:
        return []
    rows = session.execute(
        select(Signal, Source)
        .join(Source, Source.id == Signal.source_id)
        .where(
            Signal.published_at <= as_of,
            or_(*(Signal.signal_key.startswith(f"{prefix}:") for prefix in prefixes)),
        )
        .order_by(Signal.signal_key, Signal.revision_id)
    )
    return [(row[0], row[1]) for row in rows]
