"""Radar Alpha com banco real: corte as_of, revisões e coleta simulada."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from valyra.alpha import service
from valyra.alpha.domain import SGS_SERIES, STOCK_SERIES
from valyra.scripts import ingest_alpha

pytestmark = pytest.mark.postgres
URL = "/api/v1/alpha/radar"
SELIC, CDI, IPCA = SGS_SERIES
T0 = datetime(2026, 11, 10, 12, tzinfo=UTC)


def record(session, series, day, value, ingested_at, **kw):
    return service.record_observation(
        session, series, day, Decimal(value), ingested_at=ingested_at,
        source_url="https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados", **kw,
    )  # fmt: skip


def test_radar_respeita_corte_e_revisoes(client, db_session):
    record(db_session, IPCA, date(2026, 9, 1), "0.48", T0)
    record(db_session, IPCA, date(2026, 10, 1), "0.09", T0 + timedelta(days=2))
    # Revisão do mesmo mês publicada depois: só aparece com corte posterior.
    record(db_session, IPCA, date(2026, 10, 1), "0.10", T0 + timedelta(days=5))
    db_session.commit()

    early = client.get(URL, params={"as_of": (T0 + timedelta(hours=1)).isoformat()}).json()
    [ipca] = early["indicators"]
    assert ipca["latest"]["value"] == "0.48" and ipca["previous"] is None
    assert early["signals"] == []

    middle = client.get(URL, params={"as_of": (T0 + timedelta(days=3)).isoformat()}).json()
    latest = middle["indicators"][0]["latest"]
    assert (latest["value"], latest["revision_id"]) == ("0.09", 1)
    assert middle["signals"][0]["title"] == "IPCA de outubro de 2026 abaixo do mês anterior"

    now = client.get(URL).json()["indicators"][0]["latest"]
    assert (now["value"], now["revision_id"]) == ("0.1", 2)


def test_valor_repetido_nao_grava_nova_revisao(db_session):
    assert record(db_session, SELIC, date(2026, 11, 3), "15", T0)
    assert not record(db_session, SELIC, date(2026, 11, 3), "15.00", T0 + timedelta(hours=1))


def test_carga_historica_marca_publicacao_estimada(client, db_session):
    record(db_session, IPCA, date(2026, 9, 1), "0.48", T0, backfill=True)
    db_session.commit()
    latest = client.get(URL).json()["indicators"][0]["latest"]
    assert latest["published_at_estimated"] is True
    assert latest["published_at"].startswith("2026-10-31T15:00:00")


def test_signals_e_somente_insercao(db_session):
    record(db_session, SELIC, date(2026, 11, 3), "15", T0)
    db_session.commit()
    with pytest.raises(DBAPIError):
        db_session.execute(text("UPDATE signals SET title = 'x'"))
    db_session.rollback()


def test_as_of_sem_fuso_e_recusado(client):
    assert client.get(URL, params={"as_of": "2026-11-10T12:00:00"}).status_code == 422


def _open_meteo(request: httpx.Request) -> httpx.Response:
    from datetime import date as day_type

    params = request.url.params
    if request.url.host == "api.open-meteo.com":
        end = T0.date()
        start = end - timedelta(days=int(params["past_days"]))
        value = "1.0"
    else:
        start = day_type.fromisoformat(params["start_date"])
        end = day_type.fromisoformat(params["end_date"])
        value = "2.0"
    days = [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]
    # Texto cru com literais decimais: a chuva também não passa por float.
    rain = ",".join(value for _ in days)
    times = ",".join(f'"{d}"' for d in days)
    return httpx.Response(
        200, text=f'{{"daily":{{"time":[{times}],"precipitation_sum":[{rain}]}}}}'
    )


def _transport(request: httpx.Request) -> httpx.Response:
    if "open-meteo" in request.url.host:
        return _open_meteo(request)
    if request.url.host == "api.bcb.gov.br":
        code = request.url.path.split("bcdata.sgs.")[1].split("/")[0]
        if code == "12":
            return httpx.Response(503, text="manutenção")
        value = {"432": "15.00", "433": "0,09", "1": "5,3712", "27575": "301,25"}[code]
        return httpx.Response(200, json=[{"data": "01/11/2026", "valor": value}])
    ticker = request.url.path.rsplit("/", 1)[1]
    assert "token" not in request.url.params
    return httpx.Response(
        200,
        # Texto cru: o número precisa chegar como literal JSON, sem passar por float.
        text=f'{{"results":[{{"symbol":"{ticker}","regularMarketChangePercent":-1.2345,'
        '"regularMarketTime":"2026-11-27T20:07:00.000Z"}]}',
    )


def test_coleta_grava_series_e_tolera_fonte_fora_do_ar(client, db_session, test_engine):
    from sqlalchemy.orm import Session

    def factory():
        return Session(test_engine, expire_on_commit=False)

    with httpx.Client(transport=httpx.MockTransport(_transport)) as http:
        report = ingest_alpha.ingest(factory, http, now=lambda: T0)
    assert report[CDI.key].startswith("erro")
    assert report[SELIC.key] == 1 and report[STOCK_SERIES[0].key] == 1
    # Séries só das previsões (ADR-0016) entram na coleta, mas não no radar.
    assert report["bcb:sgs:1"] == 1 and report["bcb:sgs:27575"] == 1
    radar = client.get(URL).json()
    values = {i["key"]: i["latest"]["value"] for i in radar["indicators"]}
    # A variação da brapi chega como texto decimal exato, sem passar por float.
    assert values[STOCK_SERIES[0].key] == "-1.2345"
    assert values[IPCA.key] == "0.09"
    assert radar["last_ingested_at"].startswith("2026-11-10T12:00:00")


def test_prefixo_da_serie_e_literal_no_like(db_session):
    from valyra.alpha import repository

    petr4 = STOCK_SERIES[0]
    record(db_session, petr4, date(2026, 11, 3), "-1.5", T0)
    # Sem escape, "_" de "change_pct" casaria com qualquer caractere e traria esta chave.
    impostor = service.Series(**{**petr4.__dict__, "key": petr4.key.replace("_", "X")})
    record(db_session, impostor, date(2026, 11, 3), "9", T0)
    rows = repository.list_visible(db_session, petr4.key, T0, 30)
    assert [signal.signal_key for signal, _ in rows] == [f"{petr4.key}:2026-11-03"]


def test_clima_gera_chuva_anomalia_sinal_e_status_da_fonte(client, db_session, test_engine):
    from sqlalchemy.orm import Session

    from valyra.alpha.domain import REGIONS, climate_pair

    def factory():
        return Session(test_engine, expire_on_commit=False)

    with httpx.Client(transport=httpx.MockTransport(_transport)) as http:
        report = ingest_alpha.ingest(factory, http, now=lambda: T0, sources=("clima",))
    rain, anomaly = climate_pair(REGIONS[0])
    assert report[rain.key] == 1 and report[anomaly.key] == 1
    assert SELIC.key not in report
    radar = client.get(URL).json()
    by_key = {i["key"]: i for i in radar["indicators"]}
    assert by_key[rain.key]["latest"]["value"] == "30"
    assert by_key[anomaly.key]["latest"]["value"] == "-50"
    assert by_key[rain.key]["theme"] == "clima"
    assert by_key[rain.key]["region"]["name"] == "Sorriso (MT)"
    dry = [s for s in radar["signals"] if s["rule"] == "climate_dry_spell_v1"]
    assert len(dry) == len(REGIONS)
    assert dry[0]["limitations"] and dry[0]["evidence_keys"]
    [status] = radar["sources"]
    assert status["source"]["slug"] == "open-meteo" and status["series_count"] == 6
