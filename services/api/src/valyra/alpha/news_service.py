"""Casos de uso do relatório semanal de notícias (proposta da ADR-0013).

Grava cada notícia uma vez, como sinal `news_event` sem valor numérico, e monta o
relatório da semana até um corte `as_of`. Os temas são recalculados na leitura pela
regra versionada, então trocar a regra não exige reescrever linhas somente inserção.
"""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from valyra.alpha import news_repository, repository
from valyra.alpha.models import Signal, Source
from valyra.alpha.news import (
    BUSINESS_ZONE,
    SOURCES_BY_SLUG,
    FeedItem,
    Theme,
    build_digest,
    news_key,
    publication_instant,
    tickers_for,
    week_start,
)

# Teto de leitura da semana: três fontes publicam algumas dezenas de matérias por semana.
WEEK_LIMIT = 300


def _source(session: Session, slug: str) -> Source:
    source = repository.get_source(session, slug)
    if source is None:
        meta = SOURCES_BY_SLUG[slug]
        source = repository.add_source(
            session, Source(slug=slug, name=meta.name, url=meta.site_url, license=meta.license)
        )
    return source


def record_news(session: Session, item: FeedItem, *, ingested_at: datetime) -> bool:
    """Grava a notícia se a chave é nova; devolve se gravou. Nunca sobrescreve."""
    key = news_key(item.source_slug, item.link)
    if news_repository.exists(session, key):
        return False
    published_at = publication_instant(item, ingested_at)
    repository.add_signal(
        session,
        Signal(
            signal_key=key,
            revision_id=1,
            source_id=_source(session, item.source_slug).id,
            kind=news_repository.NEWS_KIND,
            title=item.title,
            summary=item.excerpt,
            observation_date=published_at.astimezone(BUSINESS_ZONE).date(),
            value=None,
            unit=None,
            payload={
                # Data da fonte guardada à parte: `published_at` pode ter sido limitado à coleta.
                "source_published_at": (
                    item.source_published_at.isoformat() if item.source_published_at else None
                ),
                # Só o endereço da imagem da própria fonte; a Valyra não copia o arquivo.
                "image_url": item.image_url,
                "image_credit": item.image_credit,
            },
            published_at=published_at,
            published_at_estimated=False,
            ingested_at=ingested_at,
            source_url=item.link,
        ),
    )
    return True


def _payload_text(payload: object, key: str) -> str | None:
    value = payload.get(key) if isinstance(payload, dict) else None
    return value if isinstance(value, str) and value else None


@dataclass(frozen=True)
class NewsView:
    signal_id: UUID
    signal_key: str
    revision_id: int
    title: str
    summary: str
    url: str
    observation_date: date
    published_at: datetime
    ingested_at: datetime
    source: Source
    # Ações do radar citadas pelo nome da empresa (regra de nomes de news.TICKER_ALIASES).
    tickers: tuple[str, ...] = ()
    image_url: str | None = None
    image_credit: str | None = None


@dataclass(frozen=True)
class ThemeView:
    theme: Theme
    items: list[NewsView]


@dataclass(frozen=True)
class WeeklyReport:
    as_of: datetime
    week_start: datetime
    themes: list[ThemeView]
    total: int
    unmatched: int
    sources: list[Source]
    last_ingested_at: datetime | None


def get_weekly_report(session: Session, as_of: datetime, *, per_theme: int = 4) -> WeeklyReport:
    """Notícias publicadas nos 7 dias até o corte, agrupadas pelos temas do orçamento."""
    rows = news_repository.list_published_between(session, week_start(as_of), as_of, WEEK_LIMIT)
    views = [
        NewsView(
            signal_id=signal.id,
            signal_key=signal.signal_key,
            revision_id=signal.revision_id,
            title=signal.title,
            summary=signal.summary,
            url=signal.source_url,
            observation_date=signal.observation_date,
            published_at=signal.published_at,
            ingested_at=signal.ingested_at,
            source=source,
            tickers=tickers_for(signal.title, signal.summary),
            image_url=_payload_text(signal.payload, "image_url"),
            image_credit=_payload_text(signal.payload, "image_credit"),
        )
        for signal, source in rows
    ]
    digest = build_digest(views, as_of, per_theme=per_theme)
    sources = {view.source.slug: view.source for view in views}
    seen = [view.ingested_at for view in views]
    return WeeklyReport(
        as_of=as_of,
        week_start=digest.week_start,
        themes=[ThemeView(theme=group.theme, items=group.items) for group in digest.groups],
        total=digest.total,
        unmatched=digest.unmatched,
        sources=sorted(sources.values(), key=lambda source: source.name),
        last_ingested_at=max(seen) if seen else None,
    )
