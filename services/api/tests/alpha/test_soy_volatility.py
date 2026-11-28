"""Estudo sintético: publicação, purge e recuperação de uma variável explicativa conhecida."""

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace

from valyra.alpha.domain import estimate_soy_volatility


def histories(count=85, noise=False):
    returns = [Decimal((i * 17 % 13) + 1) / 2 for i in range(count + 5)]
    start = date(2026, 7, 1)
    stocks, climate = [], []
    for i in range(count):
        day = start + timedelta(days=i)
        pub = datetime.combine(day, time(20), UTC)

        def row(key, value, day=day, pub=pub):
            return SimpleNamespace(
                signal_key=f"{key}:{day}",
                revision_id=1,
                observation_date=day,
                value=value,
                published_at=pub,
                published_at_estimated=True,
            )

        stocks.append(row("stock", returns[i]))
        # Driver sintético conhecido no dia t. O teste mede recuperação, não desempenho real.
        value = (
            Decimal(i * 37 % 71)
            if noise
            else sum((v * v for v in returns[i + 1 : i + 6]), Decimal(0)).sqrt() * 100
        )
        climate.append(row("climate", value))
    return stocks, climate, stocks[-1].published_at


def test_recupera_driver_sintetico_e_decomposicao_auditavel():
    stocks, rain, cut = histories()
    result = estimate_soy_volatility(stocks, rain, cut)
    assert result.status == "ready"
    assert Decimal(result.mae_m1_pp) < Decimal(result.mae_m0_pp)
    parts = [
        result.intercept_pct,
        result.market_persistence_pct,
        result.daily_shock_pct,
        result.climate_component_pct,
        result.truncation_adjustment_pct,
    ]
    assert sum(map(Decimal, parts)) == Decimal(result.m1_forecast_pct)
    assert result.eval_windows >= 5


def test_as_of_recusa_revisoes_e_observacoes_posteriores():
    stocks, rain, cut = histories()
    before = estimate_soy_volatility(stocks, rain, cut)
    changed = SimpleNamespace(
        **vars(stocks[-1])
        | {"value": Decimal("900"), "revision_id": 2, "published_at": cut + timedelta(days=1)}
    )
    future = SimpleNamespace(
        **vars(stocks[-1])
        | {
            "signal_key": "stock:future",
            "observation_date": cut.date() + timedelta(days=1),
            "published_at": cut + timedelta(days=1),
            "value": Decimal("999"),
        }
    )
    assert estimate_soy_volatility([*stocks, changed, future], rain, cut) == before


def test_walk_forward_so_ajusta_amostras_cujo_alvo_ja_terminou(monkeypatch):
    from valyra.alpha import domain

    stocks, rain, cut = histories()
    real = domain._ridge
    seen = []

    def inspect(samples, width):
        seen.append(len(samples))
        return real(samples, width)

    monkeypatch.setattr(domain, "_ridge", inspect)
    result = estimate_soy_volatility(stocks, rain, cut)
    # 85 retornos -> 76 janelas concluídas. Primeiro teste em t=23:
    # treino t=4..18, e os alvos terminam até t=23 (gap 5).
    assert seen[:2] == [15, 15]
    assert seen[-2:] == [76, 76]
    assert result.eval_windows == 57


def test_clima_ruidoso_nao_mascara_o_erro():
    stocks, rain, cut = histories(noise=True)
    result = estimate_soy_volatility(stocks, rain, cut)
    assert result.status == "ready"
    assert Decimal(result.mae_m1_pp) >= Decimal(result.mae_m0_pp)
    assert any("não superou" in text for text in result.limitations)


def test_falta_de_serie_ou_de_janelas_nao_vira_zero():
    stocks, rain, cut = histories()
    for market, weather in (([], rain), (stocks, []), (stocks[:20], rain)):
        result = estimate_soy_volatility(market, weather, cut)
        assert result.status == "insufficient_data" and result.reason
        assert result.m1_forecast_pct is None and result.mae_m1_pp is None


def test_revisao_tardia_nao_reescreve_treino_do_primeiro_passo(monkeypatch):
    from valyra.alpha import domain

    stocks, rain, cut = histories()
    seen = []
    real = domain._ridge

    def inspect(samples, width):
        seen.append(list(samples))
        return real(samples, width)

    monkeypatch.setattr(domain, "_ridge", inspect)
    domain.estimate_soy_volatility(stocks, rain, cut)
    original = seen[0]
    seen.clear()
    revised = SimpleNamespace(
        **vars(stocks[10])
        | {"published_at": stocks[50].published_at, "revision_id": 2, "value": Decimal("55")}
    )
    domain.estimate_soy_volatility([*stocks, revised], rain, cut)
    assert seen[0] == original


def test_carga_sem_publicacoes_historicas_nao_vira_backtest():
    stocks, rain, cut = histories()
    for row in [*stocks, *rain]:
        row.published_at = cut
    result = estimate_soy_volatility(stocks, rain, cut)
    assert result.status == "insufficient_data"
    assert result.train_windows == 0 and result.eval_windows == 0
