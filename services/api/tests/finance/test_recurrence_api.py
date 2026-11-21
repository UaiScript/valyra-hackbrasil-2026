"""Recorrência recalculada na importação e exposta em GET /transactions (Issue #44)."""

from pathlib import Path

import pytest

from valyra.finance.models import Transaction
from valyra.seed import DEMO_ACCOUNT_ID

URL = "/api/v1/finance/transactions"
DEMO_CSV = Path(__file__).resolve().parents[4] / "datasets" / "samples" / "transactions_demo.csv"


def transacoes(client, **params):
    body = client.get(URL, params={"limit": 200, **params}).json()
    return body["items"]


def por_descricao(client, descricao):
    return [t for t in transacoes(client) if t["description"] == descricao]


@pytest.fixture
def mensalidade(seed, importar):
    def importar_mes(mes: int, valor: bytes = b"-55.90", descricao: bytes = b"Netflix.com"):
        return importar(b"2026-%02d-10,%s,%s\n" % (mes, descricao, valor))

    return importar_mes


def test_recorrencia_formada_por_lotes_diferentes(client, mensalidade):
    mensalidade(8)
    mensalidade(9)
    # Duas ocorrências ainda não bastam.
    assert [t["is_recurring"] for t in por_descricao(client, "Netflix.com")] == [False, False]

    mensalidade(10)
    # A terceira, em outro lote, marca a série inteira, inclusive as linhas dos lotes antigos.
    assert [t["is_recurring"] for t in por_descricao(client, "Netflix.com")] == [True] * 3


def test_chave_da_serie_gravada_e_nao_exposta(client, db_session, mensalidade):
    for mes in (8, 9, 10):
        mensalidade(mes)
    item = por_descricao(client, "Netflix.com")[0]
    assert "recurrence_key" not in item
    assert db_session.get(Transaction, item["id"]).recurrence_key == "-|netflix.com"


def test_ocorrencia_irregular_desmarca_a_serie(client, mensalidade, importar):
    for mes in (8, 9, 10):
        mensalidade(mes)
    importar(b"2026-10-20,NETFLIX.COM,-55.90\n")  # mesma série pela normalização, 10 dias depois
    serie = por_descricao(client, "Netflix.com") + por_descricao(client, "NETFLIX.COM")
    assert len(serie) == 4 and not any(t["is_recurring"] for t in serie)


def test_valor_fora_da_tolerancia_nao_marca(client, mensalidade):
    mensalidade(8)
    mensalidade(9)
    mensalidade(10, valor=b"-79.90")
    assert not any(t["is_recurring"] for t in por_descricao(client, "Netflix.com"))


def test_reimportar_nao_muda_flags_nem_updated_at(client, db_session, seed, importar):
    conteudo = b"".join(b"2026-%02d-05,Aluguel apartamento,-1800.00\n" % m for m in (8, 9, 10))
    importar(conteudo)
    linhas = db_session.query(Transaction).filter_by(account_id=DEMO_ACCOUNT_ID).all()
    antes = {t.id: (t.is_recurring, t.recurrence_key, t.updated_at) for t in linhas}
    assert all(flag for flag, _, _ in antes.values())

    lote = importar(conteudo)

    assert lote["rows_imported"] == 0 and lote["rows_duplicated"] == 3
    db_session.expire_all()
    linhas = db_session.query(Transaction).filter_by(account_id=DEMO_ACCOUNT_ID).all()
    assert {t.id: (t.is_recurring, t.recurrence_key, t.updated_at) for t in linhas} == antes


def test_filtro_is_recurring(client, mensalidade, importar):
    for mes in (8, 9, 10):
        mensalidade(mes)
    importar(b"2026-10-11,Padaria Central,-12.00\n")

    recorrentes = client.get(URL, params={"is_recurring": "true"}).json()
    assert recorrentes["total"] == 3
    assert {t["description"] for t in recorrentes["items"]} == {"Netflix.com"}

    avulsas = client.get(URL, params={"is_recurring": "false"}).json()
    assert [t["description"] for t in avulsas["items"]] == ["Padaria Central"]

    assert client.get(URL).json()["total"] == 4


def test_filtro_is_recurring_invalido(client, seed):
    response = client.get(URL, params={"is_recurring": "talvez"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_csv_de_demonstracao(client, seed, importar):
    importar(DEMO_CSV.read_bytes().split(b"\n", 1)[1])
    recorrentes = {t["description"] for t in transacoes(client, is_recurring="true")}
    for esperada in (
        "Salario ACME Tecnologia",
        "Aluguel apartamento",
        "Netflix.com",
        "Spotify Premium",
        "Condominio Edificio Ipe",
    ):
        assert esperada in recorrentes
    # Uso frequente e irregular não é recorrência.
    assert "Uber *Trip" not in recorrentes
    assert "Supermercado BH" not in recorrentes
