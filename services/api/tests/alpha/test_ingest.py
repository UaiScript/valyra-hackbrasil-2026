"""Script de coleta Alpha sem banco: código de saída, argumentos e resposta malformada."""

import httpx
import pytest

from valyra.alpha.domain import STOCK_SERIES, SgsFormatError
from valyra.scripts.ingest_alpha import exit_code, fetch_brapi, main


def test_codigo_de_saida_falha_quando_uma_fonte_inteira_cai():
    ok = {"bcb:sgs:432": 1, "bcb:sgs:12": "erro: HTTPStatusError", "brapi:PETR4:change_pct": 0}
    assert exit_code(ok) == 0
    sgs_down = {"bcb:sgs:432": "erro: X", "bcb:sgs:12": "erro: X", "brapi:PETR4:change_pct": 1}
    assert exit_code(sgs_down) == 1


@pytest.mark.parametrize("days", ["0", "-5", "3651"])
def test_carga_historica_fora_da_faixa_e_recusada(days):
    with pytest.raises(SystemExit):
        main(["--backfill-days", days])


@pytest.mark.parametrize("body", [{"results": ["PETR4"]}, {"results": {}}, ["x"], {"results": []}])
def test_resposta_brapi_malformada_vira_erro_de_formato(body):
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body)))
    with pytest.raises(SgsFormatError):
        fetch_brapi(client, STOCK_SERIES[0], token="")


def test_brapi_historico_decimal_ordena_deduplica_e_usa_fallback():
    import json
    from datetime import UTC, datetime
    from decimal import Decimal

    def epoch(day):
        return int(datetime(2026, 11, day, 20, tzinfo=UTC).timestamp())

    payload = {
        "results": [
            {
                "historicalDataPrice": [
                    {"date": epoch(3), "adjustedClose": None, "close": 121},
                    {"date": epoch(1), "adjustedClose": 100, "close": 100},
                    {"date": epoch(2), "adjustedClose": 105, "close": 105},
                    {"date": epoch(2), "adjustedClose": 110, "close": 105},
                ]
            }
        ]
    }

    def transport(req):
        assert req.url.params["range"] == "3mo" and req.url.params["interval"] == "1d"
        return httpx.Response(200, content=json.dumps(payload))

    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        rows = fetch_brapi(client, STOCK_SERIES[-1], token="fake", backfill_days=90)
    assert [r.value for r in rows] == [Decimal("10.0000"), Decimal("10.0000")]
    assert all("token" not in r.source_url for r in rows)


def test_sem_token_ignora_slce3_sem_warning(monkeypatch, caplog):
    from datetime import UTC, datetime
    from unittest.mock import MagicMock

    from valyra.scripts import ingest_alpha as script

    requested = []

    def fetch(_client, series, **_kwargs):
        requested.append(series.ticker)
        return []

    monkeypatch.setattr(script, "fetch_brapi", fetch)
    factory = MagicMock()
    report = script.ingest(
        factory,
        MagicMock(),
        token="  ",
        sources=("brapi",),
        now=lambda: datetime(2026, 11, 28, tzinfo=UTC),
    )
    assert requested == ["PETR4", "VALE3", "ITUB4", "MGLU3"]
    assert all(isinstance(v, int) for v in report.values())
    assert not caplog.records


def test_clima_backfill_completa_90_dias_com_duas_chamadas():
    from datetime import date, timedelta

    from valyra.alpha.domain import REGIONS
    from valyra.scripts.ingest_alpha import fetch_climate

    today = date(2026, 11, 28)
    calls = []

    def transport(req):
        calls.append(req)
        recent = req.url.host == "api.open-meteo.com"
        start = today - timedelta(days=92) if recent else date(2016, 6, 1)
        end = today if recent else today - timedelta(days=2)
        days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
        if recent:
            assert req.url.params["past_days"] == "92"
        return httpx.Response(
            200,
            json={
                "daily": {
                    "time": [d.isoformat() for d in days],
                    "precipitation_sum": [2 if recent else 1] * len(days),
                }
            },
        )

    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        rows = fetch_climate(client, REGIONS[0], today=today, backfill_days=120)
    assert len(calls) == 2 and len(rows) == 180
    assert min(r.observation_date for r in rows) == today - timedelta(days=90)
    assert max(r.observation_date for r in rows) == today - timedelta(days=1)


def test_clima_ingest_marca_so_dias_anteriores_a_ontem_como_estimados(monkeypatch):
    from datetime import UTC, datetime, timedelta
    from decimal import Decimal
    from unittest.mock import MagicMock

    from valyra.scripts import ingest_alpha as script

    today = datetime(2026, 11, 28, 18, tzinfo=UTC)
    series = script.climate_pair(script.REGIONS[0])[0]
    monkeypatch.setattr(script, "REGIONS", script.REGIONS[:1])
    monkeypatch.setattr(
        script,
        "fetch_climate",
        lambda *_a, **_k: [
            script.Observation(
                series, today.date() - timedelta(days=d), Decimal(30), "https://example.org"
            )
            for d in (2, 1)
        ],
    )
    flags = []

    def record(*args, **kwargs):
        flags.append(kwargs["backfill"])
        return True

    monkeypatch.setattr(script.service, "record_observation", record)
    script.ingest(MagicMock(), MagicMock(), sources=("clima",), backfill_days=90, now=lambda: today)
    assert flags == [True, False]
