"""Cálculos puros do Finance: saldo realizado e resumo mensal (Issue #43, ADR-0010).

Sem banco, HTTP ou relógio: "hoje" chega como parâmetro para os testes fixarem a data.
Dinheiro em centavos inteiros, com sinal: entrada positiva, saída negativa.
"""

import calendar
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from uuid import UUID

# Ano de 1000 a 9999: anos com zeros à esquerda não aparecem nos dados e complicariam a validação.
MONTH_PATTERN = r"([1-9][0-9]{3})-(0[1-9]|1[0-2])"
_MONTH = re.compile(MONTH_PATTERN)


@dataclass(frozen=True)
class CategoryTotal:
    category_id: UUID
    total_cents: int
    count: int


@dataclass(frozen=True)
class MonthSummary:
    income_cents: int
    expenses_cents: int
    net_cents: int
    categories: tuple[CategoryTotal, ...]


def realized_balance_cents(
    balance_cents: int,
    balance_as_of: date,
    movements: Iterable[tuple[date, int]],
    on: date,
) -> int | None:
    """Saldo realizado ao fim de `on` a partir do saldo de fechamento de `balance_as_of`."""
    if on < balance_as_of:
        # O fechamento não permite reconstruir datas anteriores: o saldo fica indisponível.
        return None
    # Movimentações da própria data de referência já estão no fechamento e não entram de novo;
    # as posteriores a `on` ainda não foram realizadas.
    return balance_cents + sum(
        amount for movement_date, amount in movements if balance_as_of < movement_date <= on
    )


def month_bounds(month: str | None, today: date) -> tuple[date, date]:
    """Primeiro e último dia de `AAAA-MM`; sem mês, usa o mês de `today`."""
    if month is None:
        year, month_number = today.year, today.month
    else:
        match = _MONTH.fullmatch(month)
        if match is None:
            raise ValueError("Mês deve estar no formato AAAA-MM")
        year, month_number = int(match[1]), int(match[2])
    last_day = calendar.monthrange(year, month_number)[1]
    return date(year, month_number, 1), date(year, month_number, last_day)


def summarize_month(
    movements: Iterable[tuple[date, int, UUID]],
    first: date,
    last: date,
    today: date,
) -> MonthSummary:
    """Entradas, saídas e totais por categoria do mês, só com o que já foi realizado."""
    # Data futura não é movimentação realizada, inclusive no mês corrente (ADR-0010, seção 1).
    end = min(last, today)
    income = expenses = 0
    totals: dict[UUID, int] = {}
    counts: dict[UUID, int] = {}
    for movement_date, amount, category_id in movements:
        if not first <= movement_date <= end:
            continue
        if amount > 0:
            income += amount
        else:
            expenses += amount
        totals[category_id] = totals.get(category_id, 0) + amount
        counts[category_id] = counts.get(category_id, 0) + 1
    # Maior impacto primeiro; o id desempata para a ordem não depender da leitura do banco.
    ordered = sorted(totals, key=lambda category_id: (-abs(totals[category_id]), str(category_id)))
    return MonthSummary(
        income_cents=income,
        expenses_cents=expenses,
        net_cents=income + expenses,
        categories=tuple(
            CategoryTotal(category_id=cid, total_cents=totals[cid], count=counts[cid])
            for cid in ordered
        ),
    )
