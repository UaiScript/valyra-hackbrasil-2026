"""Checks e unicidade da tabela alerts (#47) no PostgreSQL."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from valyra.alerts.models import Alert

pytestmark = pytest.mark.postgres
NOW = datetime(2026, 11, 7, 18, tzinfo=UTC)


@pytest.fixture
def alerta(db_session, reference_rows):
    def criar(**overrides):
        values = {
            "user_id": reference_rows["user"].id,
            "kind": "cash_pressure",
            "severity": "warning",
            "title": "Saldo previsto negativo",
            "message": "Mensagem de template",
            "evidence": {"days": 30},
            "account_id": reference_rows["account"].id,
            "dedup_key": "cash:conta:2026-11",
        }
        alert = Alert(**(values | overrides))
        db_session.add(alert)
        db_session.flush()
        return alert

    return criar


def test_alerta_valido_comeca_novo(alerta):
    alert = alerta()
    assert alert.status == "new" and alert.read_at is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"kind": "market_signal"},
        {"severity": "critical"},
        {"status": "archived"},
        {"status": "read"},
        {"read_at": NOW},
        {"status": "read", "read_at": NOW, "created_at": NOW + timedelta(seconds=1)},
        {"account_id": None},
        {"evidence": None},
        {"title": None},
        {"dedup_key": None},
    ],
)
def test_alerta_invalido(db_session, alerta, overrides):
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            alerta(**overrides)


def test_lido_com_read_at_e_aceito(alerta):
    alert = alerta(status="read", read_at=NOW, created_at=NOW)
    assert alert.read_at == NOW


def test_dedup_key_unica_por_usuario(db_session, alerta):
    alerta()
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            alerta()
    # Outra chave do mesmo usuário continua permitida.
    alerta(dedup_key="cash:conta:2026-12")
