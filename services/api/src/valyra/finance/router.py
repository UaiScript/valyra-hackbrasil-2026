"""Rotas HTTP do Finance; o nome de cada rota é o operationId do contrato."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from valyra.core.db import get_session
from valyra.core.deps import get_current_user_id
from valyra.core.errors import AppError, error_responses
from valyra.core.pagination import Page, PageParams
from valyra.finance import service
from valyra.finance.analytics import MONTH_PATTERN, PROJECTION_DEFAULT_DAYS, PROJECTION_MAX_DAYS

# Alias: o filtro da rota também se chama is_anomaly.
from valyra.finance.analytics import is_anomaly as anomaly_flag
from valyra.finance.domain import MAX_FILE_BYTES
from valyra.finance.models import Category, Transaction
from valyra.finance.schemas import (
    AccountOut,
    AccountUpdate,
    CategoryOut,
    CategoryTotalOut,
    ImportBatchCreatedOut,
    ImportBatchOut,
    ImportBatchSummaryOut,
    ImportRejectionOut,
    IsoDate,
    ProjectedRecurrenceOut,
    ProjectionDayOut,
    ProjectionOut,
    SummaryOut,
    TransactionCategoryOut,
    TransactionOut,
    TransactionUpdate,
)

# Toda rota Finance recebe parâmetros validados; o 422 no envelope vale para todas.
router = APIRouter(prefix="/api/v1/finance", tags=["finance"], responses=error_responses(422))

SessionDep = Annotated[Session, Depends(get_session)]
UserIdDep = Annotated[UUID, Depends(get_current_user_id)]


def _batch_out(session: Session, user_id: UUID, batch_id: UUID) -> ImportBatchOut:
    batch, rejections = service.get_import_batch(session, user_id, batch_id)
    return ImportBatchOut(
        **ImportBatchSummaryOut.model_validate(batch).model_dump(),
        rejections=[ImportRejectionOut.model_validate(r) for r in rejections],
    )


def _transaction_out(t: Transaction, category: Category) -> TransactionOut:
    return TransactionOut(
        id=t.id,
        date=t.date,
        description=t.description,
        amount_cents=t.amount_cents,
        category=TransactionCategoryOut.model_validate(category),
        category_source=t.category_source,
        category_confidence=t.category_confidence,
        predicted_category_id=t.predicted_category_id,
        is_recurring=t.is_recurring,
        anomaly_score=t.anomaly_score,
        is_anomaly=anomaly_flag(t.anomaly_score),
    )


# Rotas síncronas: o service usa sessão SQLAlchemy bloqueante e roda no threadpool.
@router.post(
    "/accounts/{account_id}/import-batches",
    name="finance_create_import_batch",
    status_code=201,
    response_model=ImportBatchCreatedOut,
    responses=error_responses(404, 413),
)
def create_import_batch(
    account_id: UUID, file: Annotated[UploadFile, File()], session: SessionDep, user_id: UserIdDep
) -> ImportBatchCreatedOut:
    # Lê no máximo um byte além do limite: basta para saber que excedeu sem carregar o resto.
    content = file.file.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise AppError("FILE_TOO_LARGE", "O arquivo excede o limite de 1 MiB", 413)
    result = service.import_csv(session, user_id, account_id, file.filename or "", content)
    batch = _batch_out(session, user_id, result.batch.id)
    return ImportBatchCreatedOut(**batch.model_dump(), alerts_created=result.alerts_created)


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


@router.get(
    "/import-batches/{id}",
    name="finance_get_import_batch",
    response_model=ImportBatchOut,
    responses=error_responses(404),
)
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


@router.patch(
    "/accounts/{id}",
    name="finance_update_account",
    response_model=AccountOut,
    responses=error_responses(404),
)
def update_account(
    id: UUID, body: AccountUpdate, session: SessionDep, user_id: UserIdDep
) -> AccountOut:
    account = service.update_account(session, user_id, id, body.model_dump(exclude_unset=True))
    return AccountOut.model_validate(account)


# 404 quando o filtro account_id aponta conta inexistente ou de outro usuário.
@router.get(
    "/transactions",
    name="finance_list_transactions",
    response_model=Page[TransactionOut],
    responses=error_responses(404),
)
def list_transactions(
    page: Annotated[PageParams, Depends()],
    session: SessionDep,
    user_id: UserIdDep,
    account_id: UUID | None = None,
    date_from: IsoDate | None = None,
    date_to: IsoDate | None = None,
    category_id: UUID | None = None,
    is_recurring: bool | None = None,
    is_anomaly: bool | None = None,
) -> Page[TransactionOut]:
    rows, total = service.list_transactions(
        session,
        user_id,
        account_id=account_id,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        is_recurring=is_recurring,
        is_anomaly=is_anomaly,
        limit=page.limit,
        offset=page.offset,
    )
    items = [_transaction_out(t, category) for t, category in rows]
    return Page[TransactionOut](items=items, total=total, limit=page.limit, offset=page.offset)


@router.patch(
    "/transactions/{id}",
    name="finance_update_transaction",
    response_model=TransactionOut,
    responses=error_responses(404),
)
def update_transaction(
    id: UUID, body: TransactionUpdate, session: SessionDep, user_id: UserIdDep
) -> TransactionOut:
    transaction, category = service.update_transaction_category(
        session, user_id, id, body.category_id
    )
    return _transaction_out(transaction, category)


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


# 404 quando account_id aponta conta inexistente ou de outro usuário.
@router.get(
    "/summary",
    name="finance_get_summary",
    response_model=SummaryOut,
    responses=error_responses(404),
)
def get_summary(
    session: SessionDep,
    user_id: UserIdDep,
    account_id: UUID | None = None,
    month: Annotated[
        str | None, Query(pattern=f"^{MONTH_PATTERN}$", description="AAAA-MM; padrão: mês de hoje")
    ] = None,
) -> SummaryOut:
    summary = service.get_summary(session, user_id, account_id, month)
    totals = summary.month_summary
    return SummaryOut(
        account_id=summary.account_id,
        month=summary.month,
        today=summary.today,
        realized_balance_cents=summary.realized_balance_cents,
        income_cents=totals.income_cents,
        expenses_cents=totals.expenses_cents,
        net_cents=totals.net_cents,
        categories=[
            CategoryTotalOut(
                category=CategoryOut.model_validate(summary.categories[total.category_id]),
                total_cents=total.total_cents,
                count=total.count,
            )
            for total in totals.categories
        ],
    )


# 404 para conta alheia ou inexistente; 422 BALANCE_UNAVAILABLE com referência futura.
@router.get(
    "/accounts/{id}/projection",
    name="finance_get_projection",
    response_model=ProjectionOut,
    responses=error_responses(404),
)
def get_projection(
    id: UUID,
    session: SessionDep,
    user_id: UserIdDep,
    days: Annotated[
        int,
        Query(ge=1, le=PROJECTION_MAX_DAYS, description="Horizonte em dias, a partir de amanhã"),
    ] = PROJECTION_DEFAULT_DAYS,
) -> ProjectionOut:
    result = service.get_projection(session, user_id, id, days)
    projection = result.projection
    return ProjectionOut(
        account_id=result.account_id,
        today=result.today,
        start_balance_cents=projection.start_balance_cents,
        variable_daily_cents=projection.variable_daily_cents,
        days=projection.days,
        items=[
            ProjectionDayOut(
                date=day.date,
                recurrences=[
                    ProjectedRecurrenceOut(description=r.description, amount_cents=r.amount_cents)
                    for r in day.recurrences
                ],
                recurring_cents=day.recurring_cents,
                variable_cents=day.variable_cents,
                balance_cents=day.balance_cents,
            )
            for day in projection.items
        ],
        min_balance_cents=projection.min_balance_cents,
        min_balance_date=projection.min_balance_date,
    )
