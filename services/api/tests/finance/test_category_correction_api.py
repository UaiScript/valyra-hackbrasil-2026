"""Correção de categoria pelo usuário (Issue #42)."""

from datetime import date
from uuid import uuid4

import pytest

from valyra.core.db import User
from valyra.finance.models import Account, ImportBatch, Transaction

TRANSACOES_URL = "/api/v1/finance/transactions"


def categoria_por_slug(client, slug: str) -> str:
    itens = client.get("/api/v1/finance/categories").json()["items"]
    return next(c["id"] for c in itens if c["slug"] == slug)


@pytest.fixture
def saida(client, seed, importar):
    importar(b"2026-11-03,Mercado Bom Preco,-52.30\n")
    return client.get(TRANSACOES_URL).json()["items"][0]


def corrigir(client, transacao_id: str, corpo):
    return client.patch(f"{TRANSACOES_URL}/{transacao_id}", json=corpo)


def test_corrige_categoria_preservando_sugestao(client, saida):
    nova = categoria_por_slug(client, "lazer")
    assert nova != saida["category"]["id"]

    response = corrigir(client, saida["id"], {"category_id": nova})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["category"]["id"] == nova
    assert body["category_source"] == "user"
    assert body["predicted_category_id"] == saida["predicted_category_id"]
    assert body["category_confidence"] == saida["category_confidence"]
    assert body["amount_cents"] == saida["amount_cents"]


def test_correcao_persiste(client, saida):
    nova = categoria_por_slug(client, "lazer")
    corrigir(client, saida["id"], {"category_id": nova})
    persistida = client.get(TRANSACOES_URL).json()["items"][0]
    assert persistida["category"]["id"] == nova
    assert persistida["category_source"] == "user"
    assert persistida["predicted_category_id"] == saida["predicted_category_id"]


def test_filtro_por_categoria_usa_a_corrigida(client, saida):
    nova = categoria_por_slug(client, "lazer")
    corrigir(client, saida["id"], {"category_id": nova})
    body = client.get(TRANSACOES_URL, params={"category_id": nova}).json()
    assert [t["id"] for t in body["items"]] == [saida["id"]]


def test_transacao_inexistente_retorna_404(client, seed):
    response = corrigir(client, str(uuid4()), {"category_id": categoria_por_slug(client, "lazer")})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TRANSACTION_NOT_FOUND"


def test_transacao_de_outro_usuario_retorna_404_sem_alterar(client, seed, db_session):
    outro = User(name="Outra pessoa")
    db_session.add(outro)
    db_session.flush()
    conta = Account(
        user_id=outro.id, name="Alheia", balance_cents=100, balance_as_of=date(2026, 11, 1)
    )
    db_session.add(conta)
    db_session.flush()
    lote = ImportBatch(account_id=conta.id, file_name="alheio.csv")
    db_session.add(lote)
    db_session.flush()
    outros = categoria_por_slug(client, "outros")
    alheia = Transaction(
        account_id=conta.id,
        import_batch_id=lote.id,
        date=date(2026, 11, 2),
        description="Segredo alheio",
        amount_cents=-100,
        category_id=outros,
        predicted_category_id=outros,
        category_source="rule",
        row_hash=uuid4().hex,
    )
    db_session.add(alheia)
    db_session.commit()

    lazer = categoria_por_slug(client, "lazer")
    response = corrigir(client, str(alheia.id), {"category_id": lazer})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TRANSACTION_NOT_FOUND"
    db_session.refresh(alheia)
    assert str(alheia.category_id) == outros and alheia.category_source == "rule"


def test_categoria_inexistente_retorna_404(client, saida):
    response = corrigir(client, saida["id"], {"category_id": str(uuid4())})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CATEGORY_NOT_FOUND"


def test_categoria_de_tipo_incompativel_retorna_422_sem_alterar(client, saida):
    receita = categoria_por_slug(client, "outras-receitas")

    response = corrigir(client, saida["id"], {"category_id": receita})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CATEGORY_KIND_MISMATCH"
    atual = client.get(TRANSACOES_URL).json()["items"][0]
    assert atual["category"]["id"] == saida["category"]["id"]
    assert atual["category_source"] == saida["category_source"]


def test_receita_nao_aceita_categoria_de_despesa(client, seed, importar):
    importar(b"2026-11-05,Salario empresa,3000.00\n")
    entrada = client.get(TRANSACOES_URL).json()["items"][0]
    response = corrigir(client, entrada["id"], {"category_id": categoria_por_slug(client, "lazer")})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CATEGORY_KIND_MISMATCH"


@pytest.mark.parametrize(
    "corpo",
    [{}, {"category_id": None}, {"category_id": "nao-e-uuid"}, {"category_id": "x", "extra": 1}],
)
def test_corpo_invalido_retorna_422(client, saida, corpo):
    response = corrigir(client, saida["id"], corpo)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_campo_extra_com_categoria_valida_retorna_422(client, saida):
    corpo = {"category_id": categoria_por_slug(client, "lazer"), "category_source": "rule"}
    response = corrigir(client, saida["id"], corpo)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
