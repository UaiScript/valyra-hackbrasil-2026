"""Pressão de caixa na importação e rotas /api/v1/alerts (Issue #47, ADR-0010 seção 6)."""

from datetime import date
from uuid import uuid4

import pytest

from valyra.alerts.models import Alert
from valyra.core import clock
from valyra.core.db import User
from valyra.finance.models import Account
from valyra.seed import DEMO_ACCOUNT_ID

CAB = b"date,description,amount\n"
IMPORT_URL = f"/api/v1/finance/accounts/{DEMO_ACCOUNT_ID}/import-batches"
ACCOUNT_URL = f"/api/v1/finance/accounts/{DEMO_ACCOUNT_ID}"
ALERTS_URL = "/api/v1/alerts"
# Saída variável depois da referência: realizado 10000 − 9000 = 1000 e variável −100/dia.
# Em 30 dias o saldo previsto chega a 1000 − 3000 = −2000 em 07/12.
NEGATIVA = b"2026-11-03,Supermercado BH,-90.00\n"


@pytest.fixture(autouse=True)
def hoje(monkeypatch):
    monkeypatch.setattr(clock, "get_today", lambda: date(2026, 11, 7))


def importar(client, linhas: bytes):
    r = client.post(IMPORT_URL, files={"file": ("extrato.csv", CAB + linhas, "text/csv")})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def saldo_baixo(client, seed):
    assert client.patch(ACCOUNT_URL, json={"balance_cents": 10000}).status_code == 200


def test_projecao_negativa_cria_alerta(client, saldo_baixo):
    assert importar(client, NEGATIVA)["alerts_created"] == 1

    page = client.get(ALERTS_URL).json()
    assert (page["total"], page["limit"], page["offset"]) == (1, 50, 0)
    alerta = page["items"][0]
    assert (alerta["kind"], alerta["severity"], alerta["status"]) == (
        "cash_pressure",
        "warning",
        "new",
    )
    assert alerta["account_id"] == str(DEMO_ACCOUNT_ID) and alerta["read_at"] is None
    assert alerta["evidence"] == {
        "days": 30,
        "today": "2026-11-07",
        "start_balance_cents": 1000,
        "min_balance_cents": -2000,
        "min_balance_date": "2026-12-07",
    }
    assert alerta["title"] == "Saldo previsto negativo"
    assert alerta["message"] == (
        "A projeção dos próximos 30 dias indica saldo mínimo de -R$ 20,00 em 07/12/2026."
    )


def test_evidencia_bate_com_a_projecao(client, saldo_baixo):
    importar(client, NEGATIVA)
    projecao = client.get(f"{ACCOUNT_URL}/projection", params={"days": 30}).json()
    evidencia = client.get(ALERTS_URL).json()["items"][0]["evidence"]
    assert evidencia["min_balance_cents"] == projecao["min_balance_cents"]
    assert evidencia["min_balance_date"] == projecao["min_balance_date"]
    assert evidencia["start_balance_cents"] == projecao["start_balance_cents"]


def test_reimportar_no_mesmo_mes_nao_duplica(client, saldo_baixo, db_session):
    importar(client, NEGATIVA)
    assert importar(client, NEGATIVA)["alerts_created"] == 0
    assert importar(client, b"2026-11-04,Padaria,-12.00\n")["alerts_created"] == 0
    assert client.get(ALERTS_URL).json()["total"] == 1
    chave = db_session.query(Alert.dedup_key).scalar()
    assert chave == f"cash:{DEMO_ACCOUNT_ID}:2026-11"


def test_mes_seguinte_cria_novo_alerta(client, saldo_baixo, monkeypatch):
    importar(client, NEGATIVA)
    monkeypatch.setattr(clock, "get_today", lambda: date(2026, 12, 7))
    assert importar(client, b"2026-12-01,Padaria,-12.00\n")["alerts_created"] == 1
    assert client.get(ALERTS_URL).json()["total"] == 2


def test_saldo_positivo_nao_cria(client, seed):
    assert importar(client, NEGATIVA)["alerts_created"] == 0
    assert client.get(ALERTS_URL).json()["total"] == 0


def test_referencia_futura_nao_cria(client, saldo_baixo):
    assert client.patch(ACCOUNT_URL, json={"balance_as_of": "2026-11-08"}).status_code == 200
    assert importar(client, NEGATIVA)["alerts_created"] == 0
    assert client.get(ALERTS_URL).json()["total"] == 0


def test_falha_ao_gravar_alerta_desfaz_importacao(client, saldo_baixo, monkeypatch):
    def falhar(*args, **kwargs):
        raise RuntimeError("falha simulada ao gravar alerta")

    monkeypatch.setattr("valyra.alerts.service.create_cash_pressure", falhar)
    with pytest.raises(RuntimeError, match="falha simulada"):
        client.post(IMPORT_URL, files={"file": ("extrato.csv", CAB + NEGATIVA, "text/csv")})

    assert client.get("/api/v1/finance/import-batches").json()["total"] == 0
    assert client.get("/api/v1/finance/transactions").json()["total"] == 0
    assert client.get(ALERTS_URL).json()["total"] == 0


def test_marcar_como_lido_preenche_read_at_uma_vez(client, saldo_baixo):
    importar(client, NEGATIVA)
    alerta_id = client.get(ALERTS_URL).json()["items"][0]["id"]

    r = client.patch(f"{ALERTS_URL}/{alerta_id}", json={"status": "read"})
    assert r.status_code == 200, r.text
    lido = r.json()
    assert lido["status"] == "read" and lido["read_at"] is not None
    assert lido["read_at"] >= lido["created_at"]

    # Repetir é idempotente: o instante da primeira leitura é preservado.
    de_novo = client.patch(f"{ALERTS_URL}/{alerta_id}", json={"status": "read"}).json()
    assert de_novo["read_at"] == lido["read_at"]
    assert client.get(ALERTS_URL).json()["items"][0]["status"] == "read"


@pytest.mark.parametrize(
    "corpo", [{}, {"status": "new"}, {"status": None}, {"status": "read", "title": "x"}]
)
def test_corpo_invalido(client, saldo_baixo, corpo):
    importar(client, NEGATIVA)
    alerta_id = client.get(ALERTS_URL).json()["items"][0]["id"]
    r = client.patch(f"{ALERTS_URL}/{alerta_id}", json=corpo)
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_alerta_alheio_ou_inexistente(client, db_session, seed):
    outro = User(name="Outra pessoa")
    db_session.add(outro)
    db_session.flush()
    conta = Account(
        user_id=outro.id, name="Alheia", balance_cents=0, balance_as_of=date(2026, 11, 1)
    )
    db_session.add(conta)
    db_session.flush()
    alheio = Alert(
        user_id=outro.id,
        kind="cash_pressure",
        severity="warning",
        title="Saldo previsto negativo",
        message="Mensagem de template",
        evidence={"days": 30},
        account_id=conta.id,
        dedup_key=f"cash:{conta.id}:2026-11",
    )
    db_session.add(alheio)
    db_session.commit()

    assert client.get(ALERTS_URL).json()["total"] == 0
    for alerta_id in (alheio.id, uuid4()):
        r = client.patch(f"{ALERTS_URL}/{alerta_id}", json={"status": "read"})
        assert r.status_code == 404 and r.json()["error"]["code"] == "ALERT_NOT_FOUND"
    db_session.refresh(alheio)
    assert alheio.status == "new"


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 201}, {"offset": -1}])
def test_paginacao_invalida(client, seed, params):
    assert client.get(ALERTS_URL, params=params).status_code == 422
