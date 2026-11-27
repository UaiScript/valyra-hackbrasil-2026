"""Saldo, resumo (#43), recorrência (#44), atípicos (#45), projeção (#46) e pressão de caixa
(#47), sem PostgreSQL."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from valyra.finance.analytics import (
    ANOMALY_THRESHOLD,
    CategoryTotal,
    ProjectedRecurrence,
    RecurringSeries,
    anomaly_scores,
    detect_recurrences,
    is_anomaly,
    is_cash_pressure,
    month_bounds,
    next_occurrence,
    project_cash,
    realized_balance_cents,
    recurrence_key,
    recurring_series,
    summarize_month,
    variable_daily_cents,
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


# --- gasto atípico (Issue #45, ADR-0010 seção 4) ------------------------------------------


def _scores(magnitudes, categoria=MERCADO):
    movimentos = [(UUID(int=100 + i), -m, categoria) for i, m in enumerate(magnitudes)]
    resultado = anomaly_scores(movimentos)
    return [resultado.get(UUID(int=100 + i)) for i in range(len(magnitudes))]


def test_exemplo_com_mad():
    # Mediana 110, MAD 10: 120 → 0,6745 × 10 / 10 / 4,375 = 0,15417…; 1000 satura em 1.
    assert _scores([100, 100, 110, 120, 1000]) == [
        Decimal("0.0000"),
        Decimal("0.0000"),
        Decimal("0.0000"),
        Decimal("0.1542"),
        Decimal("1.0000"),
    ]


def test_saida_abaixo_da_mediana_tem_score_zero():
    assert _scores([10, 100, 100, 110, 120])[0] == Decimal("0.0000")


def test_mad_zero_usa_desvio_absoluto_medio():
    # MAD = 0; desvio médio em torno da mediana = 100 / 5 = 20.
    # z = 100 / (1,2533 × 20) = 3,98947…; score = z / 4,375 = 0,91188… → 0,9119.
    assert _scores([100, 100, 100, 100, 200]) == [Decimal("0.0000")] * 4 + [Decimal("0.9119")]


def test_todos_iguais_tem_score_zero():
    assert _scores([100] * 5) == [Decimal("0.0000")] * 5


def test_grupo_com_menos_de_cinco_saidas_fica_sem_score():
    assert _scores([100, 100, 100, 5000]) == [None] * 4


def test_entradas_ficam_sem_score_e_nao_contam_no_grupo():
    movimentos = [(UUID(int=1 + i), -100, MERCADO) for i in range(4)]
    movimentos.append((UUID(int=9), 650000, SALARIO))
    movimentos.append((UUID(int=10), 100, MERCADO))  # estorno no mercado: entrada
    assert anomaly_scores(movimentos) == {}


def test_grupos_separados_por_categoria():
    movimentos = [(UUID(int=1 + i), -100, MERCADO) for i in range(5)]
    movimentos += [(UUID(int=20 + i), -100, LAZER) for i in range(4)]
    resultado = anomaly_scores(movimentos)
    assert set(resultado) == {UUID(int=1 + i) for i in range(5)}


def test_mediana_par_no_grupo():
    # Seis saídas: mediana 100, MAD 0, desvio médio 35 / 6.
    assert _scores([100, 100, 100, 100, 105, 130])[-2:] == [Decimal("0.1563"), Decimal("0.9379")]


@pytest.mark.parametrize(
    "magnitudes",
    [[100, 100, 110, 120, 1000], [1, 2, 3, 4, 5, 6, 7], [100, 100, 100, 100, 200], [3] * 9],
)
def test_score_decimal_entre_zero_e_um_com_quatro_casas(magnitudes):
    for score in _scores(magnitudes):
        assert isinstance(score, Decimal)
        assert Decimal(0) <= score <= Decimal(1)
        assert score.as_tuple().exponent == -4


def test_limiar_de_anomalia():
    assert ANOMALY_THRESHOLD == Decimal("0.8")
    assert is_anomaly(Decimal("0.8000")) is True
    assert is_anomaly(Decimal("0.7999")) is False
    assert is_anomaly(None) is False


# --- projeção de caixa (Issue #46, ADR-0010 seção 5) --------------------------------------


def _serie_recorrente(ultima, intervalo=30, valor=-5590, descricao="Netflix.com"):
    return RecurringSeries("-|netflix.com", descricao, valor, intervalo, ultima)


def test_series_a_partir_das_linhas_marcadas():
    linhas = [
        (date(2026, 8, 5), -180000, "Aluguel apartamento", "-|aluguel apartamento"),
        (date(2026, 9, 5), -180000, "Aluguel apartamento", "-|aluguel apartamento"),
        (date(2026, 10, 5), -180000, "ALUGUEL apartamento", "-|aluguel apartamento"),
        (date(2026, 10, 6), -999, "Padaria", None),
    ]
    # Intervalos 31 e 30: mediana 30,5 → 30. A descrição vem da última ocorrência.
    assert recurring_series(linhas) == [
        RecurringSeries(
            "-|aluguel apartamento", "ALUGUEL apartamento", -180000, 30, date(2026, 10, 5)
        )
    ]


def test_mediana_par_da_serie_arredonda_para_baixo_com_sinal():
    datas = [date(2026, 7, 1), date(2026, 7, 31), date(2026, 8, 31), date(2026, 9, 30)]
    valores = [-1000, -1001, -1001, -1000]  # mediana −1000,5 → −1001 (saída maior)
    linhas = [(d, v, "X", "-|x") for d, v in zip(datas, valores, strict=True)]
    (serie,) = recurring_series(linhas)
    # Intervalos 30, 31, 30 → mediana 30; valor −1001.
    assert (serie.interval_days, serie.amount_cents) == (30, -1001)


def test_proxima_ocorrencia_futura():
    assert next_occurrence(_serie_recorrente(date(2026, 10, 10)), HOJE) == date(2026, 11, 9)


def test_recorrencia_atrasada_pula_para_a_proxima_data_futura():
    # Última em 01/09: 01/10 e 31/10 já passaram sem acontecer; a próxima é 30/11.
    assert next_occurrence(_serie_recorrente(date(2026, 9, 1)), HOJE) == date(2026, 11, 30)


def test_ocorrencia_prevista_para_hoje_tambem_pula():
    assert next_occurrence(_serie_recorrente(date(2026, 10, 8)), HOJE) == date(2026, 12, 7)


def test_variavel_diaria_ignora_recorrentes_entradas_e_fora_da_janela():
    inicio = HOJE - timedelta(days=89)
    movimentos = [
        (inicio, -4500, False),
        (HOJE, -4500, False),
        (inicio - timedelta(days=1), -100000, False),  # antes da janela
        (HOJE + timedelta(days=1), -100000, False),  # futuro
        (HOJE, -180000, True),  # recorrente
        (HOJE, 650000, False),  # entrada
    ]
    assert variable_daily_cents(movimentos, HOJE) == -100


def test_variavel_diaria_arredonda_a_magnitude_para_cima():
    assert variable_daily_cents([(HOJE, -9001, False)], HOJE) == -101
    assert variable_daily_cents([(HOJE, -1, False)], HOJE) == -1
    assert variable_daily_cents([], HOJE) == 0


def test_projecao_soma_recorrencias_e_variavel():
    serie = _serie_recorrente(date(2026, 10, 10))  # prevista em 09/11
    projecao = project_cash(10000, HOJE, 3, [serie], -100)
    assert [d.date for d in projecao.items] == [
        date(2026, 11, 8),
        date(2026, 11, 9),
        date(2026, 11, 10),
    ]
    assert [d.balance_cents for d in projecao.items] == [9900, 4210, 4110]
    assert projecao.items[1].recurrences == (ProjectedRecurrence("Netflix.com", -5590),)
    assert projecao.items[1].recurring_cents == -5590
    assert (projecao.min_balance_cents, projecao.min_balance_date) == (4110, date(2026, 11, 10))
    assert (projecao.start_balance_cents, projecao.variable_daily_cents) == (10000, -100)


def test_intervalo_curto_preve_mais_de_uma_ocorrencia_no_horizonte():
    serie = _serie_recorrente(date(2026, 11, 1), intervalo=25)
    projecao = project_cash(0, HOJE, 90, [serie], 0)
    datas = [d.date for d in projecao.items if d.recurrences]
    assert datas == [date(2026, 11, 26), date(2026, 12, 21), date(2027, 1, 15)]


def test_minimo_em_empate_fica_com_o_primeiro_dia():
    projecao = project_cash(500, HOJE, 5, [], 0)
    assert (projecao.min_balance_cents, projecao.min_balance_date) == (500, date(2026, 11, 8))


def test_entrada_recorrente_eleva_o_saldo():
    salario = RecurringSeries("+|salario", "Salario", 650000, 30, date(2026, 10, 9))
    projecao = project_cash(-1000, HOJE, 2, [salario], -100)
    assert [d.balance_cents for d in projecao.items] == [648900, 648800]
    assert (projecao.min_balance_cents, projecao.min_balance_date) == (648800, date(2026, 11, 9))


@pytest.mark.parametrize("dias", [0, 91])
def test_horizonte_fora_da_faixa(dias):
    with pytest.raises(ValueError):
        project_cash(0, HOJE, dias, [], 0)


@pytest.mark.parametrize("inicio,esperado", [(-1, True), (0, False), (1, False)])
def test_pressao_de_caixa_somente_abaixo_de_zero(inicio, esperado):
    # Variável zero: o mínimo é o próprio saldo de partida; zero exato não dispara (< 0).
    assert is_cash_pressure(project_cash(inicio, HOJE, 30, [], 0)) is esperado


def test_budget_status_limites():
    from valyra.finance.analytics import budget_spent_cents, budget_status

    assert budget_status(7999, 10000) == "ok"
    assert budget_status(8000, 10000) == "warning"
    assert budget_status(10000, 10000) == "warning"
    assert budget_status(10001, 10000) == "over"
    assert budget_spent_cents(-4500) == 4500
    assert budget_spent_cents(1200) == 0


def test_daily_allowance_arredonda_para_baixo_e_ignora_estouro():
    from valyra.finance.analytics import daily_allowance

    first, last = date(2026, 11, 1), date(2026, 11, 30)
    assert daily_allowance(1000, 0, date(2026, 11, 30), first, last) == (1, 1000)
    assert daily_allowance(1001, 0, date(2026, 11, 29), first, last) == (2, 500)
    assert daily_allowance(1000, 1500, date(2026, 11, 10), first, last) == (21, 0)
    assert daily_allowance(1000, 0, date(2026, 12, 1), first, last) == (0, None)
