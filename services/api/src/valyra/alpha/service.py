"""Casos de uso do Alpha: gravar observações coletadas e montar o radar num corte `as_of`."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from valyra.alpha import repository
from valyra.alpha.domain import (
    ALL_SERIES,
    SGS_SERIES,
    DerivedSignal,
    Series,
    estimated_publication,
    ipca_signal,
    next_revision,
    selic_signal,
    signal_key,
    visible_at,
)
from valyra.alpha.models import Signal, Source

SOURCES = {
    "bcb-sgs": {
        "name": "Banco Central do Brasil — SGS",
        "url": "https://api.bcb.gov.br/dados/serie/",
        "license": "Dados abertos do Banco Central; citar a fonte",
    },
    "brapi": {
        "name": "brapi.dev",
        "url": "https://brapi.dev/",
        "license": "Plano gratuito da brapi.dev; cotação com atraso",
    },
}
# Histórico curto basta para o radar e mantém a leitura barata no plano gratuito do banco.
HISTORY_POINTS = 30


def _source(session: Session, slug: str) -> Source:
    source = repository.get_source(session, slug)
    if source is None:
        source = repository.add_source(session, Source(slug=slug, **SOURCES[slug]))
    return source


def record_observation(
    session: Session,
    series: Series,
    observation_date: date,
    value: Decimal,
    *,
    ingested_at: datetime,
    source_url: str,
    backfill: bool = False,
) -> bool:
    """Grava a observação como revisão nova se o valor mudou; devolve se gravou.

    Coleta corrente usa a própria coleta como publicação (conservador). Carga histórica
    usa a publicação reconstituída, marcada como estimada, e só vale para chave nova.
    """
    key = signal_key(series, observation_date)
    latest = repository.latest_revision(session, key)
    revision = next_revision(latest, value)
    if revision is None:
        return False
    estimated = backfill and latest is None
    published_at = (
        min(estimated_publication(series, observation_date), ingested_at)
        if estimated
        else ingested_at
    )
    repository.add_signal(
        session,
        Signal(
            signal_key=key,
            revision_id=revision,
            source_id=_source(session, series.source_slug).id,
            kind=series.kind,
            title=series.title,
            summary=f"{series.title} ({series.unit_label}) observado em {observation_date}.",
            observation_date=observation_date,
            value=value,
            unit=series.unit,
            payload={"unit_label": series.unit_label},
            published_at=published_at,
            published_at_estimated=estimated,
            ingested_at=ingested_at,
            source_url=source_url,
        ),
    )
    return True


@dataclass(frozen=True)
class Point:
    signal_id: UUID
    signal_key: str
    revision_id: int
    observation_date: date
    value: Decimal
    published_at: datetime
    published_at_estimated: bool
    ingested_at: datetime
    source_url: str


@dataclass(frozen=True)
class IndicatorView:
    series: Series
    source: Source
    history: list[Point]

    @property
    def latest(self) -> Point | None:
        return self.history[-1] if self.history else None

    @property
    def previous(self) -> Point | None:
        return self.history[-2] if len(self.history) > 1 else None


@dataclass(frozen=True)
class Radar:
    as_of: datetime
    indicators: list[IndicatorView]
    signals: list[DerivedSignal]
    last_ingested_at: datetime | None


def get_radar(session: Session, as_of: datetime) -> Radar:
    """Radar com o que era conhecido no corte: nada publicado depois de `as_of` entra."""
    rows = repository.list_revisions(session, [s.key for s in ALL_SERIES], as_of)
    sources = {signal.signal_key: source for signal, source in rows}
    visible = visible_at((signal for signal, _ in rows), as_of)
    by_series: dict[str, list[Signal]] = defaultdict(list)
    for key, signal in visible.items():
        by_series[key.rsplit(":", 1)[0]].append(signal)
    indicators: list[IndicatorView] = []
    signals: list[DerivedSignal] = []
    for series in ALL_SERIES:
        history = sorted(by_series.get(series.key, []), key=lambda s: s.observation_date)
        history = [s for s in history if s.value is not None][-HISTORY_POINTS:]
        if not history:
            continue
        indicators.append(
            IndicatorView(
                series=series,
                source=sources[history[-1].signal_key],
                history=[
                    Point(
                        signal_id=s.id,
                        signal_key=s.signal_key,
                        revision_id=s.revision_id,
                        observation_date=s.observation_date,
                        value=s.value,
                        published_at=s.published_at,
                        published_at_estimated=s.published_at_estimated,
                        ingested_at=s.ingested_at,
                        source_url=s.source_url,
                    )
                    for s in history
                    if s.value is not None
                ],
            )
        )
        if series is SGS_SERIES[0]:
            derived = selic_signal(series, history)
        elif series is SGS_SERIES[2]:
            derived = ipca_signal(series, history)
        else:
            derived = None
        if derived is not None:
            signals.append(derived)
    signals.sort(key=lambda s: s.observation_date, reverse=True)
    # Coleta posterior ao corte não aparece: o replay mostra só o que já tinha chegado.
    last = max((s.ingested_at for s in visible.values() if s.ingested_at <= as_of), default=None)
    return Radar(as_of=as_of, indicators=indicators, signals=signals, last_ingested_at=last)
