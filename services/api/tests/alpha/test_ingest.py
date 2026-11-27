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
