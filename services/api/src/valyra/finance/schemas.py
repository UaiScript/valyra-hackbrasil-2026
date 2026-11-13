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
    # alerts_created entra com o módulo de alertas; expor 0 agora afirmaria algo não verificado.
    rejections: list[ImportRejectionOut]


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
    # is_recurring e anomalia ficam fora até existirem os cálculos que os preenchem.
    id: UUID
    date: date
    description: str
    amount_cents: int
    category: TransactionCategoryOut
    category_source: Literal["rule", "model", "user"]
    category_confidence: Decimal | None
    predicted_category_id: UUID
