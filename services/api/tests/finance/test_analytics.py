"""Saldo, resumo mensal (#43) e recorrência (#44), ADR-0010, sem PostgreSQL."""

from datetime import date
from uuid import UUID

import pytest

from valyra.finance.analytics import (
    CategoryTotal,
    detect_recurrences,
    month_bounds,
    realized_balance_cents,
    recurrence_key,
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


# --- recorrência (Issue #44, ADR-0010 seção 3) --------------------------------------------


def _ids(n: int) -> list[UUID]:
    return [UUID(int=i + 1) for i in range(n)]


def _serie(datas, valores, descricao="netflix.com"):
    if isinstance(valores, int):
        valores = [valores] * len(datas)
    return [
        (movement_id, d, v, descricao)
        for movement_id, d, v in zip(_ids(len(datas)), datas, valores, strict=True)
    ]


MENSAL = [date(2026, 8, 10), date(2026, 9, 10), date(2026, 10, 10)]


def test_assinatura_mensal_detectada():
    resultado = detect_recurrences(_serie(MENSAL, -5590))
    assert resultado == {movement_id: "-|netflix.com" for movement_id in _ids(3)}


def test_salario_detectado_com_chave_de_entrada():
    datas = [date(2026, 8, 5), date(2026, 9, 5), date(2026, 10, 5)]
    resultado = detect_recurrences(_serie(datas, 650000, "salario acme tecnologia"))
    assert set(resultado.values()) == {"+|salario acme tecnologia"}
    assert len(resultado) == 3


@pytest.mark.parametrize(
    "segunda",
    [date(2026, 9, 4), date(2026, 9, 5)],  # 25 dias depois de 10/08, e 26
)
def test_intervalo_minimo_inclusivo(segunda):
    datas = [date(2026, 8, 10), segunda, segunda.replace(month=10)]
    assert len(detect_recurrences(_serie(datas, -100))) == 3


def test_intervalo_maximo_inclusivo():
    datas = [date(2026, 8, 1), date(2026, 9, 5), date(2026, 10, 10)]  # 35 e 35 dias
    assert len(detect_recurrences(_serie(datas, -100))) == 3


@pytest.mark.parametrize(
    "datas",
    [
        [date(2026, 8, 10), date(2026, 9, 3), date(2026, 10, 3)],  # 24 dias
        [date(2026, 8, 1), date(2026, 9, 6), date(2026, 10, 6)],  # 36 dias
        [date(2026, 8, 10), date(2026, 9, 10), date(2026, 11, 10)],  # mês pulado
    ],
)
def test_intervalo_irregular_nao_detectado(datas):
    assert detect_recurrences(_serie(datas, -100)) == {}


def test_um_intervalo_irregular_derruba_a_serie_inteira():
    datas = [*MENSAL, date(2026, 10, 20)]
    assert detect_recurrences(_serie(datas, -100)) == {}


def test_duas_ocorrencias_nao_bastam():
    assert detect_recurrences(_serie(MENSAL[:2], -100)) == {}


def test_tres_ocorrencias_em_dois_meses_nao_bastam():
    # Intervalos de 25 dias cabem na regra, mas 01/01 e 26/01 caem no mesmo mês.
    datas = [date(2026, 1, 1), date(2026, 1, 26), date(2026, 2, 20)]
    assert detect_recurrences(_serie(datas, -100)) == {}


def test_tolerancia_de_dez_por_cento_inclusiva():
    # Mediana 1000: 900 e 1100 ficam exatamente no limite.
    assert len(detect_recurrences(_serie(MENSAL, [-900, -1000, -1100]))) == 3


def test_valor_fora_da_tolerancia_nao_detectado():
    assert detect_recurrences(_serie(MENSAL, [-1000, -1000, -1101])) == {}


def test_mediana_par_sem_float():
    # Mediana (1000 + 1010) / 2 = 1005; 1105,5 seria o limite, então 1105 entra e 1106 não.
    datas = [*MENSAL, date(2026, 11, 10)]
    assert len(detect_recurrences(_serie(datas, [-1000, -1010, -905, -1105]))) == 4
    assert detect_recurrences(_serie(datas, [-1000, -1010, -905, -1106])) == {}


def test_sinais_opostos_formam_series_separadas():
    cobrancas = _serie(MENSAL, -100)
    estorno = [(UUID(int=99), date(2026, 9, 12), 100, "netflix.com")]
    resultado = detect_recurrences(cobrancas + estorno)
    assert UUID(int=99) not in resultado
    assert len(resultado) == 3


def test_descricoes_diferentes_nao_se_misturam_e_ordem_da_entrada_nao_importa():
    netflix = _serie(MENSAL, -5590)
    spotify = [
        (UUID(int=10 + i), d, -2190, "spotify premium") for i, d in enumerate(reversed(MENSAL))
    ]
    resultado = detect_recurrences(list(reversed(netflix)) + spotify)
    assert sorted(set(resultado.values())) == ["-|netflix.com", "-|spotify premium"]
    assert len(resultado) == 6


def test_chave_da_serie():
    assert recurrence_key("aluguel apartamento", -180000) == "-|aluguel apartamento"
    assert recurrence_key("pix recebido", 1) == "+|pix recebido"
