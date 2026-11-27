"""Relatório semanal de notícias com banco real: coleta simulada, corte as_of e IA."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from valyra.alpha import news_service
from valyra.alpha.news import FeedItem
from valyra.scripts import ingest_news

pytestmark = pytest.mark.postgres
URL = "/api/v1/alpha/news/weekly"
FIXTURE = Path(__file__).parent / "fixtures" / "news_rss.xml"
# Coleta logo depois da última manchete do fixture (25/11 21h30 em Brasília).
COLLECTED = datetime(2026, 11, 26, 12, tzinfo=UTC)


def _transport(request: httpx.Request) -> httpx.Response:
    if request.url.host == "agenciabrasil.ebc.com.br":
        return httpx.Response(200, content=FIXTURE.read_bytes())
    if request.url.host == "servicodados.ibge.gov.br":
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "titulo": "Inflação de outubro desacelera",
                        "introducao": "IPCA divulgado pelo IBGE.",
                        "link": "https://agenciadenoticias.ibge.gov.br/teste-ipca",
                        "data_publicacao": "25/11/2026 09:00:00",
                    }
                ]
            },
        )
    return httpx.Response(503, text="manutenção")


def _ingest(test_engine, now=COLLECTED):
    from sqlalchemy.orm import Session

    def factory():
        return Session(test_engine, expire_on_commit=False)

    with httpx.Client(transport=httpx.MockTransport(_transport)) as http:
        return ingest_news.ingest(factory, http, now=lambda: now)


def test_coleta_tolera_fonte_fora_do_ar_e_nao_duplica(db_session, test_engine):
    report = _ingest(test_engine)
    assert report == {"agencia-brasil": 3, "bcb-notas": "erro: HTTPStatusError", "ibge-noticias": 1}
    assert ingest_news.exit_code(report) == 0
    again = _ingest(test_engine, COLLECTED + timedelta(hours=6))
    assert again["agencia-brasil"] == 0 and again["ibge-noticias"] == 0
    assert ingest_news.exit_code({"a": "erro: X", "b": "erro: Y"}) == 1


def test_relatorio_agrupa_por_tema_com_fonte_e_respeita_corte(client, db_session, test_engine):
    _ingest(test_engine)
    body = client.get(URL, params={"as_of": COLLECTED.isoformat()}).json()
    assert body["rule"] == "news_theme_v2"
    assert body["total_items"] == 4 and body["unmatched_items"] == 1
    themes = {theme["key"]: theme for theme in body["themes"]}
    assert set(themes) == {"juros", "inflacao", "combustiveis"}
    assert themes["combustiveis"]["category_slugs"] == ["transporte"]
    [selic] = themes["juros"]["items"]
    assert selic["source"]["slug"] == "agencia-brasil"
    assert selic["url"] == "https://agenciabrasil.ebc.com.br/economia/noticia/teste-copom"
    assert selic["published_at"].startswith("2026-11-26T00:30:00")
    assert selic["image_url"] == "https://imagens.ebc.com.br/teste/copom.jpg"
    assert selic["image_credit"] == "Fotógrafo/Agência Brasil"
    assert body["last_ingested_at"].startswith("2026-11-26T12:00:00")

    # Antes da reunião do Copom ser publicada, a manchete não existe para o relatório.
    early = client.get(URL, params={"as_of": "2026-11-25T12:00:00-03:00"}).json()
    assert "juros" not in {theme["key"] for theme in early["themes"]}
    assert early["total_items"] == 3


def test_notícia_com_data_futura_fica_presa_a_coleta(db_session):
    item = FeedItem(
        "agencia-brasil", "Selic em debate", "", "https://agenciabrasil.ebc.com.br/x",
        COLLECTED + timedelta(days=2),
    )  # fmt: skip
    assert news_service.record_news(db_session, item, ingested_at=COLLECTED)
    db_session.flush()
    report = news_service.get_weekly_report(db_session, COLLECTED)
    [view] = report.themes[0].items
    assert view.published_at == COLLECTED


def test_as_of_sem_fuso_e_recusado(client):
    assert client.get(URL, params={"as_of": "2026-11-10T12:00:00"}).status_code == 422
