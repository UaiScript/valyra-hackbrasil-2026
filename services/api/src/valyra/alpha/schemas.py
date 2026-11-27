"""Saída HTTP do radar Alpha; valores como texto decimal para não passar por float."""

from datetime import date, datetime

from pydantic import BaseModel


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


class IndicatorOut(BaseModel):
    key: str
    title: str
    unit: str
    unit_label: str
    kind: str
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
    evidence_keys: list[str]


class RadarOut(BaseModel):
    """Radar econômico no corte `as_of`: só revisões publicadas até esse instante."""

    as_of: datetime
    last_ingested_at: datetime | None
    indicators: list[IndicatorOut]
    signals: list[DerivedSignalOut]
