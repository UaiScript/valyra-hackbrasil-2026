"""Aceite do core HTTP da Issue #9 necessário ao pipeline integrado."""

import re
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from valyra.core.db import get_session
from valyra.core.deps import get_current_user_id
from valyra.core.pagination import Page


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


def test_app_error_usa_formato_unico(client_com_rota_de_erro):
    response = client_com_rota_de_erro.get("/_teste/erro")
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "NOT_FOUND", "message": "Recurso não encontrado", "details": {}}
    }


@pytest.mark.parametrize("query", ["limit=0", "limit=201", "offset=-1", "limit=abc"])
def test_validacao_usa_formato_unico(client_com_rota_de_erro, query):
    response = client_com_rota_de_erro.get("/_teste/validacao?" + query)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "errors" in response.json()["error"]["details"]


@pytest.mark.parametrize(
    "query,expected",
    [("", {"limit": 50, "offset": 0}), ("?limit=200&offset=4", {"limit": 200, "offset": 4})],
)
def test_paginacao(client_com_rota_de_erro, query, expected):
    assert client_com_rota_de_erro.get("/_teste/validacao" + query).json() == expected


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
        "finance_list_categories",
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


def test_identidade_demo_e_page(monkeypatch):
    monkeypatch.setenv("DEMO_USER_ID", "00000000-0000-0000-0000-000000000099")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://127.0.0.1/unused")
    from valyra.core.config import get_settings

    get_settings.cache_clear()
    try:
        assert get_current_user_id() == UUID("00000000-0000-0000-0000-000000000099")
        assert Page[int](items=[1], total=1, limit=50, offset=0).model_dump() == {
            "items": [1],
            "total": 1,
            "limit": 50,
            "offset": 0,
        }
    finally:
        get_settings.cache_clear()


def test_exportador_openapi_reprodutivel_com_lf_sem_banco(app, monkeypatch, tmp_path):
    import json

    from valyra.scripts import export_openapi

    monkeypatch.setattr(export_openapi, "PROJECT_ROOT", tmp_path)
    export_openapi.main()
    generated = tmp_path / "packages/contracts/openapi.json"
    first = generated.read_bytes()
    assert b"\r" not in first
    assert json.loads(first) == app.openapi()
    export_openapi.main()
    assert generated.read_bytes() == first
