"""Schemas HTTP do Finance; expõem só os campos confirmados no contrato (api-design.md)."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
