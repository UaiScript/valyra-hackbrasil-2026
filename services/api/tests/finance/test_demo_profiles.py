"""Perfis da demo: cada um é um cliente fictício com extrato próprio, isolado do demo padrão."""

from datetime import date

import pytest

from valyra.core import clock
from valyra.core.demo_profiles import PROFILE_HEADER
from valyra.scripts import seed_demo_profiles as demo
from valyra.seed import DEMO_ACCOUNT_ID

TODAY = date(2026, 11, 26)


@pytest.fixture
def perfis(seed, db_session, monkeypatch):
    monkeypatch.setattr(clock, "get_today", lambda: TODAY)
    return [demo.seed_profile(db_session, p) for p in demo.PROFILES]


def test_cada_perfil_abre_com_historico_calculado_pelo_finance(perfis, client, db_session):
    assert perfis == [True, True, True]
    camila = {PROFILE_HEADER: demo.CAMILA.key}

    accounts = client.get("/api/v1/finance/accounts", headers=camila).json()["items"]
    assert [a["id"] for a in accounts] == [str(demo.CAMILA.account_id)]
    summary = client.get("/api/v1/finance/summary", headers=camila).json()
    assert summary["realized_balance_cents"] == demo.CAMILA.balance_today
    assert summary["income_cents"] > 0 and summary["expenses_cents"] < 0
    recorrentes = client.get(
        "/api/v1/finance/transactions", params={"is_recurring": True}, headers=camila
    ).json()
    assert recorrentes["total"] > 0
    # O aperto de novembro gera o alerta de pressão de caixa pela regra da importação.
    assert client.get("/api/v1/alerts", headers=camila).json()["total"] == 1

    # O usuário demo padrão continua com a própria conta, sem receber o extrato dos perfis.
    padrao = client.get("/api/v1/finance/accounts").json()["items"]
    assert [a["id"] for a in padrao] == [str(DEMO_ACCOUNT_ID)]
    assert client.get("/api/v1/finance/transactions").json()["total"] == 0


def test_seed_mantem_alteracoes_e_reset_so_apaga_o_perfil(perfis, client, db_session):
    assert demo.seed_profile(db_session, demo.CAMILA) is False
    antes = client.get(
        "/api/v1/finance/transactions", headers={PROFILE_HEADER: demo.CAMILA.key}
    ).json()["total"]
    assert demo.seed_profile(db_session, demo.CAMILA, reset=True) is True
    depois = client.get(
        "/api/v1/finance/transactions", headers={PROFILE_HEADER: demo.CAMILA.key}
    ).json()["total"]
    assert depois == antes
    outro = client.get(
        "/api/v1/finance/transactions", headers={PROFILE_HEADER: demo.INVESTIDOR.key}
    ).json()["total"]
    assert outro > 0


def test_perfil_desconhecido_usa_o_demo_padrao(seed, client):
    r = client.get("/api/v1/finance/accounts", headers={PROFILE_HEADER: "perfil-removido"})
    assert [a["id"] for a in r.json()["items"]] == [str(DEMO_ACCOUNT_ID)]


def test_extrato_e_deterministico_e_nao_passa_de_hoje():
    rows = demo.build_rows(demo.INVESTIDOR_AVANCADO, TODAY)
    assert rows == demo.build_rows(demo.INVESTIDOR_AVANCADO, TODAY)
    assert max(r.date for r in rows) <= TODAY
    assert demo._reais(-123_405) == "-1234.05" and demo._reais(7) == "0.07"
