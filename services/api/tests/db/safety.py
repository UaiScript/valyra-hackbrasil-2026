"""Guardas executadas antes de criar schema ou limpar dados de testes."""

from sqlalchemy import Connection
from sqlalchemy.engine import URL

DatabaseIdentity = tuple[str, str | None, int | None]


def database_identity(connection: Connection) -> DatabaseIdentity:
    row = connection.exec_driver_sql(
        "SELECT current_database(), inet_server_addr()::text, inet_server_port()"
    ).one()
    return tuple(row)


def assert_safe_database(
    url: URL, identity: DatabaseIdentity, application_identity: DatabaseIdentity | None
) -> None:
    if url.drivername != "postgresql+psycopg":
        raise RuntimeError("Testes exigem PostgreSQL com psycopg")
    if not url.database or not url.database.endswith("_test"):
        raise RuntimeError("O banco dedicado deve ter nome terminado em _test")
    if identity[0] != url.database:
        raise RuntimeError("Identidade efetiva do banco difere de TEST_DATABASE_URL")
    if identity == application_identity:
        raise RuntimeError("Banco efetivo de testes coincide com o banco da aplicação")
