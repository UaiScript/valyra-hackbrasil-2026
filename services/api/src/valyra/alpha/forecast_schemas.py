"""Saída HTTP das previsões (ADR-0016); números como texto decimal, como no radar."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

ProfileId = Literal["orcamento-apertado", "comecando-a-investir", "investidor"]


class BandOut(BaseModel):
    """Quantis dos cenários simulados: 80% entre p10 e p90, 95% entre p2_5 e p97_5."""

    p2_5: str
    p10: str
    p50: str
    p90: str
    p97_5: str


class ChartPointOut(BaseModel):
    day: date
    value: str


class FanPointOut(BaseModel):
    day: date
    band: BandOut


class ChanceOut(BaseModel):
    # Fração dos cenários em que o evento aconteceu, em % inteiro (ex.: "62").
    pct: str
    event_label: str


class BacktestOut(BaseModel):
    """Previsões refeitas em datas passadas: a faixa de 80% acertou `hits` de `trials`."""

    horizon_label: str
    trials: int
    hits: int
    # Erro médio absoluto do cenário central e de repetir o último valor; nulo no passeio
    # aleatório, em que o cenário central é o próprio último valor.
    model_mae: str | None
    naive_mae: str | None


class ViewOut(BaseModel):
    """Leitura da Valyra por regra fixa sobre os números acima; não é recomendação."""

    stance: Literal["atencao", "neutra", "favoravel"]
    headline: str
    text: str
    rule: str


class InputSourceOut(BaseModel):
    slug: str
    name: str
    url: str
    license: str


class InputSeriesOut(BaseModel):
    key: str
    title: str
    # coleta = dado público coletado pela Valyra; reserva = série sintética de demonstração.
    origin: Literal["coleta", "reserva"]
    source: InputSourceOut
    observations: int
    first_day: date
    last_day: date
    last_published_at: datetime | None
    last_ingested_at: datetime | None
    published_at_estimated: bool


class TickerRangeOut(BaseModel):
    ticker: str
    band: BandOut
    chance_up_pct: str
    daily_vol_pct: str


class ForecastOut(BaseModel):
    key: str
    title: str
    question: str
    method: Literal["holt_damped", "random_walk"]
    method_label: str
    method_version: str
    paths: int
    horizon: int
    horizon_label: str
    unit: str
    unit_label: str
    current: str
    current_label: str
    headline: BandOut
    chance: ChanceOut | None
    chart_unit: str
    history: list[ChartPointOut]
    fan: list[FanPointOut]
    backtest: BacktestOut | None
    view: ViewOut
    data_origin: Literal["coleta", "reserva", "misto"]
    inputs: list[InputSeriesOut]
    tickers: list[TickerRangeOut] = Field(default_factory=list)
    params: dict[str, str]
    limitations: list[str]


class ForecastsOut(BaseModel):
    """Previsões do perfil no corte `as_of`, calculadas em código, sem LLM."""

    profile: ProfileId | None
    as_of: datetime
    computed_at: datetime
    items: list[ForecastOut]
    notes: list[str]
