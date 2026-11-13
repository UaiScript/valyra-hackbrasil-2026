"""Consultas de contas, transações e categorias (Issue #15)."""

from datetime import date
from uuid import uuid4

import pytest

from valyra.core.db import User
from valyra.finance.models import Account, ImportBatch, Transaction
from valyra.seed import DEMO_ACCOUNT_ID

CONTA_URL = f"/api/v1/finance/accounts/{DEMO_ACCOUNT_ID}"


def categoria_por_slug(client, slug: str) -> str:
    itens = client.get("/api/v1/finance/categories").json()["items"]
    return next(c["id"] for c in itens if c["slug"] == slug)


@pytest.fixture
def conta_alheia(db_session, seed):
    outro = User(name="Outra pessoa")
    db_session.add(outro)
    db_session.flush()
    conta = Account(
        user_id=outro.id, name="Alheia", balance_cents=100, balance_as_of=date(2026, 11, 1)
    )
    db_session.add(conta)
    db_session.commit()
    return conta


# --- contas -------------------------------------------------------------------------------


def test_lista_contas_do_usuario(client, seed):
    body = client.get("/api/v1/finance/accounts").json()
    assert body["total"] == 1
    assert body["items"][0] == {
        "id": str(DEMO_ACCOUNT_ID),
        "name": "Conta principal",
        "balance_cents": 500000,
        "balance_as_of": "2026-11-01",
    }


def test_lista_contas_nao_mostra_conta_de_outro_usuario(client, conta_alheia):
    ids = [c["id"] for c in client.get("/api/v1/finance/accounts").json()["items"]]
    assert ids == [str(DEMO_ACCOUNT_ID)]


def test_atualiza_saldo(client, seed):
    r = client.patch(CONTA_URL, json={"balance_cents": 421050, "balance_as_of": "2026-11-07"})
    assert r.status_code == 200
    assert r.json() == {
        "id": str(DEMO_ACCOUNT_ID),
        "name": "Conta principal",
        "balance_cents": 421050,
        "balance_as_of": "2026-11-07",
    }


def test_atualizacao_persiste(client, seed):
    client.patch(CONTA_URL, json={"name": "Conta corrente"})
    assert client.get("/api/v1/finance/accounts").json()["items"][0]["name"] == "Conta corrente"


def test_atualiza_conta_inexistente_retorna_404(client, seed):
    r = client.patch(f"/api/v1/finance/accounts/{uuid4()}", json={"name": "X"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"


def test_atualiza_conta_de_outro_usuario_retorna_404(client, conta_alheia, db_session):
    r = client.patch(f"/api/v1/finance/accounts/{conta_alheia.id}", json={"name": "Invadida"})
    assert r.status_code == 404
    db_session.refresh(conta_alheia)
    assert conta_alheia.name == "Alheia"


@pytest.mark.parametrize(
    "corpo",
    [
        {"balance_cents": 10.5},
        {"balance_cents": "1000"},
        {"balance_cents": True},
        {"balance_cents": 9_223_372_036_854_775_808},
        {"balance_cents": None},
        {"name": None},
        {"name": ""},
        {"name": "Conta\u0000principal"},
        {"name": "\u0000"},
        {"balance_as_of": None},
        {"balance_as_of": "07/11/2026"},
        {"balance_as_of": "0"},
        {"balance_as_of": "1762473600"},
        {"balance_as_of": "2026-11-07T00:00:00Z"},
        {"balance_as_of": 1762473600},
        {"user_id": str(uuid4())},
    ],
)
def test_atualizacao_invalida_retorna_422(client, seed, corpo):
    r = client.patch(CONTA_URL, json=corpo)
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    conta = client.get("/api/v1/finance/accounts").json()["items"][0]
    assert (conta["name"], conta["balance_cents"], conta["balance_as_of"]) == (
        "Conta principal",
        500000,
        "2026-11-01",
    )


def test_saldo_nao_inteiro_retorna_422(client, seed):
    r = client.patch(CONTA_URL, json={"balance_cents": 10.5})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


# --- transações ---------------------------------------------------------------------------


def test_lista_transacoes_ordenadas_por_data_desc(client, seed, importar):
    importar(b"2026-11-01,A,-1.00\n2026-11-05,B,-2.00\n")
    datas = [t["date"] for t in client.get("/api/v1/finance/transactions").json()["items"]]
    assert datas == ["2026-11-05", "2026-11-01"]


def test_filtra_por_periodo_e_categoria(client, seed, importar):
    importar(
        b"2026-10-20,Netflix.com,-55.90\n2026-11-02,Netflix.com,-55.90\n2026-11-03,Uber,-20.00\n"
    )
    cat = categoria_por_slug(client, "assinaturas")
    body = client.get(
        "/api/v1/finance/transactions",
        params={"date_from": "2026-11-01", "date_to": "2026-11-30", "category_id": cat},
    ).json()
    assert body["total"] == 1 and body["items"][0]["category"]["slug"] == "assinaturas"


def test_limites_de_data_sao_inclusivos(client, seed, importar):
    importar(b"2026-11-01,A,-1.00\n2026-11-02,B,-1.00\n2026-11-03,C,-1.00\n")
    body = client.get(
        "/api/v1/finance/transactions", params={"date_from": "2026-11-01", "date_to": "2026-11-02"}
    ).json()
    assert [t["date"] for t in body["items"]] == ["2026-11-02", "2026-11-01"]


def test_intervalo_invertido_retorna_lista_vazia(client, seed, importar):
    importar(b"2026-11-01,A,-1.00\n")
    body = client.get(
        "/api/v1/finance/transactions", params={"date_from": "2026-11-30", "date_to": "2026-11-01"}
    ).json()
    assert body["total"] == 0 and body["items"] == []


def test_transacao_em_centavos_sem_campos_ainda_nao_calculados(client, seed, importar):
    importar(b"2026-11-01,A,-1.00\n")
    item = client.get("/api/v1/finance/transactions").json()["items"][0]
    assert item["amount_cents"] == -100 and "amount" not in item
    assert "is_recurring" not in item and "is_anomaly" not in item


def test_formato_completo_da_transacao(client, seed, importar):
    importar(b"2026-11-03,Supermercado BH,-89.90\n")
    item = client.get("/api/v1/finance/transactions").json()["items"][0]
    mercado = categoria_por_slug(client, "mercado")
    assert set(item) == {
        "id",
        "date",
        "description",
        "amount_cents",
        "category",
        "category_source",
        "category_confidence",
        "predicted_category_id",
    }
    assert item["category"] == {"id": mercado, "slug": "mercado", "name": "Mercado"}
    assert (item["category_source"], item["category_confidence"]) == ("rule", None)
    assert item["predicted_category_id"] == mercado
    assert (item["date"], item["description"], item["amount_cents"]) == (
        "2026-11-03",
        "Supermercado BH",
        -8990,
    )


def test_filtro_por_conta_do_usuario(client, seed, importar):
    importar(b"2026-11-01,A,-1.00\n")
    r = client.get("/api/v1/finance/transactions", params={"account_id": str(DEMO_ACCOUNT_ID)})
    assert r.status_code == 200 and r.json()["total"] == 1


def test_filtro_por_conta_de_outro_usuario_retorna_404(client, conta_alheia):
    r = client.get("/api/v1/finance/transactions", params={"account_id": str(conta_alheia.id)})
    assert r.status_code == 404 and r.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"


def test_paginacao_de_transacoes(client, seed, importar):
    importar(b"2026-11-01,A,-1.00\n2026-11-02,B,-1.00\n2026-11-03,C,-1.00\n")
    body = client.get("/api/v1/finance/transactions", params={"limit": 2, "offset": 1}).json()
    assert (body["total"], body["limit"], body["offset"]) == (3, 2, 1)
    assert [t["date"] for t in body["items"]] == ["2026-11-02", "2026-11-01"]


def test_limit_acima_de_200_retorna_422(client, seed):
    assert client.get("/api/v1/finance/transactions?limit=201").status_code == 422


@pytest.mark.parametrize("param", ["date_from", "date_to"])
@pytest.mark.parametrize("valor", ["01/11/2026", "0", "1762473600", "2026-11-07T00:00:00Z"])
def test_data_de_filtro_invalida_retorna_422(client, seed, param, valor):
    r = client.get("/api/v1/finance/transactions", params={param: valor})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


# --- categorias ---------------------------------------------------------------------------


def test_lista_categorias(client, seed):
    body = client.get("/api/v1/finance/categories").json()
    assert body["total"] == 12 and {"slug", "name", "kind", "id"} == set(body["items"][0])


def test_categorias_ordenadas_por_tipo_e_nome(client, seed):
    itens = client.get("/api/v1/finance/categories").json()["items"]
    chaves = [(c["kind"], c["name"]) for c in itens]
    assert chaves == sorted(chaves)
    assert itens[0]["kind"] == "expense" and itens[-1]["kind"] == "income"


def test_lista_sem_filtro_nao_mostra_transacoes_de_outro_usuario(
    client, conta_alheia, db_session, importar
):
    lote = ImportBatch(account_id=conta_alheia.id, file_name="alheio.csv")
    db_session.add(lote)
    db_session.flush()
    outros = categoria_por_slug(client, "outros")
    db_session.add(
        Transaction(
            account_id=conta_alheia.id,
            import_batch_id=lote.id,
            date=date(2026, 11, 2),
            description="Segredo alheio",
            amount_cents=-100,
            category_id=outros,
            predicted_category_id=outros,
            category_source="rule",
            row_hash=uuid4().hex,
        )
    )
    db_session.commit()
    importar(b"2026-11-01,Minha,-1.00\n")
    body = client.get("/api/v1/finance/transactions").json()
    assert body["total"] == 1 and [t["description"] for t in body["items"]] == ["Minha"]
