"""Previsões estatísticas do Alpha (ADR-0016): calculadas em código, nunca pelo LLM.

Analogia do projeto: a calculadora e o narrador. Este módulo é a calculadora. Ele ajusta um
modelo simples a cada série, simula 1.000 cenários e devolve faixas, chances e um teste com o
passado. O narrador (a "visão da Valyra" e a Valyra AI) só lê o resultado pronto.

Nada aqui lê banco, rede ou relógio. Os indicadores não são dinheiro (taxas em %, índices),
então a conta interna usa float; a saída é arredondada e vira texto decimal no service.

Modelos:
- `holt_damped`: suavização exponencial com tendência amortecida (Holt), parâmetros escolhidos
  pelo menor erro de um passo no próprio histórico. Serve para séries mensais com inércia
  (IPCA, Selic, CDI, índice de commodities).
- `random_walk`: passeio aleatório sem tendência, com os retornos do passado reamostrados.
  Serve para preço de mercado (ações, dólar), em que tendência de curto prazo não se sustenta.

Em ambos os casos os cenários usam os erros do próprio passado (reamostragem), em vez de supor
uma curva normal. A "chance" é a fração de cenários em que o evento acontece, e o teste com o
passado mostra quantas vezes a faixa de 80% teria acertado. É isso que dá suporte verificável
aos percentuais exibidos.
"""

from __future__ import annotations

import math
import random
import zlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

Frequency = Literal["monthly", "daily"]
Method = Literal["holt_damped", "random_walk"]
Stance = Literal["atencao", "neutra", "favoravel"]
DataOrigin = Literal["coleta", "reserva"]

PATHS = 1000
BACKTEST_PATHS = 300
METHOD_VERSION = "forecast_v1"
VIEW_RULE = "forecast_view_v1"
# Copom decide a Selic em múltiplos de 0,25 ponto; cada cenário é arredondado a esse passo.
SELIC_STEP = 0.25
# Meta contínua de inflação do CMN para 2026: 3% com tolerância de 1,5 ponto.
IPCA_CEILING = 4.5
BUSINESS_DAYS_YEAR = 252

_ALPHAS = (0.1, 0.2, 0.3, 0.5, 0.7, 0.9)
_BETAS = (0.0, 0.05, 0.1, 0.2)
_PHIS = (0.8, 0.9, 0.98)


# ---------- Séries regulares ----------


@dataclass(frozen=True)
class Observation:
    day: date
    value: float


def month_start(day: date) -> date:
    return day.replace(day=1)


def add_months(day: date, months: int) -> date:
    index = day.year * 12 + day.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def monthly_last(points: Sequence[Observation]) -> list[Observation]:
    """Último valor de cada mês (Selic meta vale no fim do mês)."""
    by_month: dict[date, Observation] = {}
    for point in sorted(points, key=lambda p: p.day):
        by_month[month_start(point.day)] = point
    return [Observation(month, p.value) for month, p in sorted(by_month.items())]


def monthly_mean(points: Sequence[Observation]) -> list[Observation]:
    groups: dict[date, list[float]] = {}
    for point in points:
        groups.setdefault(month_start(point.day), []).append(point.value)
    return [Observation(m, sum(v) / len(v)) for m, v in sorted(groups.items())]


def complete_months(points: list[Observation], last_day: date) -> list[Observation]:
    """Descarta o mês corrente quando ainda não acabou: média parcial distorce a série."""
    if points and points[-1].day == month_start(last_day):
        following = add_months(month_start(last_day), 1) - timedelta(days=1)
        if last_day < following:
            return points[:-1]
    return points


def cdi_annualized(daily_pct: float) -> float:
    """CDI diário (% ao dia) em taxa anual equivalente, com 252 dias úteis."""
    return ((1 + daily_pct / 100) ** BUSINESS_DAYS_YEAR - 1) * 100


def next_business_days(start: date, count: int) -> list[date]:
    days: list[date] = []
    day = start
    while len(days) < count:
        day += timedelta(days=1)
        if day.weekday() < 5:  # feriados não entram: a data é aproximada e só ilustra o eixo
            days.append(day)
    return days


def basket_returns(series: Sequence[Sequence[Observation]]) -> list[Observation]:
    """Variação média do dia (pesos iguais) nos dias em que todas as ações têm dado."""
    if not series:
        return []
    maps = [{p.day: p.value for p in s} for s in series]
    common = set(maps[0]).intersection(*maps[1:])
    return [Observation(d, sum(m[d] for m in maps) / len(maps)) for d in sorted(common)]


# ---------- Modelos ----------


@dataclass(frozen=True)
class HoltFit:
    alpha: float
    beta: float
    phi: float
    level: float
    trend: float
    residuals: tuple[float, ...]

    @property
    def sigma(self) -> float:
        if len(self.residuals) < 2:
            return 0.0
        mean = sum(self.residuals) / len(self.residuals)
        return math.sqrt(sum((r - mean) ** 2 for r in self.residuals) / (len(self.residuals) - 1))


def _holt_pass(values: Sequence[float], alpha: float, beta: float, phi: float):
    level = values[0]
    trend = values[1] - values[0] if len(values) > 1 else 0.0
    sse = 0.0
    residuals: list[float] = []
    for index, value in enumerate(values[1:], start=1):
        forecast = level + phi * trend
        error = value - forecast
        # Os primeiros passos ainda acomodam o nível inicial; não entram no erro do ajuste.
        if index >= 3:
            sse += error * error
            residuals.append(error)
        level = forecast + alpha * error
        trend = phi * trend + beta * error
    return sse, level, trend, residuals


def fit_holt(values: Sequence[float]) -> HoltFit:
    if len(values) < 6:
        raise ValueError("Histórico curto demais para ajustar o modelo")
    best: tuple[float, HoltFit] | None = None
    for alpha in _ALPHAS:
        for beta in _BETAS:
            for phi in _PHIS:
                sse, level, trend, residuals = _holt_pass(values, alpha, beta, phi)
                if best is None or sse < best[0] - 1e-12:
                    best = (sse, HoltFit(alpha, beta, phi, level, trend, tuple(residuals)))
    assert best is not None
    return best[1]


def simulate_holt(fit: HoltFit, horizon: int, paths: int, rng: random.Random) -> list[list[float]]:
    """Cenários futuros pelo próprio modelo, sorteando erros do passado (reamostragem)."""
    pool = fit.residuals or (0.0,)
    out: list[list[float]] = []
    for _ in range(paths):
        level, trend = fit.level, fit.trend
        path: list[float] = []
        for _step in range(horizon):
            forecast = level + fit.phi * trend
            error = rng.choice(pool)
            value = forecast + error
            path.append(value)
            level = forecast + fit.alpha * error
            trend = fit.phi * trend + fit.beta * error
        out.append(path)
    return out


def log_returns(index_points: Sequence[float]) -> list[float]:
    return [math.log(b / a) for a, b in zip(index_points, index_points[1:], strict=False)]


def index_from_changes(changes_pct: Sequence[float], base: float = 100.0) -> list[float]:
    """Índice encadeado a partir das variações do dia (%), como uma cota que começa em 100."""
    level = base
    out = [level]
    for change in changes_pct:
        level *= 1 + change / 100
        out.append(level)
    return out


def simulate_random_walk(
    last: float, returns: Sequence[float], horizon: int, paths: int, rng: random.Random
) -> list[list[float]]:
    """Passeio aleatório sem tendência: retornos do passado sem a média, sorteados."""
    if not returns:
        return [[last] * horizon for _ in range(paths)]
    mean = sum(returns) / len(returns)
    pool = [r - mean for r in returns]
    out = []
    for _ in range(paths):
        level = last
        path = []
        for _step in range(horizon):
            level *= math.exp(rng.choice(pool))
            path.append(level)
        out.append(path)
    return out


def quantile(values: Sequence[float], q: float) -> float:
    """Quantil pelo cenário mais próximo: o valor exibido é sempre um cenário simulado."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError("Sem valores")
    return ordered[round((len(ordered) - 1) * q)]


def rng_for(key: str) -> random.Random:
    # Semente fixa por previsão: a mesma entrada sempre gera os mesmos cenários (auditável).
    return random.Random(zlib.crc32(key.encode()))


# ---------- Catálogo ----------

Kind = Literal["ipca_12m", "selic_6m", "renda_fixa_12m", "juro_real_12m", "acoes_1m",
               "dolar_1m", "agro_6m"]  # fmt: skip

SELIC_KEY = "bcb:sgs:432"
CDI_KEY = "bcb:sgs:12"
IPCA_KEY = "bcb:sgs:433"
DOLLAR_KEY = "bcb:sgs:1"
AGRO_KEY = "bcb:sgs:27575"
STOCK_TICKERS = ("PETR4", "VALE3", "ITUB4", "MGLU3")
STOCK_KEYS = tuple(f"brapi:{t}:change_pct" for t in STOCK_TICKERS)


@dataclass(frozen=True)
class Event:
    label: str
    test: Callable[[float, float], bool]  # (valor do cenário, valor de hoje) -> aconteceu?


@dataclass(frozen=True)
class Spec:
    kind: Kind
    title: str
    question: str
    inputs: tuple[str, ...]
    method: Method
    frequency: Frequency
    horizon: int
    horizon_label: str
    unit: str
    unit_label: str
    # Pontos mínimos da série base (já mensal ou diária) para confiar no ajuste.
    min_points: int
    event: Event | None
    method_label: str
    limitations: tuple[str, ...] = ()


_LIMIT_PAST = "O modelo só olha o passado da própria série; choques novos ficam de fora."
_LIMIT_NOT_ADVICE = "Leitura estatística, não recomendação de investimento."

SPECS: dict[Kind, Spec] = {
    "ipca_12m": Spec(
        kind="ipca_12m",
        title="Inflação (IPCA) acumulada em 12 meses",
        question="Para onde vai a inflação nos próximos 6 meses?",
        inputs=(IPCA_KEY,),
        method="holt_damped",
        frequency="monthly",
        horizon=6,
        horizon_label="daqui a 6 meses",
        unit="%",
        unit_label="% em 12 meses",
        min_points=24,
        event=Event("passar do teto da meta (4,5%)", lambda v, _now: v > IPCA_CEILING),
        method_label="Suavização exponencial com tendência amortecida (Holt) no IPCA mensal",
        limitations=(
            _LIMIT_PAST,
            "Não usa a sazonalidade do calendário nem as expectativas do Focus.",
        ),
    ),
    "selic_6m": Spec(
        kind="selic_6m",
        title="Selic meta",
        question="A Selic deve subir, cair ou ficar parada?",
        inputs=(SELIC_KEY,),
        method="holt_damped",
        frequency="monthly",
        horizon=6,
        horizon_label="daqui a 6 meses",
        unit="%",
        unit_label="% ao ano",
        min_points=24,
        event=Event("estar abaixo da Selic de hoje", lambda v, now: v < now - 1e-9),
        method_label="Holt amortecido na Selic de fim de mês, cenários arredondados a 0,25 ponto",
        limitations=(
            _LIMIT_PAST,
            "Não lê o comunicado do Copom; decisões fora do padrão ficam fora.",
        ),
    ),
    "renda_fixa_12m": Spec(
        kind="renda_fixa_12m",
        title="Renda fixa a 100% do CDI em 12 meses",
        question="Quanto a renda fixa pós-fixada pode render no próximo ano?",
        inputs=(CDI_KEY,),
        method="holt_damped",
        frequency="monthly",
        horizon=12,
        horizon_label="nos próximos 12 meses",
        unit="%",
        unit_label="% em 12 meses, antes do IR",
        min_points=24,
        event=None,
        method_label="Holt amortecido no CDI anualizado mês a mês, rendimento composto",
        limitations=(
            _LIMIT_PAST,
            "Bruto: não desconta imposto de renda nem taxas.",
            _LIMIT_NOT_ADVICE,
        ),
    ),
    "juro_real_12m": Spec(
        kind="juro_real_12m",
        title="Juro real: CDI acima da inflação em 12 meses",
        question="A renda fixa deve ganhar da inflação?",
        inputs=(CDI_KEY, IPCA_KEY),
        method="holt_damped",
        frequency="monthly",
        horizon=12,
        horizon_label="nos próximos 12 meses",
        unit="%",
        unit_label="% acima do IPCA em 12 meses",
        min_points=24,
        event=Event("render acima da inflação", lambda v, _now: v > 0),
        method_label="Cenários do CDI e do IPCA combinados um a um: (1 + CDI) / (1 + IPCA) − 1",
        limitations=(
            _LIMIT_PAST,
            "Combina os cenários como se juros e inflação fossem independentes.",
            _LIMIT_NOT_ADVICE,
        ),
    ),
    "acoes_1m": Spec(
        kind="acoes_1m",
        title="Cesta de ações acompanhadas",
        question="Quanto a bolsa pode oscilar no próximo mês?",
        inputs=STOCK_KEYS,
        method="random_walk",
        frequency="daily",
        horizon=21,
        horizon_label="em 21 pregões (cerca de 1 mês)",
        unit="%",
        unit_label="% de variação",
        min_points=40,
        event=Event("fechar o período em alta", lambda v, _now: v > 0),
        method_label=(
            "Passeio aleatório sem tendência, com as variações diárias do passado sorteadas"
        ),
        limitations=(
            "Preço de ação no curto prazo não tem tendência previsível: a faixa mede o risco.",
            "Pesos iguais entre PETR4, VALE3, ITUB4 e MGLU3; não é a sua carteira nem o Ibovespa.",
            _LIMIT_NOT_ADVICE,
        ),
    ),
    "dolar_1m": Spec(
        kind="dolar_1m",
        title="Dólar comercial",
        question="Quanto o dólar pode variar no próximo mês?",
        inputs=(DOLLAR_KEY,),
        method="random_walk",
        frequency="daily",
        horizon=21,
        horizon_label="em 21 dias úteis (cerca de 1 mês)",
        unit="%",
        unit_label="% de variação",
        min_points=60,
        event=Event("subir mais de 2%", lambda v, _now: v > 2),
        method_label="Passeio aleatório sem tendência no dólar de venda (PTAX diária do SGS)",
        limitations=(
            "Câmbio no curto prazo não tem tendência previsível: a faixa mede o risco.",
            _LIMIT_NOT_ADVICE,
        ),
    ),
    "agro_6m": Spec(
        kind="agro_6m",
        title="Commodities agro (IC-Br Agropecuária)",
        question="Os preços do agro (soja, milho, café, boi) devem subir?",
        inputs=(AGRO_KEY,),
        method="holt_damped",
        frequency="monthly",
        horizon=6,
        horizon_label="daqui a 6 meses",
        unit="%",
        unit_label="% de variação do índice",
        min_points=24,
        event=Event("subir no período", lambda v, _now: v > 0),
        method_label=(
            "Holt amortecido no Índice de Commodities do Banco Central, parte agropecuária"
        ),
        limitations=(
            _LIMIT_PAST,
            "É preço de commodity em reais no atacado, não o preço do supermercado.",
        ),
    ),
}

PROFILE_SPECS: dict[str, tuple[Kind, ...]] = {
    "orcamento-apertado": ("ipca_12m", "agro_6m", "selic_6m"),
    "comecando-a-investir": ("juro_real_12m", "renda_fixa_12m", "selic_6m", "ipca_12m"),
    "investidor": ("acoes_1m", "dolar_1m", "selic_6m", "agro_6m"),
}
DEFAULT_SPECS: tuple[Kind, ...] = ("ipca_12m", "selic_6m", "acoes_1m")


# ---------- Resultado ----------


@dataclass(frozen=True)
class Band:
    p2_5: float
    p10: float
    p50: float
    p90: float
    p97_5: float

    @classmethod
    def of(cls, values: Sequence[float]) -> Band:
        return cls(*(quantile(values, q) for q in (0.025, 0.1, 0.5, 0.9, 0.975)))


@dataclass(frozen=True)
class FanPoint:
    day: date
    band: Band


@dataclass(frozen=True)
class Backtest:
    """Teste com o passado: a faixa de 80% acertou o valor real em `hits` de `trials`."""

    horizon: int
    horizon_label: str
    trials: int
    hits: int
    model_mae: float | None
    naive_mae: float | None


@dataclass(frozen=True)
class TickerRange:
    ticker: str
    band: Band
    chance_up: float
    daily_vol: float


@dataclass(frozen=True)
class View:
    stance: Stance
    headline: str
    text: str


@dataclass(frozen=True)
class Forecast:
    spec: Spec
    current: float
    current_label: str
    headline: Band
    chance: float | None
    history: list[Observation]
    fan: list[FanPoint]
    chart_unit: str
    backtest: Backtest | None
    view: View
    observations: int
    first_day: date
    last_day: date
    params: dict[str, float] = field(default_factory=dict)
    tickers: list[TickerRange] = field(default_factory=list)


# ---------- Cálculo por tipo ----------


def _accum(rates_pct: Sequence[float]) -> float:
    total = 1.0
    for rate in rates_pct:
        total *= 1 + rate / 100
    return (total - 1) * 100


def _monthly_return(annual_pct: float) -> float:
    return ((1 + annual_pct / 100) ** (1 / 12) - 1) * 100


def _fan(days: Sequence[date], paths: Sequence[Sequence[float]]) -> list[FanPoint]:
    return [FanPoint(day, Band.of([p[i] for p in paths])) for i, day in enumerate(days)]


def _holt_backtest(
    values: Sequence[float], horizon: int, label: str, key: str, origins: int = 12,
    clamp: Callable[[float], float] = lambda v: v,
) -> Backtest | None:  # fmt: skip
    """Refaz a previsão em datas passadas e confere com o que aconteceu depois."""
    hits = trials = 0
    model_err = naive_err = 0.0
    rng = rng_for(f"{key}:backtest")
    for end in range(len(values) - horizon - origins + 1, len(values) - horizon + 1):
        train = values[:end]
        if len(train) < 18:
            continue
        fit = fit_holt(train)
        sims = [clamp(p[horizon - 1]) for p in simulate_holt(fit, horizon, BACKTEST_PATHS, rng)]
        actual = values[end + horizon - 1]
        band = Band.of(sims)
        trials += 1
        hits += band.p10 <= actual <= band.p90
        model_err += abs(band.p50 - actual)
        naive_err += abs(train[-1] - actual)
    if not trials:
        return None
    return Backtest(horizon, label, trials, hits, model_err / trials, naive_err / trials)


def _rw_backtest(
    index: Sequence[float], horizon: int, label: str, key: str, origins: int = 20, gap: int = 5
) -> Backtest | None:
    hits = trials = 0
    rng = rng_for(f"{key}:backtest")
    for k in range(origins):
        end = len(index) - horizon - k * gap
        if end < 30:
            break
        train = index[:end]
        sims = [
            p[-1] / train[-1] * 100 - 100
            for p in simulate_random_walk(
                train[-1], log_returns(train), horizon, BACKTEST_PATHS, rng
            )
        ]
        actual = index[end + horizon - 1] / train[-1] * 100 - 100
        band = Band.of(sims)
        trials += 1
        hits += band.p10 <= actual <= band.p90
    if not trials:
        return None
    return Backtest(horizon, label, trials, hits, None, None)


def _chance(spec: Spec, values: Sequence[float], now: float) -> float | None:
    if spec.event is None:
        return None
    return sum(1 for v in values if spec.event.test(v, now)) / len(values)


@dataclass(frozen=True)
class Prepared:
    """Séries base já regulares, prontas para o modelo (mensais ou diárias)."""

    series: dict[str, list[Observation]]
    as_of_day: date


def _round_step(value: float, step: float) -> float:
    return round(value / step) * step


def _holt_case(
    spec: Spec, base: list[Observation], horizon: int, clamp=lambda v: v
) -> tuple[HoltFit, list[list[float]], list[date]]:
    fit = fit_holt([p.value for p in base])
    paths = [
        [clamp(v) for v in path] for path in simulate_holt(fit, horizon, PATHS, rng_for(spec.kind))
    ]
    days = [add_months(base[-1].day, i) for i in range(1, horizon + 1)]
    return fit, paths, days


def _params(fit: HoltFit) -> dict[str, float]:
    return {"alpha": fit.alpha, "beta": fit.beta, "phi": fit.phi, "sigma": fit.sigma}


def compute(spec: Spec, base: dict[str, list[Observation]], profile: str | None) -> Forecast:
    """Previsão de um item do catálogo com as séries base já preparadas e suficientes."""
    kind = spec.kind
    if kind == "ipca_12m":
        series = base[IPCA_KEY]
        fit, paths, days = _holt_case(spec, series, spec.horizon)
        past = [p.value for p in series]
        current = _accum(past[-12:])
        keep = 12 - spec.horizon
        headline = [_accum(past[-keep:] + path) for path in paths]
        # O gráfico mostra o acumulado em 12 meses, a medida que as pessoas acompanham.
        history = [
            Observation(series[i].day, _accum(past[i - 11 : i + 1]))
            for i in range(max(11, len(series) - 24), len(series))
        ]
        fan_paths = [
            [
                _accum((past + path)[len(past) + s - 11 : len(past) + s + 1])
                for s in range(spec.horizon)
            ]
            for path in paths
        ]
        return _build(
            spec, profile, current, "acumulado nos últimos 12 meses", headline, history,
            _fan(days, fan_paths), "% em 12 meses",
            _holt_backtest(past, 3, "3 meses à frente, no IPCA do mês", kind), series, _params(fit),
        )  # fmt: skip
    if kind == "selic_6m":
        series = base[SELIC_KEY]
        clamp = lambda v: max(2.0, _round_step(v, SELIC_STEP))  # noqa: E731
        fit, paths, days = _holt_case(spec, series, spec.horizon, clamp)
        current = series[-1].value
        headline = [p[-1] for p in paths]
        return _build(
            spec, profile, current, "meta vigente", headline, series[-24:],
            _fan(days, paths), "% ao ano",
            _holt_backtest([p.value for p in series], 3, "3 meses à frente", kind, clamp=clamp),
            series, _params(fit),
        )  # fmt: skip
    if kind == "renda_fixa_12m":
        series = base[CDI_KEY]
        clamp = lambda v: max(0.0, v)  # noqa: E731
        fit, paths, days = _holt_case(spec, series, spec.horizon, clamp)
        current = _accum([_monthly_return(p.value) for p in series[-12:]])
        headline = [_accum([_monthly_return(v) for v in path]) for path in paths]
        return _build(
            spec, profile, current, "rendeu nos últimos 12 meses", headline, series[-24:],
            _fan(days, paths), "% ao ano (CDI anualizado)",
            _holt_backtest([p.value for p in series], 3, "3 meses à frente, no CDI anualizado",
                           kind, clamp=clamp),
            series, _params(fit),
        )  # fmt: skip
    if kind == "juro_real_12m":
        cdi, ipca = base[CDI_KEY], base[IPCA_KEY]
        cdi_fit, cdi_paths, days = _holt_case(spec, cdi, spec.horizon, lambda v: max(0.0, v))
        ipca_fit = fit_holt([p.value for p in ipca])
        ipca_paths = simulate_holt(ipca_fit, spec.horizon, PATHS, rng_for(f"{kind}:ipca"))

        def real(cdi_path: Sequence[float], ipca_path: Sequence[float]) -> float:
            nominal = _accum([_monthly_return(v) for v in cdi_path])
            inflation = _accum(ipca_path)
            return ((1 + nominal / 100) / (1 + inflation / 100) - 1) * 100

        past_nominal = _accum([_monthly_return(p.value) for p in cdi[-12:]])
        past_inflation = _accum([p.value for p in ipca[-12:]])
        current = ((1 + past_nominal / 100) / (1 + past_inflation / 100) - 1) * 100
        headline = [real(c, i) for c, i in zip(cdi_paths, ipca_paths, strict=True)]
        # Gráfico: juro real anualizado mês a mês (CDI anual contra IPCA do mês anualizado).
        ipca_by_month = {p.day: p.value for p in ipca}
        history = [
            Observation(
                p.day, ((1 + p.value / 100) / (1 + ipca_by_month[p.day] / 100) ** 12 - 1) * 100
            )
            for p in cdi[-24:]
            if p.day in ipca_by_month
        ]
        fan_paths = [
            [((1 + c[s] / 100) / (1 + i[s] / 100) ** 12 - 1) * 100 for s in range(spec.horizon)]
            for c, i in zip(cdi_paths, ipca_paths, strict=True)
        ]
        params = {f"cdi_{k}": v for k, v in _params(cdi_fit).items()}
        params |= {f"ipca_{k}": v for k, v in _params(ipca_fit).items()}
        return _build(
            spec, profile, current, "nos últimos 12 meses", headline, history,
            _fan(days, fan_paths), "% ao ano acima da inflação",
            _holt_backtest([p.value for p in ipca], 3, "3 meses à frente, no IPCA do mês",
                           f"{kind}:ipca"),
            cdi, params,
        )  # fmt: skip
    if kind == "agro_6m":
        series = base[AGRO_KEY]
        fit, paths, days = _holt_case(spec, series, spec.horizon, lambda v: max(0.01, v))
        last = series[-1].value
        current = (last / series[-13].value - 1) * 100 if len(series) > 12 else 0.0
        headline = [(p[-1] / last - 1) * 100 for p in paths]
        rebase = 100 / last  # gráfico em índice com hoje = 100
        history = [Observation(p.day, p.value * rebase) for p in series[-24:]]
        fan_paths = [[v * rebase for v in p] for p in paths]
        return _build(
            spec, profile, current, "variação nos últimos 12 meses", headline, history,
            _fan(days, fan_paths), "índice, hoje = 100",
            _holt_backtest([p.value for p in series], 3, "3 meses à frente", kind),
            series, _params(fit),
        )  # fmt: skip
    if kind in ("acoes_1m", "dolar_1m"):
        if kind == "acoes_1m":
            changes = basket_returns([base[k] for k in STOCK_KEYS])
            index = index_from_changes([p.value for p in changes])
            days_index = [changes[0].day - timedelta(days=1)] + [p.day for p in changes]
        else:
            prices = base[DOLLAR_KEY]
            index = [p.value / prices[-1].value * 100 for p in prices]
            days_index = [p.day for p in prices]
        index = [v / index[-1] * 100 for v in index]  # hoje = 100
        returns = log_returns(index)
        paths = simulate_random_walk(100.0, returns, spec.horizon, PATHS, rng_for(kind))
        days = next_business_days(days_index[-1], spec.horizon)
        headline = [p[-1] - 100 for p in paths]
        window = min(21, len(index) - 1)
        current = index[-1] / index[-1 - window] * 100 - 100
        daily_vol = _std(returns) * 100
        tickers = (
            [_ticker_range(t, base[k]) for t, k in zip(STOCK_TICKERS, STOCK_KEYS, strict=True)]
            if kind == "acoes_1m"
            else []
        )
        history = [Observation(d, v) for d, v in zip(days_index[-60:], index[-60:], strict=True)]
        return _build(
            spec, profile, current, f"variação nos últimos {window} pregões", headline, history,
            _fan(days, paths), "índice, hoje = 100",
            _rw_backtest(index, 5, "5 pregões à frente", kind),
            [Observation(d, v) for d, v in zip(days_index, index, strict=True)],
            {"daily_vol_pct": daily_vol}, tickers,
        )  # fmt: skip
    raise ValueError(f"Previsão desconhecida: {kind}")


def _std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))


def _ticker_range(ticker: str, changes: list[Observation]) -> TickerRange:
    index = index_from_changes([p.value for p in changes])
    returns = log_returns(index)
    paths = simulate_random_walk(1.0, returns, 21, PATHS, rng_for(f"acoes_1m:{ticker}"))
    values = [(p[-1] - 1) * 100 for p in paths]
    return TickerRange(
        ticker, Band.of(values), sum(v > 0 for v in values) / len(values), _std(returns) * 100
    )


def _build(
    spec: Spec, profile: str | None, current: float, current_label: str,
    headline_values: Sequence[float], history: list[Observation], fan: list[FanPoint],
    chart_unit: str, backtest: Backtest | None, base: list[Observation],
    params: dict[str, float], tickers: list[TickerRange] | None = None,
) -> Forecast:  # fmt: skip
    band = Band.of(headline_values)
    chance = _chance(spec, headline_values, current)
    return Forecast(
        spec=spec,
        current=current,
        current_label=current_label,
        headline=band,
        chance=chance,
        history=history,
        fan=fan,
        chart_unit=chart_unit,
        backtest=backtest,
        view=valyra_view(spec, band, chance, current, profile),
        observations=len(base),
        first_day=base[0].day,
        last_day=base[-1].day,
        params=params,
        tickers=tickers or [],
    )


# ---------- Visão da Valyra (regra forecast_view_v1) ----------


def pct(value: float, digits: int = 1) -> str:
    rounded = round(value, digits)
    # "-0,0%" confunde: arredondado a zero, o sinal sai.
    return f"{(rounded if rounded != 0 else 0.0):.{digits}f}".replace(".", ",")


def chance_text(chance: float) -> str:
    return f"{round(chance * 100)}%"


_PROFILE_HINT: dict[str, dict[Kind, dict[Stance, str]]] = {
    "orcamento-apertado": {
        "ipca_12m": {
            "atencao": "Para o seu orçamento: vale deixar uma folga em mercado e contas da casa.",
            "neutra": "Para o seu orçamento: mantenha os tetos atuais e acompanhe o mercado.",
            "favoravel": (
                "Para o seu orçamento: os preços tendem a subir devagar; os tetos atuais devem "
                "aguentar."
            ),
        },
        "agro_6m": {
            "atencao": (
                "Alimentos costumam sentir isso meses depois: reserve espaço na categoria mercado."
            ),
            "neutra": "Sem pressão clara vinda do campo para a sua categoria mercado.",
            "favoravel": "O campo dá folga: bom momento para manter o teto de mercado sem aperto.",
        },
        "selic_6m": {
            "atencao": "Crédito segue caro: evite parcelar com juros e priorize quitar dívidas.",
            "neutra": "Juros sem mudança clara: dívida no cartão continua sendo a mais cara.",
            "favoravel": "Se os juros caírem, renegociar dívidas pode ficar mais barato.",
        },
    },
    "comecando-a-investir": {
        "juro_real_12m": {
            "atencao": "A renda fixa pode não proteger da inflação: compare antes de investir.",
            "neutra": "A renda fixa deve ficar perto da inflação: sem ganho real garantido.",
            "favoravel": (
                "Ganho acima da inflação na maioria dos cenários: renda fixa segue competitiva."
            ),
        },
        "renda_fixa_12m": {
            "atencao": "O rendimento pode cair: prazos mais longos travam a taxa de hoje.",
            "neutra": (
                "Rendimento estável: a reserva de emergência em 100% do CDI segue bem servida."
            ),
            "favoravel": (
                "Rendimento alto: a reserva de emergência em 100% do CDI segue bem servida."
            ),
        },
        "selic_6m": {
            "atencao": "Juros subindo favorecem o pós-fixado (CDI) frente ao prefixado.",
            "neutra": "Juros parados: pós-fixado e prefixado tendem a render parecido.",
            "favoravel": "Se a Selic cair, prefixados e títulos longos travam a taxa de hoje.",
        },
        "ipca_12m": {
            "atencao": (
                "Inflação alta corrói o que fica parado: títulos atrelados ao IPCA protegem."
            ),
            "neutra": "Inflação perto da meta: compare sempre o rendimento com o IPCA.",
            "favoravel": "Inflação comportada: o juro de hoje vira mais ganho real.",
        },
    },
    "investidor": {
        "acoes_1m": {
            "atencao": (
                "Oscilação alta: aportes mensais diluem o risco melhor do que um aporte único."
            ),
            "neutra": (
                "Oscilação normal para bolsa: a faixa ajuda a dimensionar o quanto aguenta ver no "
                "vermelho."
            ),
            "favoravel": (
                "Oscilação baixa para o padrão: mesmo assim, ninguém sabe o lado do próximo mês."
            ),
        },
        "dolar_1m": {
            "atencao": (
                "Chance relevante de alta forte: proteção cambial pode fazer sentido na carteira."
            ),
            "neutra": "Câmbio sem sinal claro: diversificação em dólar é decisão de longo prazo.",
            "favoravel": "Câmbio calmo: sem urgência para mexer na exposição em dólar.",
        },
        "selic_6m": {
            "atencao": (
                "Juros altos por mais tempo pesam sobre ações e FIIs e favorecem a renda fixa."
            ),
            "neutra": "Juros sem mudança clara: o custo de oportunidade da renda fixa segue alto.",
            "favoravel": (
                "Queda de juros costuma ser observada junto à valorização de FIIs e ações."
            ),
        },
        "agro_6m": {
            "atencao": (
                "Commodities agro subindo: empresas do setor e a inflação de alimentos merecem "
                "atenção."
            ),
            "neutra": "Commodities agro sem direção clara nos cenários.",
            "favoravel": "Commodities agro em baixa: menor pressão na inflação de alimentos.",
        },
    },
}


def valyra_view(
    spec: Spec, band: Band, chance: float | None, current: float, profile: str | None
) -> View:
    """Leitura da Valyra por regra fixa e versionada; usa só os números calculados acima."""
    kind = spec.kind
    low, mid, high = pct(band.p10), pct(band.p50), pct(band.p90)
    if kind == "ipca_12m":
        assert chance is not None
        stance: Stance = "atencao" if chance >= 0.6 else "favoravel" if chance < 0.3 else "neutra"
        headline = {
            "atencao": "Inflação pressionada",
            "neutra": "Inflação dividida perto do teto",
            "favoravel": "Inflação dentro da meta",
        }[stance]
        text = (
            f"No cenário central o IPCA em 12 meses fica em {mid}%, entre {low}% e {high}% em "
            f"8 de cada 10 cenários. Chance de passar do teto da meta: {chance_text(chance)}."
        )
    elif kind == "selic_6m":
        assert chance is not None
        if band.p50 > current + 0.1:
            stance, headline = "atencao", "Juros com viés de alta"
        elif chance >= 0.5:
            stance, headline = "favoravel", "Juros com viés de queda"
        else:
            stance, headline = "neutra", "Juros tendem a ficar onde estão"
        text = (
            f"Hoje a Selic está em {pct(current, 2)}%. No cenário central ela fica em "
            f"{pct(band.p50, 2)}% {spec.horizon_label}, entre {pct(band.p10, 2)}% e "
            f"{pct(band.p90, 2)}% em 8 de cada 10 cenários. "
            f"Chance de estar abaixo de hoje: {chance_text(chance)}."
        )
    elif kind == "renda_fixa_12m":
        stance = "favoravel" if band.p50 >= current - 0.5 else "atencao"
        headline = "Rendimento alto mantido" if stance == "favoravel" else "Rendimento tende a cair"
        text = (
            f"Nos últimos 12 meses o CDI rendeu {pct(current)}%. Para os próximos 12, o cenário "
            f"central é {mid}%, entre {low}% e {high}% em 8 de cada 10 cenários."
        )
    elif kind == "juro_real_12m":
        assert chance is not None
        stance = "favoravel" if chance >= 0.8 else "atencao" if chance < 0.5 else "neutra"
        headline = {
            "favoravel": "Renda fixa à frente da inflação",
            "neutra": "Ganho real incerto",
            "atencao": "Inflação pode ganhar da renda fixa",
        }[stance]
        text = (
            f"No cenário central o CDI rende {mid}% acima da inflação em 12 meses, entre {low}% e "
            f"{high}% em 8 de cada 10 cenários. "
            f"Chance de ganhar da inflação: {chance_text(chance)}."
        )
    elif kind in ("acoes_1m", "dolar_1m"):
        assert chance is not None
        width = band.p90 - band.p10
        stance = "atencao" if width >= (14 if kind == "acoes_1m" else 7) else "neutra"
        if kind == "dolar_1m" and chance < 0.1:
            stance = "favoravel"
        label = "a cesta" if kind == "acoes_1m" else "o dólar"
        headline = {
            "atencao": "Oscilação larga à frente",
            "neutra": "Oscilação dentro do normal",
            "favoravel": "Câmbio calmo",
        }[stance]
        event = spec.event.label if spec.event else ""
        text = (
            f"Em 8 de cada 10 cenários {label} termina {spec.horizon_label} entre {low}% e "
            f"{high}%. Chance de {event}: {chance_text(chance)}. O modelo não aposta em direção: "
            "a faixa mede o risco."
        )
    else:  # agro_6m
        assert chance is not None
        stance = "atencao" if chance >= 0.65 else "favoravel" if chance < 0.35 else "neutra"
        headline = {
            "atencao": "Agro com pressão de alta",
            "neutra": "Agro sem direção clara",
            "favoravel": "Agro com folga",
        }[stance]
        text = (
            f"No cenário central o índice varia {mid}% {spec.horizon_label}, entre {low}% e "
            f"{high}% em 8 de cada 10 cenários. Chance de alta: {chance_text(chance)}."
        )
    hint = _PROFILE_HINT.get(profile or "", {}).get(kind, {}).get(stance)
    if hint:
        text = f"{text} {hint}"
    return View(stance=stance, headline=headline, text=text)


def specs_for(profile: str | None) -> tuple[Spec, ...]:
    return tuple(SPECS[k] for k in PROFILE_SPECS.get(profile or "", DEFAULT_SPECS))
