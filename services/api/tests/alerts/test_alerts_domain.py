"""Regras puras dos alertas (#47): deduplicação e template, sem PostgreSQL."""

from datetime import date
from uuid import UUID

import pytest

from valyra.alerts.domain import cash_dedup_key, cash_pressure_text, format_brl

CONTA = UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.parametrize(
    "cents,texto",
    [
        (0, "R$ 0,00"),
        (5, "R$ 0,05"),
        (-5, "-R$ 0,05"),
        (100, "R$ 1,00"),
        (123456, "R$ 1.234,56"),
        (-123456, "-R$ 1.234,56"),
        (-100000000, "-R$ 1.000.000,00"),
        (2**63 - 1, "R$ 92.233.720.368.547.758,07"),
    ],
)
def test_format_brl_sem_float(cents, texto):
    assert format_brl(cents) == texto


def test_dedup_key_usa_o_mes_de_hoje():
    assert cash_dedup_key(CONTA, date(2026, 11, 7)) == f"cash:{CONTA}:2026-11"
    assert cash_dedup_key(CONTA, date(2026, 11, 30)) == cash_dedup_key(CONTA, date(2026, 11, 1))
    assert cash_dedup_key(CONTA, date(2027, 1, 1)) == f"cash:{CONTA}:2027-01"


def test_template_so_com_numeros_calculados():
    titulo, mensagem = cash_pressure_text(-4590, date(2026, 11, 20), 30)
    assert titulo == "Saldo previsto negativo"
    assert mensagem == (
        "A projeção dos próximos 30 dias indica saldo mínimo de -R$ 45,90 em 20/11/2026."
    )
