"""Fixtures do Finance HTTP: seed do usuário demo e importação auxiliar."""

import pytest

from valyra.seed import DEMO_ACCOUNT_ID, run

CAB = b"date,description,amount\n"
IMPORT_URL = f"/api/v1/finance/accounts/{DEMO_ACCOUNT_ID}/import-batches"


@pytest.fixture
def seed(db_session):
    run(db_session)
    db_session.commit()


@pytest.fixture
def importar(client):
    def enviar(linhas: bytes):
        r = client.post(IMPORT_URL, files={"file": ("extrato.csv", CAB + linhas, "text/csv")})
        assert r.status_code == 201, r.text
        return r.json()

    return enviar
