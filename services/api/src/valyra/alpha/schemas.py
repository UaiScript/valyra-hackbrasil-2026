"""Saída HTTP do radar Alpha; valores como texto decimal para não passar por float."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class SourceOut(BaseModel):
    slug: str
    name: str
    url: str
    license: str


class PointOut(BaseModel):
    signal_key: str
    revision_id: int
    observation_date: date
    # Decimal em texto com ponto, por exemplo "15" ou "0.055131".
    value: str
    published_at: datetime
    # true: publicação reconstituída na carga histórica ("reconstituição ilustrativa").
    published_at_estimated: bool
    ingested_at: datetime
    source_url: str


class HistoryPointOut(BaseModel):
    observation_date: date
    value: str


class RegionOut(BaseModel):
    slug: str
    name: str
    # Produção típica da região, para dar contexto ao dado de clima.
    production: str


class IndicatorOut(BaseModel):
    key: str
    title: str
    unit: str
    unit_label: str
    kind: str
    theme: Literal["juros", "inflacao", "acoes", "clima"]
    periodicity: Literal["daily", "monthly"]
    region: RegionOut | None
    source: SourceOut
    latest: PointOut
    previous: PointOut | None
    history: list[HistoryPointOut]


class DerivedSignalOut(BaseModel):
    key: str
    title: str
    summary: str
    observation_date: date
    published_at: datetime
    # Regra determinística e versionada que gerou o sinal; não é previsão nem causa.
    rule: str
    theme: Literal["juros", "inflacao", "acoes", "clima"]
    # signal_key das observações que fundamentam o sinal (dados observados).
    evidence_keys: list[str]
    limitations: list[str]


class SourceStatusOut(BaseModel):
    source: SourceOut
    last_ingested_at: datetime | None
    series_count: int


class SoyVolatilityOut(BaseModel):
    status: Literal["ready", "insufficient_data"] = "insufficient_data"
    reason: str | None = None
    rule: str = "soy_volatility_ridge_v1"
    asset: str = "SLCE3"
    region: str = "sorriso-mt"
    horizon_days: int = 5
    stock_points: int = 0
    climate_points: int = 0
    train_windows: int = 0
    eval_windows: int = 0
    first_observation_date: date | None = None
    last_observation_date: date | None = None
    m0_forecast_pct: str | None = None
    m1_forecast_pct: str | None = None
    intercept_pct: str | None = None
    market_persistence_pct: str | None = None
    daily_shock_pct: str | None = None
    climate_component_pct: str | None = None
    truncation_adjustment_pct: str | None = None
    recent_rv_5d_pct: str | None = None
    sorriso_rain_anomaly_pct: str | None = None
    mae_m0_pp: str | None = None
    mae_m1_pp: str | None = None
    regime: Literal["normal", "elevada"] | None = None
    weights: dict[str, str] = Field(default_factory=dict)
    evidence_keys: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class RadarOut(BaseModel):
    """Radar econômico no corte `as_of`: só revisões publicadas até esse instante."""

    as_of: datetime
    last_ingested_at: datetime | None
    indicators: list[IndicatorOut]
    signals: list[DerivedSignalOut]
    sources: list[SourceStatusOut]

    soy_volatility: SoyVolatilityOut
