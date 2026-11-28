"""Aceite do core HTTP da Issue #9 necessário ao pipeline integrado."""

import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from valyra.core.db import get_session


@pytest.mark.postgres
def test_health_retorna_ok_com_postgres(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "postgres": "ok"}


def test_health_retorna_degraded_sem_expor_erro(app):
    class UnavailableSession:
        def execute(self, statement):
            raise OperationalError("indisponível", {}, Exception("não publicar"))

    app.dependency_overrides[get_session] = UnavailableSession
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "postgres": "error"}


def test_operation_ids_e_contrato_minimo(app):
    spec = app.openapi()
    operation_ids = set()
    for methods in spec["paths"].values():
        for operation in methods.values():
            assert re.fullmatch(
                r"(system|finance|alpha|alerts|ai)_[a-z_]+", operation["operationId"]
            )
            operation_ids.add(operation["operationId"])
    assert operation_ids == {
        "system_health",
        "finance_create_import_batch",
        "finance_list_import_batches",
        "finance_get_import_batch",
        "finance_list_accounts",
        "finance_update_account",
        "finance_list_transactions",
        "finance_update_transaction",
        "finance_list_categories",
        "finance_get_summary",
        "finance_get_projection",
        "finance_get_budgets",
        "finance_set_budget",
        "finance_delete_budget",
        "alerts_list",
        "alerts_update",
        "alpha_get_forecasts",
        "alpha_get_radar",
        "alpha_get_weekly_news",
        "ai_explain",
    }


def test_cors_somente_origem_configurada(app):
    with TestClient(app) as client:
        for origin, allowed in [
            ("http://127.0.0.1:5173", True),
            ("https://untrusted.example", False),
        ]:
            response = client.options(
                "/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
            )
            assert ("access-control-allow-origin" in response.headers) is allowed
