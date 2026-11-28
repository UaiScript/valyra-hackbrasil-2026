"""Previsões por perfil com banco real (ADR-0016): coleta, reserva e corte as_of."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from valyra.alpha import service
from valyra.alpha.domain import SGS_SERIES
from valyra.alpha.forecast import add_months

pytestmark = pytest.mark.postgres
URL = "/api/v1/alpha/forecasts"
IPCA = SGS_SERIES[2]
T0 = datetime(2026, 11, 10, 12, tzinfo=UTC)
SOURCE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados"


def seed_ipca(session, months: int = 36) -> None:
    first = date(2023, 9, 1)
    for i in range(months):
        value = Decimal("0.30") + Decimal(i % 5) / 10
        service.record_observation(
            session, IPCA, add_months(first, i), value,
            ingested_at=T0, source_url=SOURCE, backfill=True,
        )  # fmt: skip
    session.commit()


def test_sem_coleta_usa_reserva_marcada_para_cada_previsao_do_perfil(client):
    body = client.get(URL, params={"profile": "investidor"}).json()
    assert [i["key"] for i in body["items"]] == ["acoes_1m", "dolar_1m", "selic_6m", "agro_6m"]
    for item in body["items"]:
        assert item["data_origin"] == "reserva"
        assert "reserva sintética" in item["limitations"][0]
        assert item["inputs"][0]["source"]["slug"] == "valyra-reserva"
        band = item["headline"]
        assert Decimal(band["p10"]) <= Decimal(band["p50"]) <= Decimal(band["p90"])
        assert item["view"]["rule"] == "forecast_view_v1"
    assert any("sem IA" in note for note in body["notes"])


def test_historico_coletado_substitui_a_reserva_e_respeita_o_corte(client, db_session):
    seed_ipca(db_session)
    now = client.get(URL, params={"profile": "orcamento-apertado"}).json()
    ipca = next(i for i in now["items"] if i["key"] == "ipca_12m")
    assert ipca["data_origin"] == "coleta"
    [series] = ipca["inputs"]
    assert series["observations"] == 36 and series["published_at_estimated"] is True
    assert series["last_day"] == "2026-08-01"
    assert ipca["chance"]["event_label"].startswith("passar do teto")
    assert any("data de publicação estimada" in text for text in ipca["limitations"])

    # Em 01/01/2026 só os meses publicados até ali eram conhecidos: poucos para o modelo,
    # então a previsão volta para a reserva em vez de usar o que veio depois.
    early = client.get(
        URL, params={"profile": "orcamento-apertado", "as_of": "2025-01-01T12:00:00-03:00"}
    ).json()
    old = next(i for i in early["items"] if i["key"] == "ipca_12m")
    assert old["data_origin"] == "reserva"


def test_perfil_desconhecido_e_recusado(client):
    assert client.get(URL, params={"profile": "cooperado"}).status_code == 422
