"""GET /api/v1/finance/summary (Issue #43)."""

from datetime import date

import pytest

from valyra.core import clock
from valyra.core.db import User
from valyra.finance.models import Account
from valyra.seed import DEMO_ACCOUNT_ID

URL = "/api/v1/finance/summary"
CONTA_URL = f"/api/v1/finance/accounts/{DEMO_ACCOUNT_ID}"


@pytest.fixture(autouse=True)
def hoje(monkeypatch):
    # Fixa "hoje" sem depender do relógio nem do DEMO_TODAY do ambiente.
    monkeypatch.setattr(clock, "get_today", lambda: date(2026, 11, 7))


@pytest.fixture
def movimentos(seed, importar):
    # Seed: referência 500000 em 2026-11-01.
    return importar(
        b"2026-10-15,Supermercado Bom Preco,-70.00\n"
        b"2026-11-01,Padaria Central,-10.00\n"
        b"2026-11-02,Supermercado Bom Preco,-129.90\n"
        b"2026-11-05,Salario ACME,3500.00\n"
        b"2026-11-10,Supermercado Bom Preco,-200.00\n"
    )


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


def test_exemplo_da_modelagem(client, seed, importar):
    importar(b"2026-11-02,Supermercado Bom Preco,-129.90\n")
    body = client.get(URL, params={"account_id": str(DEMO_ACCOUNT_ID)}).json()
    assert body["realized_balance_cents"] == 487010
    assert body["today"] == "2026-11-07"
    assert body["account_id"] == str(DEMO_ACCOUNT_ID)


def test_resumo_do_mes_padrao(client, movimentos):
    r = client.get(URL)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["month"] == "2026-11"
    # Realizado: só 02/11 e 05/11; 01/11 já está no fechamento e 10/11 é futuro.
    assert body["realized_balance_cents"] == 500000 - 12990 + 350000
    # Mês: 01/11, 02/11 e 05/11; 10/11 ainda não foi realizado.
    assert body["income_cents"] == 350000
    assert body["expenses_cents"] == -13990
    assert body["net_cents"] == 336010
    totais = [(c["category"]["slug"], c["total_cents"], c["count"]) for c in body["categories"]]
    assert totais[0] == ("salario", 350000, 1)
    assert sum(total for _, total, _ in totais) == body["net_cents"]
    assert sum(count for *_, count in totais) == 3
    assert all(type(c["total_cents"]) is int for c in body["categories"])
    assert set(body["categories"][0]["category"]) == {"id", "slug", "name", "kind"}


def test_mes_passado_nao_muda_o_realizado(client, movimentos):
    body = client.get(URL, params={"month": "2026-10"}).json()
    assert body["month"] == "2026-10"
    assert body["expenses_cents"] == -7000
    assert body["income_cents"] == 0
    assert body["realized_balance_cents"] == 837010


def test_mes_sem_movimentos(client, seed):
    body = client.get(URL, params={"month": "2026-09"}).json()
    assert body["categories"] == []
    assert (body["income_cents"], body["expenses_cents"], body["net_cents"]) == (0, 0, 0)
    assert body["realized_balance_cents"] == 500000


def test_referencia_futura_deixa_realizado_nulo(client, movimentos):
    r = client.patch(CONTA_URL, json={"balance_as_of": "2026-11-08"})
    assert r.status_code == 200, r.text
    body = client.get(URL).json()
    assert body["realized_balance_cents"] is None
    # O resumo do mês não depende da referência.
    assert body["income_cents"] == 350000


def test_sem_conta_soma_todas_as_contas_do_usuario(client, db_session, movimentos, conta_alheia):
    demo = db_session.get(Account, DEMO_ACCOUNT_ID)
    db_session.add(
        Account(
            user_id=demo.user_id,
            name="Poupança",
            balance_cents=20000,
            balance_as_of=date(2026, 11, 1),
        )
    )
    db_session.commit()
    body = client.get(URL).json()
    assert body["account_id"] is None
    # A conta alheia (saldo 100) não entra.
    assert body["realized_balance_cents"] == 837010 + 20000


def test_uma_conta_com_referencia_futura_anula_a_soma(client, db_session, seed):
    demo = db_session.get(Account, DEMO_ACCOUNT_ID)
    db_session.add(
        Account(
            user_id=demo.user_id,
            name="Poupança",
            balance_cents=20000,
            balance_as_of=date(2026, 12, 1),
        )
    )
    db_session.commit()
    assert client.get(URL).json()["realized_balance_cents"] is None
    filtrado = client.get(URL, params={"account_id": str(DEMO_ACCOUNT_ID)}).json()
    assert filtrado["realized_balance_cents"] == 500000


def test_conta_alheia_responde_404(client, conta_alheia):
    r = client.get(URL, params={"account_id": str(conta_alheia.id)})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"


@pytest.mark.parametrize("mes", ["2026-13", "2026-00", "abc", "2026-1", "2026-11-01", "0999-01"])
def test_mes_invalido_responde_422(client, seed, mes):
    r = client.get(URL, params={"month": mes})
    assert r.status_code == 422
    assert "error" in r.json()


def test_resumo_nao_grava_nada(client, movimentos):
    antes = client.get("/api/v1/finance/transactions").json()
    client.get(URL)
    assert client.get("/api/v1/finance/transactions").json() == antes
