"""Cálculos puros do Finance: saldo, resumo (#43), recorrência (#44) e atípicos (#45), ADR-0010.

Sem banco, HTTP ou relógio: "hoje" chega como parâmetro para os testes fixarem a data.
Dinheiro em centavos inteiros, com sinal: entrada positiva, saída negativa.
"""

import calendar
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal
from itertools import pairwise
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


# Recorrência (ADR-0010, seção 3). Mudar estes limiares exige atualizar a ADR e os testes.
RECURRENCE_MIN_OCCURRENCES = 3
RECURRENCE_MIN_DAYS = 25
RECURRENCE_MAX_DAYS = 35
# ±10%: |v − med| × 10 <= |med|, comparado em inteiros.
RECURRENCE_TOLERANCE_DIVISOR = 10


def recurrence_key(normalized_description: str, amount_cents: int) -> str:
    """Chave da série dentro da conta: sinal + descrição normalizada, ex. `-|netflix.com`."""
    # O sinal separa, por exemplo, um estorno de uma cobrança com a mesma descrição.
    return f"{'+' if amount_cents > 0 else '-'}|{normalized_description}"


def _within_tolerance(amounts: list[int]) -> bool:
    ordered = sorted(amounts)
    middle = len(ordered) // 2
    # Mediana em dobro para quantidade par não exigir divisão: 2·med é a soma dos centrais.
    if len(ordered) % 2:
        twice_median = 2 * ordered[middle]
    else:
        twice_median = ordered[middle - 1] + ordered[middle]
    return all(
        abs(2 * amount - twice_median) * RECURRENCE_TOLERANCE_DIVISOR <= abs(twice_median)
        for amount in amounts
    )


def _is_recurring_series(occurrences: list[tuple[date, UUID, int]]) -> bool:
    months = {(movement_date.year, movement_date.month) for movement_date, _, _ in occurrences}
    if len(months) < RECURRENCE_MIN_OCCURRENCES:
        return False
    dates = [movement_date for movement_date, _, _ in occurrences]
    if not all(
        RECURRENCE_MIN_DAYS <= (later - earlier).days <= RECURRENCE_MAX_DAYS
        for earlier, later in pairwise(dates)
    ):
        return False
    return _within_tolerance([amount for _, _, amount in occurrences])


def detect_recurrences(movements: Iterable[tuple[UUID, date, int, str]]) -> dict[UUID, str]:
    """Ids recorrentes e a chave da série, a partir de (id, data, valor, descrição normalizada).

    Recebe todas as movimentações de uma conta, de qualquer lote: o resultado depende só do
    conjunto, então reimportar as mesmas linhas não muda nada.
    """
    series: dict[str, list[tuple[date, UUID, int]]] = {}
    for movement_id, movement_date, amount, description in movements:
        key = recurrence_key(description, amount)
        series.setdefault(key, []).append((movement_date, movement_id, amount))
    recurring: dict[UUID, str] = {}
    for key, occurrences in series.items():
        # O id desempata o mesmo dia, para o resultado não depender da ordem de leitura.
        occurrences.sort(key=lambda item: (item[0], str(item[1])))
        if _is_recurring_series(occurrences):
            recurring.update((movement_id, key) for _, movement_id, _ in occurrences)
    return recurring


# Gasto atípico (ADR-0010, seção 4). O score é heurístico, não uma probabilidade.
ANOMALY_MIN_EXPENSES = 5
# score >= 0,8 equivale a z >= 3,5, o corte de Iglewicz–Hoaglin (4,375 = 3,5 / 0,8).
ANOMALY_THRESHOLD = Decimal("0.8")
_MAD_SCALE = Decimal("0.6745")
_MEAN_AD_SCALE = Decimal("1.2533")
_SCORE_DIVISOR = Decimal("4.375")
_SCORE_PLACES = Decimal("0.0001")  # NUMERIC(5,4) no banco
_ZERO = Decimal(0)
_ONE = Decimal(1)


def _median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _group_scores(magnitudes: list[Decimal]) -> list[Decimal]:
    median = _median(magnitudes)
    deviations = [abs(x - median) for x in magnitudes]
    mad = _median(deviations)
    mean_ad = sum(deviations, _ZERO) / len(deviations)

    def z(x: Decimal) -> Decimal:
        # Unilateral: só gastar acima da mediana pontua.
        excess = max(_ZERO, x - median)
        if mad > 0:
            return _MAD_SCALE * excess / mad
        # Mais da metade igual à mediana: o desvio absoluto médio (em torno da mediana) ainda
        # enxerga aumentos reais; se também for zero, todos os valores são iguais.
        if mean_ad == 0:
            return _ZERO
        return excess / (_MEAN_AD_SCALE * mean_ad)

    return [
        min(_ONE, z(x) / _SCORE_DIVISOR).quantize(_SCORE_PLACES, rounding=ROUND_HALF_EVEN)
        for x in magnitudes
    ]


def anomaly_scores(movements: Iterable[tuple[UUID, int, UUID]]) -> dict[UUID, Decimal]:
    """Score das saídas por categoria, a partir de (id, valor, categoria) de uma conta.

    Entradas e saídas de categorias com menos de 5 saídas ficam fora: sem score, não zero.
    """
    groups: dict[UUID, list[tuple[UUID, int]]] = {}
    for movement_id, amount, category_id in movements:
        if amount < 0:
            groups.setdefault(category_id, []).append((movement_id, amount))
    scores: dict[UUID, Decimal] = {}
    for expenses in groups.values():
        if len(expenses) < ANOMALY_MIN_EXPENSES:
            continue
        magnitudes = [Decimal(-amount) for _, amount in expenses]
        for (movement_id, _), score in zip(expenses, _group_scores(magnitudes), strict=True):
            scores[movement_id] = score
    return scores


def is_anomaly(score: Decimal | None) -> bool:
    return score is not None and score >= ANOMALY_THRESHOLD
