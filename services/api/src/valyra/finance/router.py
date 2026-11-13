"""Rotas HTTP do Finance; o nome de cada rota é o operationId do contrato."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from valyra.core.db import get_session
from valyra.core.deps import get_current_user_id
from valyra.core.errors import AppError
from valyra.core.pagination import Page, PageParams
from valyra.finance import service
from valyra.finance.domain import MAX_FILE_BYTES
from valyra.finance.schemas import ImportBatchOut, ImportBatchSummaryOut, ImportRejectionOut

router = APIRouter(prefix="/api/v1/finance", tags=["finance"])

SessionDep = Annotated[Session, Depends(get_session)]
UserIdDep = Annotated[UUID, Depends(get_current_user_id)]


def _batch_out(session: Session, user_id: UUID, batch_id: UUID) -> ImportBatchOut:
    batch, rejections = service.get_import_batch(session, user_id, batch_id)
    return ImportBatchOut(
        **ImportBatchSummaryOut.model_validate(batch).model_dump(),
        rejections=[ImportRejectionOut.model_validate(r) for r in rejections],
    )


# Rotas síncronas: o service usa sessão SQLAlchemy bloqueante e roda no threadpool.
@router.post(
    "/accounts/{account_id}/import-batches",
    name="finance_create_import_batch",
    status_code=201,
    response_model=ImportBatchOut,
)
def create_import_batch(
    account_id: UUID, file: Annotated[UploadFile, File()], session: SessionDep, user_id: UserIdDep
) -> ImportBatchOut:
    # Lê no máximo um byte além do limite: basta para saber que excedeu sem carregar o resto.
    content = file.file.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise AppError("FILE_TOO_LARGE", "O arquivo excede o limite de 1 MiB", 413)
    batch = service.import_csv(session, user_id, account_id, file.filename or "", content)
    return _batch_out(session, user_id, batch.id)


@router.get(
    "/import-batches",
    name="finance_list_import_batches",
    response_model=Page[ImportBatchSummaryOut],
)
def list_import_batches(
    page: Annotated[PageParams, Depends()], session: SessionDep, user_id: UserIdDep
) -> Page[ImportBatchSummaryOut]:
    items, total = service.list_import_batches(session, user_id, page.limit, page.offset)
    return Page[ImportBatchSummaryOut](
        items=[ImportBatchSummaryOut.model_validate(b) for b in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/import-batches/{id}", name="finance_get_import_batch", response_model=ImportBatchOut)
def get_import_batch(id: UUID, session: SessionDep, user_id: UserIdDep) -> ImportBatchOut:
    return _batch_out(session, user_id, id)
