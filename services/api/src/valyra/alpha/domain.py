"""Regras puras do Alpha (ADR-0012): catálogo, leitura do SGS, corte temporal e sinais.

Nada aqui lê banco, rede ou relógio; instantes chegam como parâmetro.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, localcontext
from typing import Literal, Protocol
from zoneinfo import ZoneInfo

BUSINESS_ZONE = ZoneInfo("America/Sao_Paulo")
Periodicity = Literal["daily", "monthly"]
# Temas da tela e dos filtros; um indicador pertence a um só tema.
Theme = Literal["juros", "inflacao", "acoes", "clima"]


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
    theme: Theme
    sgs_code: int | None = None
    ticker: str | None = None
    region: Region | None = None
    requires_token: bool = False


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
        theme="juros",
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
        theme="juros",
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
        theme="inflacao",
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
        theme="acoes",
        ticker=ticker,
        requires_token=ticker == "SLCE3",
    )
    for ticker in (*BRAPI_TICKERS, "SLCE3")
)


@dataclass(frozen=True)
class Region:
    """Região produtora acompanhada pelo clima (Open-Meteo, por coordenada)."""

    slug: str
    name: str
    production: str
    latitude: Decimal
    longitude: Decimal


# Três polos de alimentos com perfis diferentes: grãos no Centro-Oeste e hortaliças perto de SP.
_D = Decimal
REGIONS: tuple[Region, ...] = (
    Region("sorriso-mt", "Sorriso (MT)", "soja e milho", _D("-12.545"), _D("-55.711")),
    Region("rio-verde-go", "Rio Verde (GO)", "grãos e carnes", _D("-17.797"), _D("-50.919")),
    Region("mogi-sp", "Mogi das Cruzes (SP)", "hortaliças", _D("-23.522"), _D("-46.188")),
)
RAIN_WINDOW_DAYS = 30
NORMAL_YEARS = 10
# Com menos anos completos, a "média" fica frágil demais para virar comparação.
MIN_NORMAL_YEARS = 7


def _rain_series(region: Region) -> tuple[Series, Series]:
    base = f"openmeteo:{region.slug}"
    return (
        Series(
            key=f"{base}:rain_30d",
            source_slug="open-meteo",
            title=f"Chuva em 30 dias · {region.name}",
            unit="mm",
            unit_label="mm em 30 dias",
            periodicity="daily",
            metric_key=f"alpha.openmeteo.{region.slug}.rain_30d",
            kind="climate_anomaly",
            theme="clima",
            region=region,
        ),
        Series(
            key=f"{base}:rain_30d_anomaly",
            source_slug="open-meteo",
            title=f"Chuva contra a média · {region.name}",
            unit="%",
            unit_label=f"% vs. média de {NORMAL_YEARS} anos",
            periodicity="daily",
            metric_key=f"alpha.openmeteo.{region.slug}.rain_30d_anomaly",
            kind="climate_anomaly",
            theme="clima",
            region=region,
        ),
    )


CLIMATE_SERIES: tuple[Series, ...] = tuple(s for r in REGIONS for s in _rain_series(r))
ALL_SERIES = SGS_SERIES + STOCK_SERIES + CLIMATE_SERIES


def climate_pair(region: Region) -> tuple[Series, Series]:
    rain, anomaly = (s for s in CLIMATE_SERIES if s.region == region)
    return rain, anomaly


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
    """Publicação reconstituída para carga histórica, escolhida para errar para depois.

    Diárias: dia seguinte ao meio-dia (Copom anuncia a meta na véspera da vigência; a B3
    divulga o CDI na noite do próprio dia). Mensais (IPCA): último dia do mês seguinte ao
    meio-dia. O dia de divulgação do IBGE varia, então não se usa uma data típica: o fim do
    mês seguinte fica depois de qualquer divulgação regular. Sempre marcada como estimada.
    """
    if series.periodicity == "monthly":
        # Primeiro dia do segundo mês seguinte, menos um dia = último dia do mês seguinte.
        index = observation_date.year * 12 + observation_date.month + 1
        day = date(index // 12, index % 12 + 1, 1) - timedelta(days=1)
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


def _br_date(day: date) -> str:
    return day.strftime("%d/%m/%Y")


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
    theme: Theme
    # Limites da leitura, exibidos junto ao sinal: a regra não é previsão nem causa.
    limitations: tuple[str, ...] = ()


_MONTHS = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)  # fmt: skip


_WINDOW_ONLY = "Considera só o histórico coletado pela Valyra, não toda a série do Banco Central."
_NO_FORECAST = "Descreve o que já aconteceu; não antecipa a próxima decisão do Copom."


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
            # O título fala só da janela coletada: antes dela pode ter havido mudança.
            title=(
                f"Selic meta em {display(last.value, series.unit_label)}, sem mudança entre "
                f"{_br_date(first.observation_date)} e {_br_date(last.observation_date)}"
            ),
            summary=(
                "Sem mudança da meta no histórico coletado, de "
                f"{_br_date(first.observation_date)} a {_br_date(last.observation_date)}."
            ),
            observation_date=last.observation_date,
            published_at=max(row.published_at for row in (first, last)),
            evidence_keys=(first.signal_key, last.signal_key),
            rule="selic_meta_stable_v1",
            theme="juros",
            limitations=(_WINDOW_ONLY, _NO_FORECAST),
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
        summary=f"Mudança registrada na observação de {_br_date(after.observation_date)}.",
        observation_date=after.observation_date,
        published_at=max(before.published_at, after.published_at),
        evidence_keys=(before.signal_key, after.signal_key),
        rule="selic_meta_change_v1",
        theme="juros",
        limitations=(_WINDOW_ONLY, _NO_FORECAST),
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
        theme="inflacao",
        limitations=("Compara só dois meses; não indica tendência nem o efeito no seu orçamento.",),
    )


def _same_day(day: date, years_back: int) -> date:
    try:
        return day.replace(year=day.year - years_back)
    except ValueError:  # 29 de fevereiro em ano não bissexto
        return day.replace(year=day.year - years_back, day=28)


def _window_sum(daily: dict[date, Decimal], end: date) -> Decimal | None:
    days = [end - timedelta(days=offset) for offset in range(RAIN_WINDOW_DAYS)]
    if any(day not in daily for day in days):
        return None
    return sum((daily[day] for day in days), Decimal(0))


@dataclass(frozen=True)
class RainReading:
    end: date
    total_mm: Decimal
    normal_mm: Decimal
    years: int
    anomaly_pct: Decimal | None


def rain_reading(
    recent: dict[date, Decimal], history: dict[date, Decimal], end: date
) -> RainReading | None:
    """Chuva acumulada nos 30 dias até `end` contra a média da mesma janela em 10 anos.

    Só janelas completas contam: um dia faltando descarta aquele ano, em vez de virar zero.
    """
    total = _window_sum(recent, end)
    if total is None:
        return None
    sums = [
        value
        for years_back in range(1, NORMAL_YEARS + 1)
        if (value := _window_sum(history, _same_day(end, years_back))) is not None
    ]
    if len(sums) < MIN_NORMAL_YEARS:
        return None
    normal = sum(sums, Decimal(0)) / len(sums)
    anomaly = None
    if normal > 0:
        anomaly = ((total - normal) * 100 / normal).quantize(Decimal("0.1"))
    return RainReading(
        end=end,
        total_mm=total.quantize(Decimal("0.1")),
        normal_mm=normal.quantize(Decimal("0.1")),
        years=len(sums),
        anomaly_pct=anomaly,
    )


DRY_THRESHOLD = Decimal(-30)
WET_THRESHOLD = Decimal(50)


def climate_signal(series: Series, history: Sequence[Revision]) -> DerivedSignal | None:
    """Estiagem ou excesso de chuva relevante na região, pela última anomalia visível."""
    points = [row for row in history if row.value is not None]
    if not points or series.region is None:
        return None
    last = max(points, key=lambda r: r.observation_date)
    assert last.value is not None
    region = series.region
    if last.value <= DRY_THRESHOLD:
        word, rule = "abaixo", "climate_dry_spell_v1"
    elif last.value >= WET_THRESHOLD:
        word, rule = "acima", "climate_wet_spell_v1"
    else:
        return None
    pct = format_decimal(abs(last.value)).replace(".", ",")
    return DerivedSignal(
        key=f"{series.key}:{rule}:{last.observation_date.isoformat()}",
        title=f"Chuva em {region.name} {pct}% {word} da média de {NORMAL_YEARS} anos",
        summary=(
            f"Acumulado de {RAIN_WINDOW_DAYS} dias até {_br_date(last.observation_date)} em região "
            f"de {region.production}. Hipótese a acompanhar: clima fora do padrão em polos "
            "produtores costuma ser observado junto a pressões nos preços de alimentos."
        ),
        observation_date=last.observation_date,
        published_at=last.published_at,
        evidence_keys=(last.signal_key,),
        rule=rule,
        theme="clima",
        limitations=(
            "Dado modelado por coordenada (Open-Meteo), não medição de estação oficial.",
            "Hipótese de acompanhamento: não prevê preços nem demonstra causa.",
        ),
    )


MODEL_STOCK_KEY = "brapi:SLCE3:change_pct"
MODEL_CLIMATE_KEY = "openmeteo:sorriso-mt:rain_30d_anomaly"
MIN_TRAIN = 15
MIN_EVAL = 5
MODEL_WINDOW = 5
MODEL_HORIZON = 5
_MODEL_QUANTUM = Decimal("0.0001")


@dataclass(frozen=True)
class SoyVolatility:
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
    weights: dict[str, str] = field(default_factory=dict)
    evidence_keys: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


def _ridge(samples: list[tuple[list[Decimal], Decimal]], width: int) -> list[Decimal]:
    # Intercepto livre; as outras diagonais recebem lambda=1. Pivoteamento
    # determinístico evita depender de BLAS ou da ordem de execução da máquina.
    matrix = [
        [
            sum((x[i] * x[j] for x, _ in samples), Decimal(0))
            + (Decimal(1) if i == j and i else Decimal(0))
            for j in range(width)
        ]
        + [sum((x[i] * y for x, y in samples), Decimal(0))]
        for i in range(width)
    ]
    for col in range(width):
        pivot = max(range(col, width), key=lambda r: abs(matrix[r][col]))
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        scale = matrix[col][col]
        if not scale:
            raise ValueError("Sistema Ridge singular")
        matrix[col] = [v / scale for v in matrix[col]]
        for row in range(width):
            if row != col:
                factor = matrix[row][col]
                matrix[row] = [
                    a - factor * b for a, b in zip(matrix[row], matrix[col], strict=True)
                ]
    return [row[-1] for row in matrix]


def _prediction(weights: list[Decimal], x: list[Decimal]) -> Decimal:
    return max(Decimal(0), sum((w * v for w, v in zip(weights, x, strict=True)), Decimal(0)))


def _model_text(value: Decimal) -> str:
    return format(value.quantize(_MODEL_QUANTUM, rounding=ROUND_HALF_EVEN), "f")


def estimate_soy_volatility(
    stock_history: Sequence[Revision], climate_history: Sequence[Revision], as_of: datetime
) -> SoyVolatility:
    """Estudo reconstituído com expanding window e embargo de cinco pregões.

    Revisões são escolhidas no instante de cada feature, não só no corte final;
    uma correção publicada depois não reescreve as features de um teste passado.
    """
    with localcontext() as ctx:
        ctx.prec = 40
        return _estimate_soy(stock_history, climate_history, as_of)


def _estimate_soy(stock_history, climate_history, as_of) -> SoyVolatility:
    cutoff_day = as_of.astimezone(BUSINESS_ZONE).date()
    stocks = sorted(
        (
            r
            for r in visible_at(stock_history, as_of).values()
            if r.value is not None and r.observation_date <= cutoff_day
        ),
        key=lambda r: r.observation_date,
    )
    climate = list(visible_at(climate_history, as_of).values())
    base = dict(
        stock_points=len(stocks),
        climate_points=len(climate),
        first_observation_date=stocks[0].observation_date if stocks else None,
        last_observation_date=stocks[-1].observation_date if stocks else None,
    )
    limits = [
        "Janela curta; estudo experimental, sem garantia de desempenho futuro.",
        "Pesos e contribuições são associações estatísticas, não demonstração de causa.",
        "Oscilação mede amplitude de risco, não probabilidade de alta/queda nem recomendação.",
        "Clima modelado em Sorriso não representa todas as operações da empresa.",
        "Janelas de avaliação se sobrepõem; os erros não são amostras independentes.",
    ]
    if any(getattr(r, "published_at_estimated", False) for r in [*stocks, *climate]):
        limits.append(
            "Publicações estimadas: avaliação histórica reconstituída, não backtest ao vivo."
        )
    if not stocks or not climate:
        return SoyVolatility(
            **base,
            reason="Falta histórico de SLCE3 ou clima de Sorriso-MT.",
            limitations=tuple(limits),
        )
    if stocks[-1].observation_date + timedelta(days=7) <= cutoff_day:
        limits.append("Horizonte original já passou: estimativa histórica, não atual.")
    features = {}
    feature_cuts = {}
    used = set()
    for t in range(MODEL_WINDOW - 1, len(stocks)):
        day = stocks[t].observation_date
        # Mesmo calendário conservador da carga histórica: dia seguinte ao meio-dia.
        # Uma primeira coleta tardia também não desloca o passado para incluir o futuro.
        cut = min(
            as_of,
            datetime.combine(day + timedelta(days=1), time(12), BUSINESS_ZONE).astimezone(UTC),
        )
        if t == len(stocks) - 1:
            cut = as_of
        feature_cuts[t] = cut
        past = visible_at(stock_history, cut)
        window = [past.get(r.signal_key) for r in stocks[t - 4 : t + 1]]
        rain = [
            r
            for r in visible_at(climate_history, cut).values()
            if r.value is not None and r.observation_date <= day
        ]
        if any(r is None or r.value is None for r in window) or not rain:
            continue
        water = max(rain, key=lambda r: (r.observation_date, r.published_at, r.revision_id))
        x = [
            Decimal(1),
            sum((r.value**2 for r in window), Decimal(0)).sqrt(),
            abs(window[-1].value),
            abs(water.value) / 100,
        ]
        features[t] = (x, water)
        used.update(r.signal_key for r in window)
        used.add(water.signal_key)
    targets = {
        t: sum((r.value**2 for r in stocks[t + 1 : t + 6]), Decimal(0)).sqrt()
        for t in features
        if t + MODEL_HORIZON < len(stocks)
    }
    errors = [[], []]
    for tau, target in targets.items():
        # Nenhum alvo que termina depois de tau participa do ajuste desse passo.
        known = visible_at(stock_history, feature_cuts[tau])
        train = [
            t
            for t in targets
            if t <= tau - MODEL_HORIZON
            and feature_cuts[t] <= feature_cuts[tau]
            and all(r.signal_key in known for r in stocks[t + 1 : t + 6])
        ]
        labels = {
            t: sum(
                (known[r.signal_key].value ** 2 for r in stocks[t + 1 : t + 6]), Decimal(0)
            ).sqrt()
            for t in train
        }
        if len(train) < MIN_TRAIN:
            continue
        for model, width in enumerate((3, 4)):
            w = _ridge([(features[t][0][:width], labels[t]) for t in train], width)
            errors[model].append(abs(target - _prediction(w, features[tau][0][:width])))
    base.update(train_windows=len(targets), eval_windows=len(errors[0]))
    if (
        len(targets) < MIN_TRAIN + MIN_EVAL
        or len(errors[0]) < MIN_EVAL
        or len(stocks) - 1 not in features
    ):
        return SoyVolatility(
            **base,
            reason=(
                "Histórico alinhado insuficiente: requer treino e avaliação "
                "walk-forward com purge gap."
            ),
            limitations=tuple(limits),
        )
    x, water = features[len(stocks) - 1]
    w0 = _ridge([(features[t][0][:3], y) for t, y in targets.items()], 3)
    w1 = _ridge([(features[t][0], y) for t, y in targets.items()], 4)
    contributions = [w * v for w, v in zip(w1, x, strict=True)]
    forecast = _prediction(w1, x)
    mae0, mae1 = (sum(e, Decimal(0)) / len(e) for e in errors)
    if Decimal(_model_text(mae1)) >= Decimal(_model_text(mae0)):
        limits.append("M1 não superou o baseline M0 no MAE walk-forward desta janela.")
    ordered = sorted(targets.values())
    position = Decimal(len(ordered) - 1) * Decimal("0.75")
    low = int(position)
    threshold = ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (
        position - low
    )
    # Mantém a soma pública das contribuições compatível com o truncamento e arredondamento.
    parts = [v.quantize(_MODEL_QUANTUM, rounding=ROUND_HALF_EVEN) for v in contributions]
    adjustment = forecast.quantize(_MODEL_QUANTUM, rounding=ROUND_HALF_EVEN) - sum(parts)
    return SoyVolatility(
        **base,
        status="ready",
        m0_forecast_pct=_model_text(_prediction(w0, x[:3])),
        m1_forecast_pct=_model_text(forecast),
        intercept_pct=_model_text(parts[0]),
        market_persistence_pct=_model_text(parts[1]),
        daily_shock_pct=_model_text(parts[2]),
        climate_component_pct=_model_text(parts[3]),
        truncation_adjustment_pct=_model_text(adjustment),
        recent_rv_5d_pct=_model_text(x[1]),
        sorriso_rain_anomaly_pct=_model_text(water.value),
        mae_m0_pp=_model_text(mae0),
        mae_m1_pp=_model_text(mae1),
        regime="elevada" if forecast >= threshold else "normal",
        weights={
            key: _model_text(value)
            for key, value in zip(
                ("intercept", "market_persistence", "daily_shock", "climate"), w1, strict=True
            )
        },
        evidence_keys=tuple(sorted(used | {r.signal_key for r in stocks})),
        limitations=tuple(limits),
    )
