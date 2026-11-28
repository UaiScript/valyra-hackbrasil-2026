"""Casos de uso do Alpha: gravar observações coletadas e montar o radar num corte `as_of`."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from valyra.alpha import repository
from valyra.alpha.domain import (
    ALL_SERIES,
    MODEL_CLIMATE_KEY,
    MODEL_STOCK_KEY,
    SGS_SERIES,
    DerivedSignal,
    Series,
    SoyVolatility,
    climate_signal,
    estimate_soy_volatility,
    estimated_publication,
    format_decimal,
    ipca_signal,
    next_revision,
    selic_signal,
    signal_key,
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
    "open-meteo": {
        "name": "Open-Meteo",
        "url": "https://open-meteo.com/",
        "license": "CC BY 4.0; API gratuita para uso não comercial",
    },
}
# Histórico curto basta para o radar e mantém a leitura barata no plano gratuito do banco.
HISTORY_POINTS = 30
MODEL_HISTORY_POINTS = 90


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
class SourceStatus:
    """Fonte com a última coleta visível no corte: a tela mostra se está atualizada."""

    source: Source
    last_ingested_at: datetime | None
    series_count: int


@dataclass(frozen=True)
class Radar:
    as_of: datetime
    indicators: list[IndicatorView]
    signals: list[DerivedSignal]
    last_ingested_at: datetime | None
    sources: list[SourceStatus] = field(default_factory=list)
    soy_volatility: SoyVolatility = field(default_factory=SoyVolatility)
    model_record_ids: list[UUID] = field(default_factory=list)


def get_radar(session: Session, as_of: datetime) -> Radar:
    """Radar com o que era conhecido no corte: nada publicado depois de `as_of` entra."""
    indicators: list[IndicatorView] = []
    signals: list[DerivedSignal] = []
    last: datetime | None = None
    for series in ALL_SERIES:
        rows = repository.list_visible(session, series.key, as_of, HISTORY_POINTS)
        if not rows:
            continue
        history = [signal for signal, _ in reversed(rows)]
        # Coleta posterior ao corte não aparece: o replay mostra só o que já tinha chegado.
        seen = [s.ingested_at for s in history if s.ingested_at <= as_of]
        if seen:
            last = max(seen) if last is None else max(last, *seen)
        indicators.append(
            IndicatorView(
                series=series,
                source=rows[0][1],
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
                ],
            )
        )
        if series is SGS_SERIES[0]:
            derived = selic_signal(series, history)
        elif series is SGS_SERIES[2]:
            derived = ipca_signal(series, history)
        elif series.theme == "clima" and series.unit == "%":
            derived = climate_signal(series, history)
        else:
            derived = None
        if derived is not None:
            signals.append(derived)
    model_rows = {
        key: repository.list_model_revisions(session, key, as_of, MODEL_HISTORY_POINTS)
        for key in (MODEL_STOCK_KEY, MODEL_CLIMATE_KEY)
    }
    signals.sort(key=lambda s: s.observation_date, reverse=True)
    model = estimate_soy_volatility(
        model_rows.get(MODEL_STOCK_KEY, []), model_rows.get(MODEL_CLIMATE_KEY, []), as_of
    )
    return Radar(
        as_of=as_of,
        indicators=indicators,
        signals=signals,
        last_ingested_at=last,
        sources=_source_statuses(indicators, as_of),
        soy_volatility=model,
        model_record_ids=[
            s.id
            for rows in model_rows.values()
            for s in rows
            if s.signal_key in model.evidence_keys
        ],
    )


def _source_statuses(indicators: list[IndicatorView], as_of: datetime) -> list[SourceStatus]:
    grouped: dict[str, list[IndicatorView]] = {}
    for view in indicators:
        grouped.setdefault(view.source.slug, []).append(view)
    statuses = []
    for views in grouped.values():
        seen = [p.ingested_at for v in views for p in v.history if p.ingested_at <= as_of]
        statuses.append(
            SourceStatus(
                source=views[0].source,
                last_ingested_at=max(seen, default=None),
                series_count=len(views),
            )
        )
    return statuses


def format_value(value: Decimal) -> str:
    """Texto decimal de um valor Alpha, para outros módulos (IA) sem importar o domínio."""
    return format_decimal(value)
