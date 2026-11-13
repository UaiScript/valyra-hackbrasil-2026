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
from valyra.finance.schemas import (
    AccountOut,
    AccountUpdate,
    CategoryOut,
    ImportBatchOut,
    ImportBatchSummaryOut,
    ImportRejectionOut,
    IsoDate,
    TransactionCategoryOut,
    TransactionOut,
)

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


@router.get("/accounts", name="finance_list_accounts", response_model=Page[AccountOut])
def list_accounts(
    page: Annotated[PageParams, Depends()], session: SessionDep, user_id: UserIdDep
) -> Page[AccountOut]:
    items, total = service.list_accounts(session, user_id, page.limit, page.offset)
    return Page[AccountOut](
        items=[AccountOut.model_validate(a) for a in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.patch("/accounts/{id}", name="finance_update_account", response_model=AccountOut)
def update_account(
    id: UUID, body: AccountUpdate, session: SessionDep, user_id: UserIdDep
) -> AccountOut:
    account = service.update_account(session, user_id, id, body.model_dump(exclude_unset=True))
    return AccountOut.model_validate(account)


@router.get("/transactions", name="finance_list_transactions", response_model=Page[TransactionOut])
def list_transactions(
    page: Annotated[PageParams, Depends()],
    session: SessionDep,
    user_id: UserIdDep,
    account_id: UUID | None = None,
    date_from: IsoDate | None = None,
    date_to: IsoDate | None = None,
    category_id: UUID | None = None,
) -> Page[TransactionOut]:
    rows, total = service.list_transactions(
        session,
        user_id,
        account_id=account_id,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        limit=page.limit,
        offset=page.offset,
    )
    items = [
        TransactionOut(
            id=t.id,
            date=t.date,
            description=t.description,
            amount_cents=t.amount_cents,
            category=TransactionCategoryOut.model_validate(category),
            category_source=t.category_source,
            category_confidence=t.category_confidence,
            predicted_category_id=t.predicted_category_id,
        )
        for t, category in rows
    ]
    return Page[TransactionOut](items=items, total=total, limit=page.limit, offset=page.offset)


@router.get("/categories", name="finance_list_categories", response_model=Page[CategoryOut])
def list_categories(
    page: Annotated[PageParams, Depends()], session: SessionDep
) -> Page[CategoryOut]:
    items, total = service.list_categories(session, page.limit, page.offset)
    return Page[CategoryOut](
        items=[CategoryOut.model_validate(c) for c in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )
