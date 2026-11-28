"""Previsões por perfil (ADR-0016): lê as séries coletadas no corte e chama o domínio.

Cada série usa o histórico coletado quando ele basta para o modelo; se não basta (coleta
recém-ligada, fonte fora do ar), entra a série de reserva sintética, sempre marcada. O
resultado fica em memória por alguns minutos: a conta é barata, mas a demo não precisa
refazê-la a cada clique, e o LLM nunca é chamado aqui.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from valyra.alpha import forecast, repository
from valyra.alpha.domain import BUSINESS_ZONE, FORECAST_SGS_SERIES, SGS_SERIES, STOCK_SERIES
from valyra.alpha.forecast import METHOD_VERSION
from valyra.alpha.forecast_reserve import reserve_series
from valyra.alpha.models import Source

# Pontos lidos por série: anos de Selic diária viram meses; ações e dólar bastam em um ano.
_READ_LIMIT = {
    forecast.SELIC_KEY: 2200,
    forecast.CDI_KEY: 1600,
    forecast.IPCA_KEY: 120,
    forecast.AGRO_KEY: 120,
    forecast.DOLLAR_KEY: 400,
    **dict.fromkeys(forecast.STOCK_KEYS, 300),
}
_SERIES = {s.key: s for s in SGS_SERIES + FORECAST_SGS_SERIES + STOCK_SERIES}
_RESERVE_SOURCE = {
    "slug": "valyra-reserva",
    "name": "Série de reserva sintética da Valyra",
    "url": "https://github.com/UaiScript/valyra-hackbrasil-2026",
    "license": "Dados sintéticos de demonstração; não são dados reais",
}
CACHE_SECONDS = 600
# Versão do método, para outros módulos (IA) citarem sem importar o domínio.
FORECAST_METHOD_VERSION = METHOD_VERSION


@dataclass(frozen=True)
class InputSeries:
    """Procedência de uma série de entrada, para a tela e para a IA."""

    key: str
    title: str
    origin: forecast.DataOrigin
    source_slug: str
    source_name: str
    source_url: str
    license: str
    observations: int
    first_day: date
    last_day: date
    last_published_at: datetime | None
    last_ingested_at: datetime | None
    published_at_estimated: bool
    # Última revisão visível, citada pela IA como dependência do cálculo.
    last_signal_id: UUID | None
    last_signal_key: str | None
    last_revision_id: int | None
    source_id: UUID | None


@dataclass(frozen=True)
class ProfileForecasts:
    profile: str | None
    as_of: datetime
    computed_at: datetime
    items: list[tuple[forecast.Forecast, list[InputSeries]]]


def _min_raw_points(key: str) -> int:
    """Quantos pontos brutos a série precisa para o modelo da previsão que a usa."""
    if key in (forecast.SELIC_KEY,):
        return 24 * 20  # meses completos vindos de dias corridos
    if key == forecast.CDI_KEY:
        return 25 * 19
    if key in (forecast.IPCA_KEY, forecast.AGRO_KEY):
        return 25
    if key == forecast.DOLLAR_KEY:
        return 61
    return 41


def _load(session: Session, key: str, as_of: datetime) -> tuple[list, Source | None]:
    rows = repository.list_visible(session, key, as_of, _READ_LIMIT[key])
    return [signal for signal, _ in reversed(rows)], (rows[0][1] if rows else None)


def _monthly_ok(points: list[forecast.Observation]) -> bool:
    return len(points) >= 24


def _prepare(key: str, raw: list[forecast.Observation], as_of_day: date):
    if key == forecast.SELIC_KEY:
        return forecast.monthly_last(raw)
    if key == forecast.CDI_KEY:
        monthly = forecast.monthly_mean(
            [forecast.Observation(p.day, forecast.cdi_annualized(p.value)) for p in raw]
        )
        return forecast.complete_months(monthly, raw[-1].day if raw else as_of_day)
    return raw


def _series_input(
    session: Session, key: str, as_of: datetime
) -> tuple[list[forecast.Observation], InputSeries]:
    rows, source = _load(session, key, as_of)
    raw = [forecast.Observation(r.observation_date, float(r.value)) for r in rows]
    as_of_day = as_of.astimezone(BUSINESS_ZONE).date()
    prepared = _prepare(key, raw, as_of_day) if raw else []
    enough = len(raw) >= _min_raw_points(key) and (
        key in (forecast.DOLLAR_KEY, *forecast.STOCK_KEYS) or _monthly_ok(prepared)
    )
    title = _SERIES[key].title if key in _SERIES else key
    if enough and source is not None:
        last = rows[-1]
        return prepared, InputSeries(
            key=key,
            title=title,
            origin="coleta",
            source_slug=source.slug,
            source_name=source.name,
            source_url=last.source_url,
            license=source.license,
            observations=len(raw),
            first_day=raw[0].day,
            last_day=raw[-1].day,
            last_published_at=max(r.published_at for r in rows),
            last_ingested_at=max(r.ingested_at for r in rows if r.ingested_at <= as_of)
            if any(r.ingested_at <= as_of for r in rows)
            else None,
            published_at_estimated=any(r.published_at_estimated for r in rows),
            last_signal_id=last.id,
            last_signal_key=last.signal_key,
            last_revision_id=last.revision_id,
            source_id=source.id,
        )
    return _reserve_input(key, as_of_day, title)


def _reserve_input(
    key: str, as_of_day: date, title: str
) -> tuple[list[forecast.Observation], InputSeries]:
    reserve = reserve_series(key, as_of_day)
    return _prepare(key, reserve, as_of_day), InputSeries(
        key=key,
        title=title,
        origin="reserva",
        source_slug=_RESERVE_SOURCE["slug"],
        source_name=_RESERVE_SOURCE["name"],
        source_url=_RESERVE_SOURCE["url"],
        license=_RESERVE_SOURCE["license"],
        observations=len(reserve),
        first_day=reserve[0].day,
        last_day=reserve[-1].day,
        last_published_at=None,
        last_ingested_at=None,
        published_at_estimated=False,
        last_signal_id=None,
        last_signal_key=None,
        last_revision_id=None,
        source_id=None,
    )


# Uma entrada por perfil (três mais o padrão): o tamanho é fixo e cada uma expira sozinha.
_cache: dict[str | None, tuple[float, ProfileForecasts]] = {}
_lock = threading.Lock()


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def get_forecasts(
    session: Session,
    profile: str | None,
    as_of: datetime,
    *,
    now: datetime,
    use_cache: bool = True,
) -> ProfileForecasts:
    """Previsões do perfil com o que era conhecido no corte; nada publicado depois entra.

    O cache só vale para o corte "agora" e guarda o `as_of` efetivo do cálculo, que a rota
    devolve. Quem precisa do corte exato (a IA) passa `use_cache=False`.
    """
    # Só o corte "agora" vai para o cache: um as_of histórico arbitrário criaria uma entrada
    # por valor e a memória cresceria sem limite.
    live = use_cache and as_of >= now
    if live:
        with _lock:
            hit = _cache.get(profile)
        if hit and hit[0] > time.monotonic():
            return hit[1]
    specs = forecast.specs_for(profile)
    needed = list(dict.fromkeys(k for spec in specs for k in spec.inputs))
    base: dict[str, list[forecast.Observation]] = {}
    inputs: dict[str, InputSeries] = {}
    for series_key in needed:
        base[series_key], inputs[series_key] = _series_input(session, series_key, as_of)
    stocks = [k for k in forecast.STOCK_KEYS if k in inputs]
    if any(inputs[k].origin == "reserva" for k in stocks):
        # A cesta só usa dias em que todas as ações têm dado: misturar coleta e reserva
        # deixaria quase nenhum dia em comum. Sem histórico de todas, a cesta inteira é reserva.
        day = as_of.astimezone(BUSINESS_ZONE).date()
        for k in stocks:
            if inputs[k].origin == "coleta":
                base[k], inputs[k] = _reserve_input(k, day, inputs[k].title)
    items = []
    for spec in specs:
        spec_inputs = [inputs[k] for k in spec.inputs]
        items.append((forecast.compute(spec, base, profile), spec_inputs))
    result = ProfileForecasts(profile=profile, as_of=as_of, computed_at=now, items=items)
    if live:
        with _lock:
            _cache[profile] = (time.monotonic() + CACHE_SECONDS, result)
    return result
