"""Séries de reserva sintéticas para as previsões (ADR-0016).

Entram só quando a coleta ainda não tem histórico suficiente para uma série, por exemplo
logo depois de ligar a coleta ou com a fonte fora do ar na demo. São geradas aqui, com
semente fixa, e nunca gravadas no banco: a tela e a IA as marcam como "dados de reserva
sintéticos", e a IA não as recebe como evidência. Os níveis imitam a ordem de grandeza das
séries públicas para a demo fazer sentido, mas não são dados reais.
"""

from __future__ import annotations

import math
import random
from datetime import date, timedelta

from valyra.alpha.forecast import (
    AGRO_KEY,
    CDI_KEY,
    DOLLAR_KEY,
    IPCA_KEY,
    SELIC_KEY,
    STOCK_KEYS,
    Observation,
    add_months,
    month_start,
)

MONTHS = 72
BUSINESS_DAYS = 260


def _business_days_until(end: date, count: int) -> list[date]:
    days: list[date] = []
    day = end
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day -= timedelta(days=1)
    return list(reversed(days))


def _months_until(end: date, count: int) -> list[date]:
    last = month_start(end)
    return [add_months(last, -i) for i in range(count, 0, -1)]


def _selic_path(months: list[date], rng: random.Random) -> list[float]:
    # Ciclos de alta e queda, com o Copom mudando a meta em passos de 0,25 a 1 ponto.
    level, out = 11.75, []
    for i, _ in enumerate(months):
        if i % 2 == 0:
            drift = 0.5 if (i // 18) % 2 == 0 else -0.5
            move = drift + rng.choice((-0.25, 0.0, 0.0, 0.25))
            level = min(15.0, max(9.0, level + move))
        out.append(level)
    return out


def reserve_series(key: str, as_of: date) -> list[Observation]:
    """Histórico sintético da série `key` terminando no dia (ou mês anterior) do corte."""
    rng = random.Random(f"reserva:{key}")
    if key == IPCA_KEY:
        months = _months_until(month_start(as_of) - timedelta(days=1), MONTHS)
        # Sazonalidade leve (alimentos no início do ano) em torno de 0,38% ao mês.
        return [
            Observation(m, round(0.38 + 0.18 * math.cos((m.month - 2) / 12 * 2 * math.pi)
                                 + rng.gauss(0, 0.14), 2))
            for m in months
        ]  # fmt: skip
    if key == SELIC_KEY:
        months = _months_until(as_of, MONTHS)
        return [Observation(m, v) for m, v in zip(months, _selic_path(months, rng), strict=True)]
    if key == CDI_KEY:
        months = _months_until(as_of, MONTHS)
        selic = _selic_path(months, random.Random(f"reserva:{SELIC_KEY}"))
        out = []
        for month, rate in zip(months, selic, strict=True):
            daily = ((1 + (rate - 0.1) / 100) ** (1 / 252) - 1) * 100
            day = month
            while day.month == month.month and day <= as_of:
                if day.weekday() < 5:
                    out.append(Observation(day, round(daily, 6)))
                day += timedelta(days=1)
        return out
    if key == AGRO_KEY:
        months = _months_until(month_start(as_of) - timedelta(days=1), MONTHS)
        level, out = 280.0, []
        for month in months:
            level *= math.exp(rng.gauss(0.003, 0.035))
            out.append(Observation(month, round(level, 2)))
        return out
    if key == DOLLAR_KEY:
        days = _business_days_until(as_of, BUSINESS_DAYS)
        level, out = 5.3, []
        for day in days:
            level *= math.exp(rng.gauss(0, 0.0075))
            out.append(Observation(day, round(level, 4)))
        return out
    if key in STOCK_KEYS:
        days = _business_days_until(as_of, BUSINESS_DAYS)
        vol = {0: 1.9, 1: 1.7, 2: 1.3, 3: 3.4}[STOCK_KEYS.index(key)]
        return [Observation(d, round(rng.gauss(0.03, vol), 2)) for d in days]
    raise KeyError(key)
