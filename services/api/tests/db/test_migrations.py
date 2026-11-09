import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from tests.conftest import migration_config

TABLES = {"users", "accounts", "import_batches", "import_rejections", "categories", "transactions"}


def test_single_migration_head():
    heads = ScriptDirectory.from_config(migration_config()).get_heads()
    assert len(heads) == 1, f"Esperada uma cabeça Alembic; encontradas: {heads}"


def test_initial_migration_is_in_history():
    history = ScriptDirectory.from_config(migration_config()).walk_revisions()
    assert any(revision.revision == "0001_finance_inicial" for revision in history)


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
def test_cleanup_keeps_migration_version(db_session):
    version = db_session.connection().exec_driver_sql("SELECT version_num FROM alembic_version")
    expected_head = ScriptDirectory.from_config(migration_config()).get_current_head()
    assert version.scalar_one() == expected_head
