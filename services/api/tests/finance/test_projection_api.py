"""GET /api/v1/finance/accounts/{id}/projection (Issue #46, ADR-0010 seção 5)."""

from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest

from valyra.core import clock
from valyra.core.db import User
from valyra.finance.models import Account
from valyra.seed import DEMO_ACCOUNT_ID

URL = f"/api/v1/finance/accounts/{DEMO_ACCOUNT_ID}/projection"
DEMO_CSV = Path(__file__).resolve().parents[4] / "datasets" / "samples" / "transactions_demo.csv"


@pytest.fixture(autouse=True)
def hoje(monkeypatch):
    # Fixa "hoje" sem depender do relógio nem do DEMO_TODAY do ambiente.
    monkeypatch.setattr(clock, "get_today", lambda: date(2026, 11, 7))


@pytest.fixture
def movimentos(seed, importar):
    # Seed: referência 500000 em 2026-11-01. Netflix recorrente (intervalos 31 e 30 → 30 dias)
    # e uma saída variável depois da referência: realizado 491000, variável 9000 / 90 = 100/dia.
    return importar(
        b"2026-08-10,Netflix.com,-55.90\n"
        b"2026-09-10,Netflix.com,-55.90\n"
        b"2026-10-10,Netflix.com,-55.90\n"
        b"2026-11-02,Supermercado BH,-90.00\n"
    )


def test_projecao_diaria(client, movimentos):
    r = client.get(URL, params={"days": 3})

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["account_id"] == str(DEMO_ACCOUNT_ID) and body["today"] == "2026-11-07"
    assert (body["start_balance_cents"], body["variable_daily_cents"], body["days"]) == (
        491000,
        -100,
        3,
    )
    assert body["items"] == [
        {
            "date": "2026-11-08",
            "recurrences": [],
            "recurring_cents": 0,
            "variable_cents": -100,
            "balance_cents": 490900,
        },
        {
            "date": "2026-11-09",
            "recurrences": [{"description": "Netflix.com", "amount_cents": -5590}],
            "recurring_cents": -5590,
            "variable_cents": -100,
            "balance_cents": 485210,
        },
        {
            "date": "2026-11-10",
            "recurrences": [],
            "recurring_cents": 0,
            "variable_cents": -100,
            "balance_cents": 485110,
        },
    ]
    assert (body["min_balance_cents"], body["min_balance_date"]) == (485110, "2026-11-10")


def test_horizonte_padrao_de_30_dias(client, movimentos):
    body = client.get(URL).json()
    assert body["days"] == 30 and len(body["items"]) == 30
    assert body["items"][-1]["date"] == "2026-12-07"


def test_recorrencia_atrasada_pula_para_a_proxima_data(client, seed, importar):
    # Intervalos de 31 dias: 02/10 e 02/11 já passaram sem lançamento; a próxima é 03/12.
    importar(
        b"2026-07-01,Spotify Premium,-21.90\n"
        b"2026-08-01,Spotify Premium,-21.90\n"
        b"2026-09-01,Spotify Premium,-21.90\n"
    )
    items = client.get(URL).json()["items"]
    previstas = [i["date"] for i in items if i["recurrences"]]
    assert previstas == ["2026-12-03"]


@pytest.mark.parametrize("dias", ["0", "91", "-1", "trinta"])
def test_horizonte_invalido(client, seed, dias):
    r = client.get(URL, params={"days": dias})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_horizonte_maximo(client, seed):
    assert len(client.get(URL, params={"days": 90}).json()["items"]) == 90


def test_referencia_futura_deixa_saldo_indisponivel(client, seed):
    conta = f"/api/v1/finance/accounts/{DEMO_ACCOUNT_ID}"
    assert client.patch(conta, json={"balance_as_of": "2026-11-08"}).status_code == 200

    r = client.get(URL)

    assert r.status_code == 422
    assert r.json()["error"]["code"] == "BALANCE_UNAVAILABLE"


def test_conta_alheia_ou_inexistente_responde_404(client, db_session, seed):
    outro = User(name="Outra pessoa")
    db_session.add(outro)
    db_session.flush()
    alheia = Account(
        user_id=outro.id, name="Alheia", balance_cents=100, balance_as_of=date(2026, 11, 1)
    )
    db_session.add(alheia)
    db_session.commit()

    for conta_id in (alheia.id, uuid4()):
        r = client.get(f"/api/v1/finance/accounts/{conta_id}/projection")
        assert r.status_code == 404 and r.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"


def test_projecao_nao_grava_nada(client, movimentos):
    antes = client.get("/api/v1/finance/transactions", params={"limit": 200}).json()
    resumo_antes = client.get("/api/v1/finance/summary").json()

    assert client.get(URL, params={"days": 90}).status_code == 200

    assert client.get("/api/v1/finance/transactions", params={"limit": 200}).json() == antes
    assert client.get("/api/v1/finance/summary").json() == resumo_antes


def test_csv_de_demonstracao(client, seed, importar):
    importar(DEMO_CSV.read_bytes().split(b"\n", 1)[1])
    body = client.get(URL).json()
    # O CSV termina antes da referência (01/11): o saldo de partida é a própria referência.
    assert body["start_balance_cents"] == 500000
    assert body["variable_daily_cents"] < 0
    previstas = {
        (i["date"], r["description"], r["amount_cents"])
        for i in body["items"]
        for r in i["recurrences"]
    }
    # Salário em 05/08, 05/09 e 05/10: intervalo 30 (piso de 30,5); 04/11 já passou → 04/12.
    assert ("2026-12-04", "Salario ACME Tecnologia", 650000) in previstas
