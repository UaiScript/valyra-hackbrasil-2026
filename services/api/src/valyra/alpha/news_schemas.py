"""Saída HTTP do relatório semanal de notícias do Alpha (proposta da ADR-0013)."""

from datetime import date, datetime

from pydantic import BaseModel

from valyra.alpha.schemas import SourceOut


class NewsItemOut(BaseModel):
    signal_key: str
    title: str
    # Trecho curto da própria fonte, sem HTML; nunca a matéria inteira.
    summary: str
    url: str
    source: SourceOut
    observation_date: date
    # Publicação pela fonte, limitada ao instante da coleta (nunca depois dela).
    published_at: datetime
    ingested_at: datetime
    # Tickers do radar Alpha citados pelo nome da empresa; liga a manchete à cotação.
    tickers: list[str]


class NewsThemeOut(BaseModel):
    key: str
    title: str
    # Frase fixa da regra: o que o tema pode mexer no orçamento, sem número nem previsão.
    why: str
    # Slugs de categoria Finance ligados ao tema; vazio quando o tema não tem categoria própria.
    category_slugs: list[str]
    # Tema do radar Alpha com os dados observados para ler junto (juros, inflacao, acoes, clima).
    radar_theme: str | None
    items: list[NewsItemOut]


class WeeklyNewsOut(BaseModel):
    """Notícias publicadas nos 7 dias até `as_of`, agrupadas por tema pela regra `rule`."""

    as_of: datetime
    week_start: datetime
    rule: str
    total_items: int
    # Notícias da semana que não tocam nenhum tema do orçamento; ficam fora do relatório.
    unmatched_items: int
    themes: list[NewsThemeOut]
    sources: list[SourceOut]
    last_ingested_at: datetime | None
