"""Coleta agendada das notícias do relatório semanal (proposta da ADR-0013).

Uso: python -m valyra.scripts.ingest_news

Lê o feed de cada fonte de NEWS_SOURCES e grava só as notícias novas. Cada fonte é gravada
na própria transação: uma fonte fora do ar não descarta o que as outras trouxeram.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from valyra.alpha import news_service
from valyra.alpha.news import (
    MAX_FEED_BYTES,
    NEWS_SOURCES,
    FeedFormatError,
    FeedItem,
    NewsSource,
    parse_ibge,
    parse_rss,
)
from valyra.core.db import get_session_factory

logger = logging.getLogger("valyra.alpha.news")
TIMEOUT = httpx.Timeout(20.0)
# Poucos itens por fonte bastam para a semana: a coleta roda várias vezes ao dia.
IBGE_PARAMS = {"qtd": "40"}


DB_ERROR = "erro de banco"


def _same_source(source: NewsSource, host: str) -> bool:
    # Redirecionamento só vale dentro do domínio da própria fonte (http→https, www).
    # Confere só a resposta final: saltos intermediários já foram requisitados, o que é
    # aceitável porque as URLs de feed são fixas no código, não vêm de usuário.
    host = host.lower()
    return host == source.domain or host.endswith(f".{source.domain}")


def fetch(client: httpx.Client, source: NewsSource) -> list[FeedItem]:
    params = IBGE_PARAMS if source.format == "ibge_json" else None
    with client.stream("GET", source.feed_url, params=params) as response:
        response.raise_for_status()
        if not _same_source(source, response.url.host):
            raise FeedFormatError("feed redirecionado para fora do domínio da fonte")
        # Lido em pedaços com teto: um corpo enorme é recusado sem ir inteiro para a memória.
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > MAX_FEED_BYTES:
                raise FeedFormatError("feed acima do tamanho máximo")
            chunks.append(chunk)
    body = b"".join(chunks)
    if source.format == "ibge_json":
        try:
            return parse_ibge(source.slug, json.loads(body))
        except ValueError:
            raise FeedFormatError("JSON inválido") from None
    return parse_rss(source.slug, body)


def ingest(
    session_factory: Callable[[], Session],
    client: httpx.Client,
    *,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    sources: tuple[NewsSource, ...] = NEWS_SOURCES,
) -> dict[str, int | str]:
    """Coleta cada fonte e grava as notícias novas; devolve gravadas ou o erro por fonte."""
    report: dict[str, int | str] = {}
    for source in sources:
        try:
            items = fetch(client, source)
        except (httpx.HTTPError, FeedFormatError, ValueError) as error:
            logger.warning("Falha ao coletar %s: %s", source.slug, type(error).__name__)
            report[source.slug] = f"erro: {type(error).__name__}"
            continue
        ingested_at = now()
        with session_factory() as session:
            try:
                written = sum(
                    news_service.record_news(session, item, ingested_at=ingested_at)
                    for item in items
                )
                session.commit()
            except SQLAlchemyError as error:
                # Falha de banco numa fonte não impede as próximas; o relatório registra o erro.
                session.rollback()
                logger.warning("Falha ao gravar %s: %s", source.slug, type(error).__name__)
                report[source.slug] = f"{DB_ERROR}: {type(error).__name__}"
                continue
            except BaseException:
                session.rollback()
                raise
        report[source.slug] = written
    return report


def exit_code(report: dict[str, int | str]) -> int:
    """1 quando todas as fontes falharam ou o banco falhou em alguma.

    Uma fonte fora do ar não deixa o job vermelho; erro de banco é nosso e precisa de alerta.
    """
    results = list(report.values())
    if any(isinstance(result, str) and result.startswith(DB_ERROR) for result in results):
        return 1
    return 1 if results and all(isinstance(result, str) for result in results) else 0


def main(argv: list[str] | None = None) -> int:
    del argv
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    with httpx.Client(
        timeout=TIMEOUT, headers={"User-Agent": "valyra-news-ingest"}, follow_redirects=True
    ) as client:
        report = ingest(get_session_factory(), client)
    for key, result in report.items():
        logger.info("%s: %s", key, result)
        if isinstance(result, str) and os.environ.get("GITHUB_ACTIONS") == "true":
            print(f"::warning title=Coleta de notícias::{key}: {result}")
    return exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
