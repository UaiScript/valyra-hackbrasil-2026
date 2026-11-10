"""Fixtures HTTP; conexão real ocorre somente no teste que pede db_session."""

from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from valyra.core.config import Settings
from valyra.core.db import get_session
from valyra.core.errors import AppError
from valyra.core.pagination import PageParams
from valyra.main import create_app


@pytest.fixture
def app(monkeypatch):
    # A composição só usa CORS. URL sem credenciais não será aberta pelos testes unitários.
    settings = Settings(database_url="postgresql+psycopg://127.0.0.1/unused", _env_file=None)
    monkeypatch.setattr("valyra.main.get_settings", lambda: settings)
    return create_app()


@pytest.fixture
def client(app, db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    with TestClient(app) as client:
        yield client


@pytest.fixture
def client_com_rota_de_erro(app):
    @app.get("/_teste/erro", name="system_test_error")
    def error():
        raise AppError("NOT_FOUND", "Recurso não encontrado", 404)

    @app.get("/_teste/validacao", name="system_test_validation")
    def validation(params: Annotated[PageParams, Depends()]):
        return {"limit": params.limit, "offset": params.offset}

    with TestClient(app) as client:
        yield client
