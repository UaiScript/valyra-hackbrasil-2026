"""Schemas HTTP do Finance; expõem só os campos confirmados no contrato (api-design.md)."""

import re
from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
)

# Faixa de BIGINT: fora dela o banco recusaria o valor; aqui vira 422 em vez de erro técnico.
BIGINT_MIN = -(2**63)
BIGINT_MAX = 2**63 - 1
_ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


class ImportRejectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    line_number: int
    reason: str
    raw_line: str


class ImportBatchSummaryOut(BaseModel):
    # account_id, file_name e timestamps ficam fora até o contrato completo do lote ser fechado.
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: Literal["processing", "completed", "failed"]
    rows_total: int
    rows_imported: int
    rows_duplicated: int
    rows_rejected: int


class ImportBatchOut(ImportBatchSummaryOut):
    rejections: list[ImportRejectionOut]


class ImportBatchCreatedOut(ImportBatchOut):
    # Só na criação: o GET do lote não sabe quantos alertas aquela importação gerou.
    alerts_created: int


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    balance_cents: int
    balance_as_of: date


def _within_bigint(value: int) -> int:
    # Validador em vez de ge/le: limites de 2**63 virariam float impreciso no OpenAPI.
    if not BIGINT_MIN <= value <= BIGINT_MAX:
        raise ValueError("Valor fora da faixa BIGINT em centavos")
    return value


def _iso_date_text(value: Any) -> Any:
    # Sem isto o modo lax do Pydantic aceitaria timestamps numéricos e datetimes como data.
    if not isinstance(value, str) or not _ISO_DATE.fullmatch(value):
        raise ValueError("Data deve ser texto no formato AAAA-MM-DD")
    return value


def _without_nul(value: str) -> str:
    # O PostgreSQL rejeita NUL em texto; validar aqui devolve 422 em vez de erro 500.
    if "\x00" in value:
        raise ValueError("Nome não pode conter o caractere NUL")
    return value


IsoDate = Annotated[date, BeforeValidator(_iso_date_text)]


class AccountUpdate(BaseModel):
    """Campos omissíveis; null explícito é recusado, pois nenhuma coluna da conta aceita nulo."""

    # Campo desconhecido gera 422, evitando que um erro de digitação passe como sucesso vazio.
    model_config = ConfigDict(extra="forbid")

    # Default não é validado pelo Pydantic: omitir é permitido, enviar null não.
    name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1), AfterValidator(_without_nul)
    ] = Field(default=None)
    balance_cents: Annotated[StrictInt, AfterValidator(_within_bigint)] = Field(default=None)
    balance_as_of: IsoDate = Field(default=None)


class TransactionUpdate(BaseModel):
    """Correção de categoria; category_id é obrigatório e null é recusado."""

    # Campo desconhecido gera 422, como no AccountUpdate.
    model_config = ConfigDict(extra="forbid")

    category_id: UUID


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    kind: Literal["expense", "income"]


class TransactionCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str


class TransactionOut(BaseModel):
    # recurrence_key é detalhe interno da série e não é exposto.
    id: UUID
    date: date
    description: str
    amount_cents: int
    category: TransactionCategoryOut
    category_source: Literal["rule", "model", "user"]
    category_confidence: Decimal | None
    predicted_category_id: UUID
    # Recalculado ao fim de cada importação (ADR-0010, seção 3); recurrence_key não é exposto.
    is_recurring: bool
    # Score heurístico de 0 a 1 (ADR-0010, seção 4), não probabilidade; null sem grupo suficiente.
    anomaly_score: Decimal | None
    # Derivado de anomaly_score >= 0,8, não gravado no banco.
    is_anomaly: bool


class CategoryTotalOut(BaseModel):
    category: CategoryOut
    # Com sinal, como amount_cents: categoria de saída soma valores negativos.
    total_cents: int
    count: int


class SummaryOut(BaseModel):
    """Resumo da Issue #43: saldo realizado de hoje e movimentações realizadas do mês."""

    # null quando o resumo soma todas as contas do usuário.
    account_id: UUID | None
    month: str
    today: date
    # null quando alguma referência de saldo é posterior a hoje (ADR-0010, seção 1).
    realized_balance_cents: int | None
    income_cents: int
    # Soma das saídas, com sinal negativo; net_cents = income_cents + expenses_cents.
    expenses_cents: int
    net_cents: int
    categories: list[CategoryTotalOut]


class ProjectedRecurrenceOut(BaseModel):
    description: str
    # Com sinal; mediana da série recorrente, não um valor realizado.
    amount_cents: int


class ProjectionDayOut(BaseModel):
    date: date
    recurrences: list[ProjectedRecurrenceOut]
    # Soma das recorrências previstas no dia, com sinal.
    recurring_cents: int
    # Média diária de saídas variáveis (<= 0), igual em todos os dias.
    variable_cents: int
    # Saldo previsto ao fim do dia.
    balance_cents: int


class ProjectionOut(BaseModel):
    """Projeção da Issue #46: valores previstos, separados do saldo realizado de partida."""

    account_id: UUID
    today: date
    # Saldo realizado ao fim de hoje (ADR-0010, seção 1).
    start_balance_cents: int
    variable_daily_cents: int
    days: int
    items: list[ProjectionDayOut]
    min_balance_cents: int
    # Primeiro dia em que o mínimo ocorre.
    min_balance_date: date
