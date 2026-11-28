"""Saldo, resumo (#43), recorrência (#44), atípicos (#45), projeção (#46) e pressão de caixa
(#47), sem PostgreSQL."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from valyra.finance.analytics import (
    ANOMALY_THRESHOLD,
    RecurringSeries,
    anomaly_scores,
    detect_recurrences,
    is_anomaly,
    is_cash_pressure,
    next_occurrence,
    project_cash,
    realized_balance_cents,
    recurring_series,
    summarize_month,
    variable_daily_cents,
)

MERCADO = UUID("00000000-0000-0000-0000-00000000000a")
HOJE = date(2026, 11, 7)


# --- saldo realizado ----------------------------------------------------------------------


def test_movimento_na_data_de_referencia_ou_antes_nao_entra_de_novo():
    # O fechamento de 01/11 já inclui o próprio dia; o histórico anterior também está nele.
    movimentos = [(date(2026, 11, 1), -5000), (date(2026, 10, 15), -7000)]
    assert realized_balance_cents(500000, date(2026, 11, 1), movimentos, HOJE) == 500000


# --- mês ----------------------------------------------------------------------------------


# --- resumo mensal ------------------------------------------------------------------------


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


@pytest.mark.parametrize(
    "segunda",
    [date(2026, 9, 4)],  # 25 dias depois de 10/08, e 26
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
        [date(2026, 8, 10), date(2026, 9, 3), date(2026, 10, 3)],
        [date(2026, 8, 1), date(2026, 9, 6), date(2026, 10, 6)],
    ],
)
def test_intervalo_irregular_nao_detectado(datas):
    assert detect_recurrences(_serie(datas, -100)) == {}


def test_tres_ocorrencias_em_dois_meses_nao_bastam():
    # Intervalos de 25 dias cabem na regra, mas 01/01 e 26/01 caem no mesmo mês.
    datas = [date(2026, 1, 1), date(2026, 1, 26), date(2026, 2, 20)]
    assert detect_recurrences(_serie(datas, -100)) == {}


def test_tolerancia_de_dez_por_cento_inclusiva():
    # Mediana 1000: 900 e 1100 ficam exatamente no limite.
    assert len(detect_recurrences(_serie(MENSAL, [-900, -1000, -1100]))) == 3


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


# --- gasto atípico (Issue #45, ADR-0010 seção 4) ------------------------------------------


def _scores(magnitudes, categoria=MERCADO):
    movimentos = [(UUID(int=100 + i), -m, categoria) for i, m in enumerate(magnitudes)]
    resultado = anomaly_scores(movimentos)
    return [resultado.get(UUID(int=100 + i)) for i in range(len(magnitudes))]


def test_mad_zero_usa_desvio_absoluto_medio():
    # MAD = 0; desvio médio em torno da mediana = 100 / 5 = 20.
    # z = 100 / (1,2533 × 20) = 3,98947…; score = z / 4,375 = 0,91188… → 0,9119.
    assert _scores([100, 100, 100, 100, 200]) == [Decimal("0.0000")] * 4 + [Decimal("0.9119")]


def test_mediana_par_no_grupo():
    # Seis saídas: mediana 100, MAD 0, desvio médio 35 / 6.
    assert _scores([100, 100, 100, 100, 105, 130])[-2:] == [Decimal("0.1563"), Decimal("0.9379")]


@pytest.mark.parametrize(
    "magnitudes",
    [[1, 2, 3, 4, 5, 6, 7]],
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


def test_mediana_par_da_serie_arredonda_para_baixo_com_sinal():
    datas = [date(2026, 7, 1), date(2026, 7, 31), date(2026, 8, 31), date(2026, 9, 30)]
    valores = [-1000, -1001, -1001, -1000]  # mediana −1000,5 → −1001 (saída maior)
    linhas = [(d, v, "X", "-|x") for d, v in zip(datas, valores, strict=True)]
    (serie,) = recurring_series(linhas)
    # Intervalos 30, 31, 30 → mediana 30; valor −1001.
    assert (serie.interval_days, serie.amount_cents) == (30, -1001)


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
    # Mês futuro conta todos os dias dele, não os dias a partir de hoje.
    assert daily_allowance(3000, 0, date(2026, 10, 20), first, last) == (30, 100)
