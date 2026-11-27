"""Leitura e gravação das notícias (`signals` com kind `news_event`); nunca faz commit."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from valyra.alpha.models import Signal, Source

NEWS_KIND = "news_event"


def exists(session: Session, key: str) -> bool:
    return session.scalar(select(Signal.id).where(Signal.signal_key == key).limit(1)) is not None


def list_published_between(
    session: Session, start: datetime, as_of: datetime, limit: int
) -> list[tuple[Signal, Source]]:
    """Notícias publicadas na janela e já coletadas no corte, da mais recente para a mais antiga.

    A janela usa `published_at` (data da fonte); o corte exige também `ingested_at`: uma
    matéria publicada antes do corte mas coletada depois ainda não era conhecida pela Valyra.
    Notícia não tem revisão de valor (é gravada uma vez por chave), então não precisa do
    DISTINCT ON do radar.
    """
    rows = session.execute(
        select(Signal, Source)
        .join(Source, Source.id == Signal.source_id)
        .where(
            Signal.kind == NEWS_KIND,
            Signal.published_at >= start,
            Signal.published_at <= as_of,
            Signal.ingested_at <= as_of,
        )
        .order_by(Signal.published_at.desc(), Signal.signal_key)
        .limit(limit)
    )
    return [(signal, source) for signal, source in rows]
