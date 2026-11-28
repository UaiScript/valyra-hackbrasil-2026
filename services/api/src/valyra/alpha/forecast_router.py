"""Rota das previsões por perfil (ADR-0016): só leitura, calculada em código."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from valyra.alpha import forecast_service
from valyra.alpha.domain import format_decimal
from valyra.alpha.forecast import METHOD_VERSION, PATHS, VIEW_RULE, Band
from valyra.alpha.forecast_schemas import (
    BacktestOut,
    BandOut,
    ChanceOut,
    ChartPointOut,
    FanPointOut,
    ForecastOut,
    ForecastsOut,
    InputSeriesOut,
    InputSourceOut,
    ProfileId,
    TickerRangeOut,
    ViewOut,
)
from valyra.core.db import get_session
from valyra.core.errors import error_responses

router = APIRouter(prefix="/api/v1/alpha", tags=["alpha"], responses=error_responses(422))

SessionDep = Annotated[Session, Depends(get_session)]

NOTES = [
    "Calculado em código no servidor, sem IA: a Valyra AI só explica o resultado pronto.",
    "A chance é a fração de 1.000 cenários simulados em que o evento acontece.",
    "A faixa de 80% contém o valor em 8 de cada 10 cenários; o teste com o passado mostra "
    "quantas vezes ela teria acertado.",
    "Leitura estatística, não recomendação de investimento.",
]


def decimal_text(value: float, digits: int = 2) -> str:
    """Float do modelo em texto decimal fixo (indicadores, nunca dinheiro)."""
    return format_decimal(Decimal(f"{value:.{digits}f}"))


def _band(band: Band, digits: int = 2) -> BandOut:
    return BandOut(
        p2_5=decimal_text(band.p2_5, digits),
        p10=decimal_text(band.p10, digits),
        p50=decimal_text(band.p50, digits),
        p90=decimal_text(band.p90, digits),
        p97_5=decimal_text(band.p97_5, digits),
    )


def forecast_out(item, inputs) -> ForecastOut:
    origins = {i.origin for i in inputs}
    origin = origins.pop() if len(origins) == 1 else "misto"
    limitations = list(item.spec.limitations)
    if origin != "coleta":
        limitations.insert(
            0,
            "Parte ou todo o histórico é de reserva sintética: a coleta ainda não tem pontos "
            "suficientes desta série. Os números ilustram o método, não o mercado real.",
        )
    if any(i.published_at_estimated for i in inputs):
        limitations.append(
            "Parte do histórico veio de carga retroativa, com data de publicação estimada."
        )
    bt = item.backtest
    return ForecastOut(
        key=item.spec.kind,
        title=item.spec.title,
        question=item.spec.question,
        method=item.spec.method,
        method_label=item.spec.method_label,
        method_version=METHOD_VERSION,
        paths=PATHS,
        horizon=item.spec.horizon,
        horizon_label=item.spec.horizon_label,
        unit=item.spec.unit,
        unit_label=item.spec.unit_label,
        current=decimal_text(item.current),
        current_label=item.current_label,
        headline=_band(item.headline),
        chance=(
            ChanceOut(pct=decimal_text(item.chance * 100, 0), event_label=item.spec.event.label)
            if item.chance is not None and item.spec.event is not None
            else None
        ),
        chart_unit=item.chart_unit,
        history=[ChartPointOut(day=p.day, value=decimal_text(p.value, 3)) for p in item.history],
        fan=[FanPointOut(day=p.day, band=_band(p.band, 3)) for p in item.fan],
        backtest=(
            BacktestOut(
                horizon_label=bt.horizon_label,
                trials=bt.trials,
                hits=bt.hits,
                model_mae=decimal_text(bt.model_mae, 3) if bt.model_mae is not None else None,
                naive_mae=decimal_text(bt.naive_mae, 3) if bt.naive_mae is not None else None,
            )
            if bt is not None
            else None
        ),
        view=ViewOut(
            stance=item.view.stance,
            headline=item.view.headline,
            text=item.view.text,
            rule=VIEW_RULE,
        ),  # fmt: skip
        data_origin=origin,
        inputs=[
            InputSeriesOut(
                key=i.key,
                title=i.title,
                origin=i.origin,
                source=InputSourceOut(
                    slug=i.source_slug, name=i.source_name, url=i.source_url, license=i.license
                ),
                observations=i.observations,
                first_day=i.first_day,
                last_day=i.last_day,
                last_published_at=i.last_published_at,
                last_ingested_at=i.last_ingested_at,
                published_at_estimated=i.published_at_estimated,
            )
            for i in inputs
        ],
        tickers=[
            TickerRangeOut(
                ticker=t.ticker,
                band=_band(t.band),
                chance_up_pct=decimal_text(t.chance_up * 100, 0),
                daily_vol_pct=decimal_text(t.daily_vol),
            )
            for t in item.tickers
        ],
        params={k: decimal_text(v, 3) for k, v in item.params.items()},
        limitations=limitations,
    )


@router.get("/forecasts", name="alpha_get_forecasts", response_model=ForecastsOut)
def get_forecasts(
    session: SessionDep,
    profile: Annotated[
        ProfileId | None,
        Query(description="Perfil da demo; ausente usa o conjunto padrão de previsões"),
    ] = None,
    as_of: Annotated[
        AwareDatetime | None,
        Query(description="Corte do replay, com fuso; ausente usa o instante atual"),
    ] = None,
) -> ForecastsOut:
    now = datetime.now(UTC)
    cut = now if as_of is None else min(as_of.astimezone(UTC), now)
    result = forecast_service.get_forecasts(session, profile, cut, now=now)
    return ForecastsOut(
        profile=profile,
        as_of=result.as_of,
        computed_at=result.computed_at,
        items=[forecast_out(item, inputs) for item, inputs in result.items],
        notes=NOTES,
    )
