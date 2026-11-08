from decimal import Decimal

import pytest
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.engine import make_url

from tests.db.safety import assert_safe_database
from valyra.core.config import Settings
from valyra.finance.models import MoneyCents


@pytest.mark.parametrize(
    "url,identity,app_identity",
    [
        ("sqlite:///valyra_test", ("valyra_test", None, None), None),
        ("postgresql+psycopg://localhost/valyra", ("valyra", "127.0.0.1", 5432), None),
        ("postgresql+psycopg://localhost/valyra_test", ("valyra", "127.0.0.1", 5432), None),
        (
            "postgresql+psycopg://alias/valyra_test",
            ("valyra_test", "127.0.0.1", 5432),
            ("valyra_test", "127.0.0.1", 5432),
        ),
    ],
)
def test_cleanup_refuses_unsafe_destination(url, identity, app_identity):
    with pytest.raises(RuntimeError):
        assert_safe_database(make_url(url), identity, app_identity)


def test_cleanup_accepts_separate_effective_database():
    assert_safe_database(
        make_url("postgresql+psycopg://localhost/valyra_test"),
        ("valyra_test", "127.0.0.1", 5432),
        ("valyra", "127.0.0.1", 5432),
    )


@pytest.mark.parametrize("value", [10.5, "1000", Decimal("1.00"), True])
def test_money_bind_refuses_implicit_conversion(value):
    with pytest.raises(ValueError, match="inteiro em centavos"):
        MoneyCents().bind_processor(dialect())(value)


def test_money_bind_keeps_exact_integer():
    assert MoneyCents().bind_processor(dialect())(9007199254740993) == 9007199254740993


def test_demo_configuration_is_typed_and_configurable():
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://localhost/unused",
        demo_user_id="00000000-0000-0000-0000-000000000002",
    )
    assert str(settings.demo_user_id) == "00000000-0000-0000-0000-000000000002"
