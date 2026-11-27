"""Regras puras do Alpha (ADR-0012): catálogo, leitura do SGS, corte temporal e sinais.

Nada aqui lê banco, rede ou relógio; instantes chegam como parâmetro.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Literal, Protocol
from zoneinfo import ZoneInfo

BUSINESS_ZONE = ZoneInfo("America/Sao_Paulo")
Periodicity = Literal["daily", "monthly"]


@dataclass(frozen=True)
class Series:
    """Série acompanhada no radar; `key` é o prefixo lógico dos `signal_key`."""

    key: str
    source_slug: str
    title: str
    unit: str
    unit_label: str
    periodicity: Periodicity
    metric_key: str
    kind: str
    sgs_code: int | None = None
    ticker: str | None = None


SGS_SERIES: tuple[Series, ...] = (
    Series(
        key="bcb:sgs:432",
        source_slug="bcb-sgs",
        title="Selic meta",
        unit="%",
        unit_label="% ao ano",
        periodicity="daily",
        metric_key="alpha.bcb.selic_meta",
        kind="macro_indicator",
        sgs_code=432,
    ),
    Series(
        key="bcb:sgs:12",
        source_slug="bcb-sgs",
        title="CDI diário",
        unit="%",
        unit_label="% ao dia",
        periodicity="daily",
        metric_key="alpha.bcb.cdi_daily",
        kind="macro_indicator",
        sgs_code=12,
    ),
    Series(
        key="bcb:sgs:433",
        source_slug="bcb-sgs",
        title="IPCA do mês",
        unit="%",
        unit_label="% no mês",
        periodicity="monthly",
        metric_key="alpha.bcb.ipca_month",
        kind="macro_indicator",
        sgs_code=433,
    ),
)
# Tickers que a brapi libera sem token; com token o plano gratuito aceita outros.
BRAPI_TICKERS = ("PETR4", "VALE3", "ITUB4", "MGLU3")
STOCK_SERIES: tuple[Series, ...] = tuple(
    Series(
        key=f"brapi:{ticker}:change_pct",
        source_slug="brapi",
        title=f"{ticker}: variação do dia",
        unit="%",
        unit_label="% no dia",
        periodicity="daily",
        metric_key=f"alpha.brapi.{ticker.lower()}.change_pct",
        kind="price_move",
        ticker=ticker,
    )
    for ticker in BRAPI_TICKERS
)
ALL_SERIES = SGS_SERIES + STOCK_SERIES


def signal_key(series: Series, observation_date: date) -> str:
    return f"{series.key}:{observation_date.isoformat()}"


class SgsFormatError(ValueError):
    """Resposta do SGS fora do formato `[{"data": "dd/mm/aaaa", "valor": "x"}]`."""


_SGS_DATE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


def parse_decimal(raw: object) -> Decimal:
    # Aceita vírgula ou ponto: relatos divergem sobre o separador devolvido pelo SGS.
    if isinstance(raw, bool) or not isinstance(raw, (str, int)):
        raise SgsFormatError("valor numérico ausente")
    text = str(raw).strip().replace(",", ".")
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise SgsFormatError("valor numérico inválido") from None
    if not value.is_finite():
        raise SgsFormatError("valor numérico inválido")
    return value


def parse_sgs(payload: object) -> list[tuple[date, Decimal]]:
    if not isinstance(payload, list):
        raise SgsFormatError("resposta do SGS não é uma lista")
    rows: dict[date, Decimal] = {}
    for item in payload:
        if not isinstance(item, dict):
            raise SgsFormatError("item do SGS não é objeto")
        match = _SGS_DATE.fullmatch(str(item.get("data", "")))
        if match is None:
            raise SgsFormatError("data do SGS fora de dd/mm/aaaa")
        day, month, year = (int(part) for part in match.groups())
        rows[date(year, month, day)] = parse_decimal(item.get("valor"))
    return sorted(rows.items())


def estimated_publication(series: Series, observation_date: date) -> datetime:
    """Publicação reconstituída para carga histórica; erra para depois, nunca para antes.

    Diárias: dia seguinte ao meio-dia. Mensais (IPCA): dia 12 do mês seguinte ao meio-dia,
    depois da janela usual de divulgação do IBGE. Sempre marcada como estimada.
    """
    if series.periodicity == "monthly":
        year = observation_date.year + (observation_date.month == 12)
        month = 1 if observation_date.month == 12 else observation_date.month + 1
        day = date(year, month, 12)
    else:
        day = observation_date + timedelta(days=1)
    return datetime.combine(day, time(12), BUSINESS_ZONE).astimezone(UTC)


class Revision(Protocol):
    signal_key: str
    revision_id: int
    observation_date: date
    value: Decimal | None
    published_at: datetime


def visible_at[R: Revision](rows: Iterable[R], as_of: datetime) -> dict[str, R]:
    """Para cada `signal_key`, a revisão mais recente publicada até o corte (modelagem 5.2)."""
    chosen: dict[str, R] = {}
    for row in rows:
        if row.published_at > as_of:
            continue
        current = chosen.get(row.signal_key)
        if current is None or (row.published_at, row.revision_id) > (
            current.published_at,
            current.revision_id,
        ):
            chosen[row.signal_key] = row
    return chosen


def next_revision(latest: Revision | None, value: Decimal) -> int | None:
    """Número da nova revisão, ou None quando o valor coletado já é o vigente."""
    if latest is None:
        return 1
    if latest.value is not None and latest.value == value:
        return None
    return latest.revision_id + 1


def format_decimal(value: Decimal) -> str:
    # Texto sem notação científica nem zeros à direita; não passa por float.
    text = format(value.normalize(), "f")
    return "0" if text in {"-0", ""} else text


def display(value: Decimal, unit_label: str) -> str:
    return f"{format_decimal(value).replace('.', ',')} {unit_label}"


@dataclass(frozen=True)
class DerivedSignal:
    """Sinal por regra determinística; `evidence_keys` aponta as revisões usadas."""

    key: str
    title: str
    summary: str
    observation_date: date
    published_at: datetime
    evidence_keys: tuple[str, ...]
    rule: str


_MONTHS = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)  # fmt: skip


def _month_name(day: date) -> str:
    return f"{_MONTHS[day.month - 1]} de {day.year}"


def selic_signal(series: Series, history: Sequence[Revision]) -> DerivedSignal | None:
    """Última mudança da Selic meta dentro do histórico visível, ou estabilidade."""
    points = [
        row for row in sorted(history, key=lambda r: r.observation_date) if row.value is not None
    ]
    if not points:
        return None
    last = points[-1]
    change = next(
        (
            (before, after)
            for before, after in zip(reversed(points[:-1]), reversed(points[1:]), strict=True)
            if before.value != after.value
        ),
        None,
    )
    assert last.value is not None
    if change is None:
        first = points[0]
        return DerivedSignal(
            key=f"{series.key}:estavel",
            title=f"Selic meta estável em {display(last.value, series.unit_label)}",
            summary=(
                "Sem mudança da meta no histórico coletado, de "
                f"{first.observation_date.isoformat()} a {last.observation_date.isoformat()}."
            ),
            observation_date=last.observation_date,
            published_at=max(row.published_at for row in (first, last)),
            evidence_keys=(first.signal_key, last.signal_key),
            rule="selic_meta_stable_v1",
        )
    before, after = change
    assert before.value is not None and after.value is not None
    verb = "subiu" if after.value > before.value else "caiu"
    return DerivedSignal(
        key=f"{series.key}:mudanca:{after.observation_date.isoformat()}",
        title=(
            f"Selic meta {verb} de {display(before.value, series.unit_label)} "
            f"para {display(after.value, series.unit_label)}"
        ),
        summary=f"Mudança registrada na observação de {after.observation_date.isoformat()}.",
        observation_date=after.observation_date,
        published_at=max(before.published_at, after.published_at),
        evidence_keys=(before.signal_key, after.signal_key),
        rule="selic_meta_change_v1",
    )


def ipca_signal(series: Series, history: Sequence[Revision]) -> DerivedSignal | None:
    """IPCA do último mês visível comparado ao mês anterior."""
    points = [
        row for row in sorted(history, key=lambda r: r.observation_date) if row.value is not None
    ]
    if len(points) < 2:
        return None
    previous, last = points[-2], points[-1]
    assert previous.value is not None and last.value is not None
    if last.value > previous.value:
        word = "acima do"
    elif last.value < previous.value:
        word = "abaixo do"
    else:
        word = "igual ao"
    return DerivedSignal(
        key=f"{series.key}:comparacao:{last.observation_date.isoformat()}",
        title=f"IPCA de {_month_name(last.observation_date)} {word} mês anterior",
        summary=(
            f"{display(last.value, series.unit_label)} contra "
            f"{display(previous.value, series.unit_label)} "
            f"em {_month_name(previous.observation_date)}."
        ),
        observation_date=last.observation_date,
        published_at=max(previous.published_at, last.published_at),
        evidence_keys=(previous.signal_key, last.signal_key),
        rule="ipca_month_compare_v1",
    )
