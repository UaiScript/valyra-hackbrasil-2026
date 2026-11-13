"""Fixtures isoladas: nunca usam DATABASE_URL como destino da limpeza."""

import os
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from tests.db.safety import assert_safe_database, database_identity
from valyra.core.config import Settings
from valyra.core.db import Base, User, get_session
from valyra.finance.models import Account, Category, ImportBatch, Transaction
from valyra.main import create_app

API_ROOT = Path(__file__).resolve().parents[1]


def migration_config(connection=None) -> Config:
    config = Config(str(API_ROOT / "alembic.ini"))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


@pytest.fixture(scope="session")
def test_destination():
    raw_url = os.environ.get("TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip(
            "Integração bloqueada: TEST_DATABASE_URL não definida; PostgreSQL dedicado exigido"
        )
    url = make_url(raw_url)
    # Validação estática antes até de abrir conexão; nunca há fallback para o banco do app.
    assert_safe_database(url, (url.database, None, None), None)
    try:
        application_url = Settings().database_url
    except ValidationError as exc:
        if any(e["loc"] != ("database_url",) or e["type"] != "missing" for e in exc.errors()):
            raise
        application_url = None
    app_identity = None
    if application_url:
        app_engine = create_engine(application_url)
        try:
            with app_engine.connect() as connection:
                app_identity = database_identity(connection)
        finally:
            app_engine.dispose()
    return url, app_identity


@contextmanager
def isolated_engine(destination):
    url, app_identity = destination
    # Schema aleatório permite testar um banco lógico vazio sem apagar dados preexistentes.
    schema = f"valyra_test_{uuid4().hex}"
    bootstrap = create_engine(url)
    try:
        with bootstrap.begin() as connection:
            assert_safe_database(url, database_identity(connection), app_identity)
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
    finally:
        bootstrap.dispose()
    engine = create_engine(
        url,
        connect_args={"options": f"-c search_path={schema} -c timezone=UTC"},
        execution_options={"valyra_test_schema": schema},
    )
    try:
        yield engine
    finally:
        try:
            with engine.begin() as connection:
                assert_safe_database(url, database_identity(connection), app_identity)
                connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        finally:
            engine.dispose()


@pytest.fixture
def empty_engine(test_destination):
    with isolated_engine(test_destination) as engine:
        yield engine


@pytest.fixture(scope="session")
def test_engine(test_destination):
    with isolated_engine(test_destination) as engine:
        with engine.begin() as connection:
            command.upgrade(migration_config(connection), "head")
        yield engine


@pytest.fixture
def db_session(test_engine, test_destination):
    url, app_identity = test_destination
    schema = test_engine.get_execution_options()["valyra_test_schema"]
    with test_engine.begin() as connection:
        assert_safe_database(url, database_identity(connection), app_identity)
        if connection.exec_driver_sql("SELECT current_schema()").scalar_one() != schema:
            raise RuntimeError("Schema efetivo difere do schema isolado de testes")
        # Lista explícita pela metadata: alembic_version não participa do TRUNCATE.
        tables = ", ".join(f'"{schema}"."{table.name}"' for table in Base.metadata.sorted_tables)
        connection.exec_driver_sql(f"TRUNCATE TABLE {tables}")
    with Session(test_engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def reference_rows(db_session):
    user = User(name="Teste")
    db_session.add(user)
    db_session.flush()
    account = Account(
        user_id=user.id, name="Conta teste", balance_cents=500000, balance_as_of=date(2026, 11, 1)
    )
    category = Category(slug="outros", name="Outros", kind="expense")
    db_session.add_all([account, category])
    db_session.flush()
    batch = ImportBatch(account_id=account.id, file_name="teste.csv")
    db_session.add(batch)
    db_session.flush()
    return {"user": user, "account": account, "category": category, "batch": batch}


@pytest.fixture
def insert_transaction(db_session, reference_rows):
    def insert(**overrides):
        values = {
            "account_id": reference_rows["account"].id,
            "import_batch_id": reference_rows["batch"].id,
            "date": date(2026, 11, 3),
            "description": "Movimentação sintética",
            "amount_cents": -8990,
            "category_id": reference_rows["category"].id,
            "predicted_category_id": reference_rows["category"].id,
            "category_source": "rule",
            "row_hash": uuid4().hex,
        }
        transaction = Transaction(**(values | overrides))
        db_session.add(transaction)
        db_session.flush()
        return transaction

    return insert


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
