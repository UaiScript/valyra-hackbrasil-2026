"""Gasto atípico recalculado na importação e na correção de categoria (Issue #45)."""

from decimal import Decimal

import pytest
from sqlalchemy import select

from valyra.finance.models import Transaction

URL = "/api/v1/finance/transactions"

# Mercado: magnitudes 100, 100, 110, 120 e 1000 centavos → mediana 110, MAD 10.
MERCADO = (
    b"2026-10-01,Supermercado BH,-1.00\n"
    b"2026-10-02,Supermercado BH,-1.00\n"
    b"2026-10-03,Supermercado BH,-1.10\n"
    b"2026-10-04,Supermercado BH,-1.20\n"
    b"2026-10-05,Supermercado BH,-10.00\n"
)


def categoria_por_slug(client, slug: str) -> str:
    itens = client.get("/api/v1/finance/categories").json()["items"]
    return next(c["id"] for c in itens if c["slug"] == slug)


def transacoes(client, **params):
    return client.get(URL, params={"limit": 200, **params}).json()["items"]


def por_valor(client):
    return {t["amount_cents"]: t for t in transacoes(client)}


@pytest.fixture
def mercado(seed, importar):
    return importar(MERCADO)


def test_outlier_marcado_e_score_como_string_decimal(client, mercado):
    itens = por_valor(client)
    assert (itens[-1000]["anomaly_score"], itens[-1000]["is_anomaly"]) == ("1.0000", True)
    assert (itens[-120]["anomaly_score"], itens[-120]["is_anomaly"]) == ("0.1542", False)
    assert itens[-100]["anomaly_score"] == "0.0000"


def test_entrada_e_categoria_pequena_ficam_sem_score(client, mercado, importar):
    importar(b"2026-10-05,Salario ACME,3500.00\n2026-10-06,Cinema Shopping,-40.00\n")
    itens = por_valor(client)
    for valor in (350000, -4000):
        assert (itens[valor]["anomaly_score"], itens[valor]["is_anomaly"]) == (None, False)


def test_score_gravado_respeita_o_check_do_banco(db_session, mercado):
    scores = db_session.scalars(select(Transaction.anomaly_score)).all()
    assert all(isinstance(s, Decimal) and Decimal(0) <= s <= Decimal(1) for s in scores)


def test_corrigir_categoria_recalcula_origem_e_destino(client, mercado, importar):
    # Lazer com quatro saídas ainda sem score; o outlier do mercado completa cinco.
    importar(b"".join(b"2026-10-%02d,Cinema Shopping,-50.00\n" % d for d in range(10, 14)))
    assert all(t["anomaly_score"] is None for t in transacoes(client) if t["amount_cents"] == -5000)
    outlier = por_valor(client)[-1000]

    r = client.patch(
        f"{URL}/{outlier['id']}", json={"category_id": categoria_por_slug(client, "lazer")}
    )

    assert r.status_code == 200, r.text
    # A resposta já traz o score recalculado no grupo de destino (1000 abaixo da mediana 5000).
    assert (r.json()["anomaly_score"], r.json()["is_anomaly"]) == ("0.0000", False)
    itens = transacoes(client)
    # Origem ficou com quatro saídas: perde os scores.
    assert all(t["anomaly_score"] is None for t in itens if t["amount_cents"] in (-100, -110, -120))
    # Destino passou a cinco saídas: ganha scores.
    assert all(t["anomaly_score"] == "0.0000" for t in itens if t["amount_cents"] == -5000)


def test_filtro_is_anomaly(client, mercado, importar):
    importar(b"2026-10-05,Salario ACME,3500.00\n")

    atipicas = client.get(URL, params={"is_anomaly": "true"}).json()
    assert [t["amount_cents"] for t in atipicas["items"]] == [-1000]

    # Sem score (a entrada) também conta como não atípica.
    normais = client.get(URL, params={"is_anomaly": "false"}).json()
    assert normais["total"] == 5 and -1000 not in {t["amount_cents"] for t in normais["items"]}


def test_filtro_is_anomaly_invalido(client, seed):
    response = client.get(URL, params={"is_anomaly": "talvez"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_reimportar_nao_muda_scores_nem_updated_at(client, db_session, mercado, importar):
    antes = {t.id: (t.anomaly_score, t.updated_at) for t in db_session.scalars(select(Transaction))}

    lote = importar(MERCADO)

    assert lote["rows_imported"] == 0
    db_session.expire_all()
    depois = {
        t.id: (t.anomaly_score, t.updated_at) for t in db_session.scalars(select(Transaction))
    }
    assert depois == antes
