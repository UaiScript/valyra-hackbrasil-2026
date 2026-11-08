"""Composição dos modelos fora de core; uma única metadata para todo o histórico."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from valyra.core.config import get_settings
from valyra.core.db import Base
from valyra.finance import models  # noqa: F401 -- registra as cinco tabelas na Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def migrate(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url=config.attributes.get("database_url") or get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()
elif (connection := config.attributes.get("connection")) is not None:
    migrate(connection)
else:
    engine = create_engine(get_settings().database_url, poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            migrate(connection)
    finally:
        engine.dispose()
