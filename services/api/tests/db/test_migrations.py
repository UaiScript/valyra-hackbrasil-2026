import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from tests.conftest import migration_config

FINANCE_TABLES = {
    "users",
    "accounts",
    "import_batches",
    "import_rejections",
    "categories",
    "transactions",
}
TABLES = FINANCE_TABLES | {"alerts", "budgets"}


def test_single_migration_head():
    heads = ScriptDirectory.from_config(migration_config()).get_heads()
    assert len(heads) == 1, f"Esperada uma cabeça Alembic; encontradas: {heads}"


def test_initial_migration_is_in_history():
    history = ScriptDirectory.from_config(migration_config()).walk_revisions()
    assert any(revision.revision == "0001_finance_inicial" for revision in history)


def test_alerts_migration_follows_finance():
    revision = ScriptDirectory.from_config(migration_config()).get_revision("0002_alerts")
    assert revision.down_revision == "0001_finance_inicial"


def test_budgets_migration_follows_alerts():
    revision = ScriptDirectory.from_config(migration_config()).get_revision("0003_budgets")
    assert revision.down_revision == "0002_alerts"


@pytest.mark.postgres
def test_upgrade_from_empty_and_check(empty_engine):
    with empty_engine.begin() as connection:
        assert inspect(connection).get_table_names() == []
        config = migration_config(connection)
        command.upgrade(config, "head")
        assert set(inspect(connection).get_table_names()) == TABLES | {"alembic_version"}
        command.check(config)


@pytest.mark.postgres
def test_downgrade_and_upgrade_only_in_disposable_schema(empty_engine):
    with empty_engine.begin() as connection:
        config = migration_config(connection)
        command.upgrade(config, "head")
        command.downgrade(config, "base")
        assert set(inspect(connection).get_table_names()) == {"alembic_version"}
        command.upgrade(config, "head")
        command.check(config)


@pytest.mark.postgres
def test_alerts_downgrade_keeps_finance(empty_engine):
    with empty_engine.begin() as connection:
        config = migration_config(connection)
        command.upgrade(config, "head")
        command.downgrade(config, "0001_finance_inicial")
        assert set(inspect(connection).get_table_names()) == FINANCE_TABLES | {"alembic_version"}
        command.upgrade(config, "head")
        assert set(inspect(connection).get_table_names()) == TABLES | {"alembic_version"}
        command.check(config)


@pytest.mark.postgres
def test_budgets_downgrade_keeps_alerts(empty_engine):
    with empty_engine.begin() as connection:
        config = migration_config(connection)
        command.upgrade(config, "head")
        command.downgrade(config, "0002_alerts")
        tables = FINANCE_TABLES | {"alerts", "alembic_version"}
        assert set(inspect(connection).get_table_names()) == tables
        command.upgrade(config, "head")
        command.check(config)


@pytest.mark.postgres
def test_cleanup_keeps_migration_version(db_session):
    version = db_session.connection().exec_driver_sql("SELECT version_num FROM alembic_version")
    expected_head = ScriptDirectory.from_config(migration_config()).get_current_head()
    assert version.scalar_one() == expected_head
