"""Coleta agendada do Alpha (ADR-0012): SGS do Banco Central e brapi.dev.

Uso: python -m valyra.scripts.ingest_alpha [--backfill-days N]

Sem `--backfill-days`, lê os últimos 20 pontos de cada série (limite do SGS) e grava
como publicação o instante da coleta. Com ele, carrega o histórico usando publicação
reconstituída e marcada como estimada. Cada série é gravada na própria transação: uma
fonte fora do ar não descarta o que as outras trouxeram.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import httpx
from sqlalchemy.orm import Session

from valyra.alpha import service
from valyra.alpha.domain import (
    BUSINESS_ZONE,
    SGS_SERIES,
    STOCK_SERIES,
    Series,
    SgsFormatError,
    parse_decimal,
    parse_sgs,
)
from valyra.core.config import get_settings
from valyra.core.db import get_session_factory

logger = logging.getLogger("valyra.alpha.ingest")
SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
BRAPI_URL = "https://brapi.dev/api/quote/{ticker}"
# O SGS recusa janelas diárias acima de 10 anos; fatias de 3 anos ficam bem abaixo.
SGS_WINDOW_DAYS = 365 * 3
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
    if not results:
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


def ingest(
    session_factory: Callable[[], Session],
    client: httpx.Client,
    *,
    backfill_days: int | None = None,
    token: str = "",
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, int | str]:
    """Coleta cada série e grava as revisões novas; devolve gravadas ou o erro por série."""
    today = now().astimezone(BUSINESS_ZONE).date()
    report: dict[str, int | str] = {}
    for series in (*SGS_SERIES, *STOCK_SERIES):
        try:
            if series.sgs_code is not None:
                observations = fetch_sgs(client, series, backfill_days=backfill_days, today=today)
            else:
                observations = fetch_brapi(client, series, token=token)
        except (httpx.HTTPError, SgsFormatError, ValueError) as error:
            logger.warning("Falha ao coletar %s: %s", series.key, type(error).__name__)
            report[series.key] = f"erro: {type(error).__name__}"
            continue
        ingested_at = now()
        with session_factory() as session:
            try:
                written = sum(
                    service.record_observation(
                        session,
                        item.series,
                        item.observation_date,
                        item.value,
                        ingested_at=ingested_at,
                        source_url=item.source_url,
                        backfill=backfill_days is not None,
                    )
                    for item in observations
                )
                session.commit()
            except BaseException:
                session.rollback()
                raise
        report[series.key] = written
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--backfill-days", type=int, default=None)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = get_settings()
    with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": "valyra-alpha-ingest"}) as client:
        report = ingest(
            get_session_factory(),
            client,
            backfill_days=args.backfill_days,
            token=settings.brapi_token.get_secret_value(),
        )
    for key, result in report.items():
        logger.info("%s: %s", key, result)
    # Falha só quando nada foi coletado: uma fonte instável não derruba o agendamento.
    return 1 if all(isinstance(result, str) for result in report.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
