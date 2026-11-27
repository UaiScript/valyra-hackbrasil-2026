"""Coleta agendada do Alpha (ADR-0012): SGS do Banco Central, brapi.dev e Open-Meteo.

Uso: python -m valyra.scripts.ingest_alpha [--sources bcb,brapi,clima] [--backfill-days N]

Sem `--backfill-days`, lê os últimos 20 pontos de cada série (limite do SGS) e grava
como publicação o instante da coleta. Com ele, carrega o histórico usando publicação
reconstituída e marcada como estimada. Cada série é gravada na própria transação: uma
fonte fora do ar não descarta o que as outras trouxeram. O clima não tem carga histórica:
cada coleta grava a chuva dos últimos 30 dias e a comparação com os 10 anos anteriores.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from functools import partial

import httpx
from sqlalchemy.orm import Session

from valyra.alpha import service
from valyra.alpha.domain import (
    BUSINESS_ZONE,
    NORMAL_YEARS,
    RAIN_WINDOW_DAYS,
    REGIONS,
    SGS_SERIES,
    STOCK_SERIES,
    Region,
    Series,
    SgsFormatError,
    climate_pair,
    parse_decimal,
    parse_sgs,
    rain_reading,
)
from valyra.core.config import get_settings
from valyra.core.db import get_session_factory

logger = logging.getLogger("valyra.alpha.ingest")
SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
BRAPI_URL = "https://brapi.dev/api/quote/{ticker}"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
SOURCES = ("bcb", "brapi", "clima")
# O SGS recusa janelas diárias acima de 10 anos; fatias de 3 anos ficam bem abaixo.
SGS_WINDOW_DAYS = 365 * 3
# Teto da carga histórica: 10 anos cabem no limite do SGS e no tempo do workflow.
MAX_BACKFILL_DAYS = 3650
TIMEOUT = httpx.Timeout(20.0)


@dataclass(frozen=True)
class Observation:
    series: Series
    observation_date: date
    value: Decimal
    source_url: str


def _sgs_url(code: int, suffix: str = "") -> str:
    return SGS_URL.format(code=code) + suffix


def fetch_sgs(
    client: httpx.Client, series: Series, *, backfill_days: int | None, today: date
) -> list[Observation]:
    assert series.sgs_code is not None
    if backfill_days is None:
        windows = [(_sgs_url(series.sgs_code, "/ultimos/20"), {"formato": "json"})]
    else:
        windows = []
        start = today - timedelta(days=backfill_days)
        while start <= today:
            end = min(start + timedelta(days=SGS_WINDOW_DAYS), today)
            windows.append(
                (
                    _sgs_url(series.sgs_code),
                    {
                        "formato": "json",
                        "dataInicial": start.strftime("%d/%m/%Y"),
                        "dataFinal": end.strftime("%d/%m/%Y"),
                    },
                )
            )
            start = end + timedelta(days=1)
    found: list[Observation] = []
    for url, params in windows:
        response = client.get(url, params=params)
        response.raise_for_status()
        public_url = str(response.request.url)
        for day, value in parse_sgs(response.json()):
            found.append(Observation(series, day, value, public_url))
    return found


def fetch_brapi(client: httpx.Client, series: Series, *, token: str) -> list[Observation]:
    assert series.ticker is not None
    url = BRAPI_URL.format(ticker=series.ticker)
    response = client.get(url, params={"token": token} if token else None)
    response.raise_for_status()
    # parse_float=Decimal: a variação nunca passa por float.
    body = response.json(parse_float=Decimal)
    results = body.get("results") if isinstance(body, dict) else None
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        raise SgsFormatError("resposta da brapi sem resultados")
    quote = results[0]
    raw_time = str(quote.get("regularMarketTime", ""))
    try:
        moment = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
    except ValueError:
        raise SgsFormatError("horário da cotação inválido") from None
    if moment.tzinfo is None:
        raise SgsFormatError("horário da cotação sem fuso")
    value = parse_decimal(str(quote.get("regularMarketChangePercent", "")))
    # A URL pública não leva o token: ele é segredo do repositório.
    return [Observation(series, moment.astimezone(BUSINESS_ZONE).date(), value, url)]


def _daily_rain(body: object) -> dict[date, Decimal]:
    daily = body.get("daily") if isinstance(body, dict) else None
    if not isinstance(daily, dict):
        raise SgsFormatError("resposta do Open-Meteo sem bloco daily")
    days, values = daily.get("time"), daily.get("precipitation_sum")
    if not isinstance(days, list) or not isinstance(values, list) or len(days) != len(values):
        raise SgsFormatError("série diária do Open-Meteo inconsistente")
    rain: dict[date, Decimal] = {}
    for raw_day, raw_value in zip(days, values, strict=True):
        if raw_value is None:
            # Dia sem dado fica fora; a janela que precisar dele é descartada, não zerada.
            continue
        if not isinstance(raw_value, (Decimal, int)) or isinstance(raw_value, bool):
            raise SgsFormatError("chuva do Open-Meteo não numérica")
        rain[date.fromisoformat(str(raw_day))] = Decimal(raw_value)
    return rain


def _coordinates(region: Region) -> dict[str, str]:
    return {
        "latitude": str(region.latitude),
        "longitude": str(region.longitude),
        "daily": "precipitation_sum",
        "timezone": "America/Sao_Paulo",
    }


def fetch_climate(client: httpx.Client, region: Region, *, today: date) -> list[Observation]:
    """Chuva de 30 dias até ontem e anomalia contra a mesma janela nos 10 anos anteriores."""
    end = today - timedelta(days=1)
    # O arquivo histórico (ERA5) chega com dias de atraso; a janela recente vem do
    # endpoint de previsão, que também devolve dias passados.
    recent = client.get(
        FORECAST_URL,
        params=_coordinates(region) | {"past_days": RAIN_WINDOW_DAYS + 1, "forecast_days": 1},
    )
    recent.raise_for_status()
    start = end.replace(year=end.year - NORMAL_YEARS) - timedelta(days=RAIN_WINDOW_DAYS + 1)
    archive = client.get(
        ARCHIVE_URL,
        params=_coordinates(region)
        | {"start_date": start.isoformat(), "end_date": end.replace(year=end.year - 1).isoformat()},
    )
    archive.raise_for_status()
    reading = rain_reading(
        _daily_rain(recent.json(parse_float=Decimal)),
        _daily_rain(archive.json(parse_float=Decimal)),
        end,
    )
    if reading is None:
        raise SgsFormatError("janela de chuva incompleta")
    rain_series, anomaly_series = climate_pair(region)
    url = str(recent.request.url)
    found = [Observation(rain_series, end, reading.total_mm, url)]
    if reading.anomaly_pct is not None:
        archive_url = str(archive.request.url)
        found.append(Observation(anomaly_series, end, reading.anomaly_pct, archive_url))
    return found


def ingest(
    session_factory: Callable[[], Session],
    client: httpx.Client,
    *,
    backfill_days: int | None = None,
    token: str = "",
    sources: tuple[str, ...] = SOURCES,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, int | str]:
    """Coleta cada série e grava as revisões novas; devolve gravadas ou o erro por série."""
    today = now().astimezone(BUSINESS_ZONE).date()
    report: dict[str, int | str] = {}
    # Cada tarefa coleta um grupo de séries; uma falha marca todas as séries do grupo.
    tasks: list[tuple[tuple[Series, ...], Callable[[], list[Observation]]]] = []
    if "bcb" in sources:
        for series in SGS_SERIES:
            tasks.append(
                (
                    (series,),
                    partial(fetch_sgs, client, series, backfill_days=backfill_days, today=today),
                )
            )
    if "brapi" in sources:
        for series in STOCK_SERIES:
            tasks.append(((series,), partial(fetch_brapi, client, series, token=token)))
    if "clima" in sources:
        for region in REGIONS:
            tasks.append(
                (climate_pair(region), partial(fetch_climate, client, region, today=today))
            )
    for group, fetch in tasks:
        try:
            observations = fetch()
        except (httpx.HTTPError, SgsFormatError, ValueError) as error:
            for series in group:
                logger.warning("Falha ao coletar %s: %s", series.key, type(error).__name__)
                report[series.key] = f"erro: {type(error).__name__}"
            continue
        ingested_at = now()
        with session_factory() as session:
            try:
                written = {series.key: 0 for series in group}
                for item in observations:
                    written[item.series.key] += service.record_observation(
                        session,
                        item.series,
                        item.observation_date,
                        item.value,
                        ingested_at=ingested_at,
                        source_url=item.source_url,
                        backfill=backfill_days is not None and item.series.theme != "clima",
                    )
                session.commit()
            except BaseException:
                session.rollback()
                raise
        report.update(written)
    return report


def _backfill_days(text: str) -> int:
    days = int(text)
    if not 1 <= days <= MAX_BACKFILL_DAYS:
        raise argparse.ArgumentTypeError(f"use de 1 a {MAX_BACKFILL_DAYS} dias")
    return days


def _sources(text: str) -> tuple[str, ...]:
    chosen = tuple(part.strip() for part in text.split(",") if part.strip())
    if not chosen or any(part not in SOURCES for part in chosen):
        raise argparse.ArgumentTypeError(f"use uma ou mais de: {', '.join(SOURCES)}")
    return chosen


def exit_code(report: dict[str, int | str]) -> int:
    """1 quando uma fonte inteira falhou: o agendamento fica vermelho e alguém vê."""
    by_source: dict[str, list[bool]] = {}
    for key, result in report.items():
        by_source.setdefault(key.split(":", 1)[0], []).append(isinstance(result, str))
    return 1 if any(all(failed) for failed in by_source.values()) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--backfill-days", type=_backfill_days, default=None)
    parser.add_argument(
        "--sources",
        type=_sources,
        default=SOURCES,
        help="Fontes separadas por vírgula: bcb, brapi, clima (padrão: todas)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = get_settings()
    with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": "valyra-alpha-ingest"}) as client:
        report = ingest(
            get_session_factory(),
            client,
            backfill_days=args.backfill_days,
            token=settings.brapi_token.get_secret_value(),
            sources=args.sources,
        )
    for key, result in report.items():
        logger.info("%s: %s", key, result)
        if isinstance(result, str) and os.environ.get("GITHUB_ACTIONS") == "true":
            # Anotação visível no resumo do workflow, mesmo quando o job termina verde.
            print(f"::warning title=Coleta Alpha::{key}: {result}")
    return exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
