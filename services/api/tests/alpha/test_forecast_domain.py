"""Previsões Alpha sem banco (ADR-0016): modelos, chances, teste com o passado e visão."""

import math
from datetime import date

import pytest

from valyra.alpha import forecast as f
from valyra.alpha.forecast_reserve import reserve_series

DAY = date(2026, 11, 26)


def _base(day: date = DAY) -> dict[str, list[f.Observation]]:
    keys = [f.IPCA_KEY, f.SELIC_KEY, f.CDI_KEY, f.AGRO_KEY, f.DOLLAR_KEY, *f.STOCK_KEYS]
    raw = {k: reserve_series(k, day) for k in keys}
    raw[f.SELIC_KEY] = f.monthly_last(raw[f.SELIC_KEY])
    raw[f.CDI_KEY] = f.complete_months(
        [f.Observation(p.day, f.cdi_annualized(p.value)) for p in f.monthly_mean(raw[f.CDI_KEY])],
        day,
    )
    return raw


def test_holt_acompanha_tendencia_linear_sem_ruido():
    values = [10 + 0.5 * i for i in range(30)]
    fit = f.fit_holt(values)
    paths = f.simulate_holt(fit, 3, 50, f.rng_for("linear"))
    # Reta sem ruído: os erros do passado são mínimos e os cenários seguem a reta.
    assert all(abs(p[0] - 25.0) < 0.1 for p in paths)
    assert fit.sigma < 0.05


def test_passeio_aleatorio_nao_aposta_em_direcao():
    returns = [0.02, -0.01, 0.015, -0.02, 0.01] * 20  # média positiva no passado
    paths = f.simulate_random_walk(100, returns, 21, 2000, f.rng_for("rw"))
    up = sum(p[-1] > 100 for p in paths) / len(paths)
    # A média do passado é retirada: a chance de alta fica perto de metade.
    assert 0.4 < up < 0.6


def test_ipca_acumula_12_meses_por_juros_compostos():
    assert f._accum([1.0] * 12) == pytest.approx((1.01**12 - 1) * 100)


@pytest.mark.parametrize(
    "profile", ["orcamento-apertado", "comecando-a-investir", "investidor", None]
)
def test_cada_perfil_recebe_previsoes_coerentes(profile):
    base = _base()
    kinds = [spec.kind for spec in f.specs_for(profile)]
    assert kinds == list(f.PROFILE_SPECS.get(profile or "", f.DEFAULT_SPECS))
    for spec in f.specs_for(profile):
        result = f.compute(spec, base, profile)
        band = result.headline
        assert band.p2_5 <= band.p10 <= band.p50 <= band.p90 <= band.p97_5
        assert len(result.fan) == spec.horizon and result.history
        if spec.event is not None:
            assert result.chance is not None and 0 <= result.chance <= 1
        assert result.backtest is not None and 0 <= result.backtest.hits <= result.backtest.trials
        # A visão da Valyra só repete números já calculados: a faixa de 80% aparece no texto.
        digits = 2 if spec.kind == "selic_6m" else 1
        assert f.pct(band.p10, digits) in result.view.text
        assert f.pct(band.p90, digits) in result.view.text


def test_mesma_entrada_gera_os_mesmos_cenarios():
    base = _base()
    first = f.compute(f.SPECS["ipca_12m"], base, None)
    second = f.compute(f.SPECS["ipca_12m"], base, None)
    assert first.headline == second.headline and first.chance == second.chance


def test_selic_simulada_anda_em_passos_de_0_25():
    result = f.compute(f.SPECS["selic_6m"], _base(), None)
    for point in result.fan:
        for value in (point.band.p10, point.band.p50, point.band.p90):
            assert math.isclose(value / 0.25, round(value / 0.25), abs_tol=1e-9)


def test_teste_com_o_passado_confere_faixa_contra_o_que_aconteceu():
    # Série constante: a faixa colapsa no próprio valor e acerta todas as vezes.
    values = [5.0] * 40
    bt = f._holt_backtest(values, 3, "3 meses", "constante")
    assert bt is not None and bt.hits == bt.trials == 12
    assert bt.model_mae == pytest.approx(0) and bt.naive_mae == pytest.approx(0)


def test_mes_corrente_incompleto_sai_da_media_do_cdi():
    points = [f.Observation(date(2026, 10, 1), 14.0), f.Observation(date(2026, 11, 1), 14.1)]
    assert f.complete_months(points, date(2026, 11, 26)) == points[:1]
    assert f.complete_months(points, date(2026, 11, 30)) == points


@pytest.mark.parametrize(
    ("chance", "stance"), [(0.8, "atencao"), (0.45, "neutra"), (0.1, "favoravel")]
)
def test_visao_da_inflacao_segue_a_chance_de_passar_do_teto(chance, stance):
    band = f.Band(3, 3.5, 4, 4.5, 5)
    view = f.valyra_view(f.SPECS["ipca_12m"], band, chance, 4.4, "orcamento-apertado")
    assert view.stance == stance
    assert f"{round(chance * 100)}%" in view.text and "Para o seu orçamento" in view.text


def test_zero_arredondado_sai_sem_sinal():
    assert f.pct(-0.0001) == "0,0"
