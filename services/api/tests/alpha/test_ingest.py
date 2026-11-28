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


def test_brapi_historico_vira_variacao_de_cada_pregao():
    body = {
        "results": [
            {
                "regularMarketChangePercent": 1.5,
                "regularMarketTime": "2026-11-27T20:07:00.000Z",
                "historicalDataPrice": [
                    {"date": 1764158400, "close": 40.0},  # 26/11/2025 12h UTC
                    {"date": 1764244800, "close": 41.0},
                    {"date": "x", "close": 1},  # linha inválida só encurta o histórico
                ],
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["range"] == "3mo"
        return httpx.Response(200, json=body)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    found = fetch_brapi(client, STOCK_SERIES[0], token="", history=True)
    assert [str(o.value) for o in found] == ["2.50", "1.5"]
    assert found[0].observation_date.isoformat() == "2025-11-27"
