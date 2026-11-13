"""Fixtures HTTP; conexão real ocorre somente no teste que pede db_session."""

from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from valyra.core.errors import AppError
from valyra.core.pagination import PageParams


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
