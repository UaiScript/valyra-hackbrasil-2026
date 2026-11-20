"""Saldo realizado e resumo mensal (Issue #43, ADR-0010 seção 1), sem PostgreSQL."""

from datetime import date
from uuid import UUID

import pytest

from valyra.finance.analytics import (
    CategoryTotal,
    month_bounds,
    realized_balance_cents,
    summarize_month,
)

MERCADO = UUID("00000000-0000-0000-0000-00000000000a")
SALARIO = UUID("00000000-0000-0000-0000-00000000000b")
LAZER = UUID("00000000-0000-0000-0000-00000000000c")
HOJE = date(2026, 11, 7)


# --- saldo realizado ----------------------------------------------------------------------


def test_exemplo_da_modelagem():
    movimentos = [(date(2026, 11, 2), -12990)]
    assert realized_balance_cents(500000, date(2026, 11, 1), movimentos, HOJE) == 487010


def test_data_futura_fica_fora_do_realizado():
    movimentos = [(date(2026, 11, 2), -12990), (date(2026, 11, 10), -20000)]
    assert realized_balance_cents(500000, date(2026, 11, 1), movimentos, HOJE) == 487010


def test_movimento_do_proprio_dia_de_hoje_entra():
    movimentos = [(HOJE, -100)]
    assert realized_balance_cents(500000, date(2026, 11, 1), movimentos, HOJE) == 499900


def test_movimento_na_data_de_referencia_ou_antes_nao_entra_de_novo():
    # O fechamento de 01/11 já inclui o próprio dia; o histórico anterior também está nele.
    movimentos = [(date(2026, 11, 1), -5000), (date(2026, 10, 15), -7000)]
    assert realized_balance_cents(500000, date(2026, 11, 1), movimentos, HOJE) == 500000


def test_hoje_igual_a_referencia_devolve_a_propria_referencia():
    assert realized_balance_cents(500000, HOJE, [(HOJE, -1)], HOJE) == 500000


def test_referencia_futura_deixa_saldo_indisponivel():
    assert realized_balance_cents(500000, date(2026, 11, 8), [], HOJE) is None


def test_saldo_pode_ficar_negativo():
    assert realized_balance_cents(100, date(2026, 11, 1), [(date(2026, 11, 2), -250)], HOJE) == -150


# --- mês ----------------------------------------------------------------------------------


def test_mes_padrao_e_o_mes_de_hoje():
    assert month_bounds(None, HOJE) == (date(2026, 11, 1), date(2026, 11, 30))


@pytest.mark.parametrize(
    ("mes", "limites"),
    [
        ("2026-12", (date(2026, 12, 1), date(2026, 12, 31))),
        ("2028-02", (date(2028, 2, 1), date(2028, 2, 29))),
        ("2026-02", (date(2026, 2, 1), date(2026, 2, 28))),
    ],
)
def test_limites_do_mes(mes, limites):
    assert month_bounds(mes, HOJE) == limites


@pytest.mark.parametrize(
    "mes", ["2026-13", "2026-00", "2026-1", "26-11", "0999-01", "2026-11-01", ""]
)
def test_mes_invalido(mes):
    with pytest.raises(ValueError):
        month_bounds(mes, HOJE)


# --- resumo mensal ------------------------------------------------------------------------


def test_resumo_soma_entradas_saidas_e_categorias_com_sinal():
    movimentos = [
        (date(2026, 11, 2), -12990, MERCADO),
        (date(2026, 11, 3), -5000, MERCADO),
        (date(2026, 11, 5), 350000, SALARIO),
        (date(2026, 11, 6), -8000, LAZER),
    ]
    resumo = summarize_month(movimentos, date(2026, 11, 1), date(2026, 11, 30), HOJE)
    assert resumo.income_cents == 350000
    assert resumo.expenses_cents == -25990
    assert resumo.net_cents == 324010
    assert resumo.categories == (
        CategoryTotal(SALARIO, 350000, 1),
        CategoryTotal(MERCADO, -17990, 2),
        CategoryTotal(LAZER, -8000, 1),
    )


def test_resumo_ignora_outros_meses_e_datas_futuras():
    movimentos = [
        (date(2026, 10, 31), -1, MERCADO),
        (date(2026, 11, 1), -2, MERCADO),
        (date(2026, 11, 7), -4, MERCADO),
        (date(2026, 11, 8), -8, MERCADO),
        (date(2026, 12, 1), -16, MERCADO),
    ]
    resumo = summarize_month(movimentos, date(2026, 11, 1), date(2026, 11, 30), HOJE)
    assert resumo.expenses_cents == -6
    assert resumo.categories == (CategoryTotal(MERCADO, -6, 2),)


def test_mes_passado_inteiro_entra():
    movimentos = [(date(2026, 10, 1), -1, MERCADO), (date(2026, 10, 31), -2, MERCADO)]
    resumo = summarize_month(movimentos, date(2026, 10, 1), date(2026, 10, 31), HOJE)
    assert resumo.expenses_cents == -3


def test_mes_futuro_fica_vazio():
    movimentos = [(date(2026, 12, 1), -1, MERCADO)]
    resumo = summarize_month(movimentos, date(2026, 12, 1), date(2026, 12, 31), HOJE)
    assert (resumo.income_cents, resumo.expenses_cents, resumo.net_cents) == (0, 0, 0)
    assert resumo.categories == ()


def test_empate_de_magnitude_e_ordenado_pelo_id():
    movimentos = [(date(2026, 11, 2), -500, LAZER), (date(2026, 11, 2), 500, SALARIO)]
    resumo = summarize_month(movimentos, date(2026, 11, 1), date(2026, 11, 30), HOJE)
    # SALARIO (...0b) vem antes de LAZER (...0c), independentemente da ordem de entrada.
    assert [c.category_id for c in resumo.categories] == [SALARIO, LAZER]


def test_valores_continuam_inteiros():
    resumo = summarize_month(
        [(date(2026, 11, 2), -1, MERCADO)], date(2026, 11, 1), date(2026, 11, 30), HOJE
    )
    assert all(
        type(v) is int for v in (resumo.income_cents, resumo.expenses_cents, resumo.net_cents)
    )
