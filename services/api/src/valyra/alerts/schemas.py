"""Entrada e saída HTTP dos alertas (Issue #47)."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CashPressureEvidenceOut(BaseModel):
    """Snapshot da projeção que gerou o alerta; valores previstos, não realizados."""

    days: int
    today: date
    start_balance_cents: int
    min_balance_cents: int
    min_balance_date: date


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: Literal["cash_pressure"]
    severity: Literal["info", "warning"]
    status: Literal["new", "read"]
    title: str
    message: str
    evidence: CashPressureEvidenceOut
    account_id: UUID
    created_at: datetime
    read_at: datetime | None


class AlertUpdate(BaseModel):
    # Só a leitura é permitida: voltar a "new" não faz parte do contrato da #47.
    model_config = ConfigDict(extra="forbid")

    status: Literal["read"]
