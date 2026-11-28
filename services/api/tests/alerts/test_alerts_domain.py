"""Precisão monetária dos alertas; deduplicação e texto são cobertos pela integração."""

import pytest

from valyra.alerts.domain import format_brl


@pytest.mark.parametrize(
    "cents,texto",
    [(-123456, "-R$ 1.234,56"), (2**63 - 1, "R$ 92.233.720.368.547.758,07")],
)
def test_format_brl_sem_float(cents, texto):
    assert format_brl(cents) == texto
