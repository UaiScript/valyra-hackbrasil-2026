"""Casos de uso do Finance: importação de CSV (#14) e consultas (#15)."""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from valyra.core.errors import AppError
from valyra.finance import repository
from valyra.finance.domain import CsvFormatError, categorize, compute_row_hashes, parse_csv
from valyra.finance.models import Account, Category, ImportBatch, ImportRejection, Transaction

_CSV_ERROR_MESSAGES = {
    "CSV_ENCODING": "O arquivo precisa estar em UTF-8",
    "CSV_MISSING_COLUMNS": "O cabeçalho precisa conter date, description e amount",
    "CSV_TOO_MANY_ROWS": "O arquivo excede o limite de 5000 registros",
}


def get_account_for_user(session: Session, user_id: UUID, account_id: UUID) -> Account:
    account = repository.get_account(session, user_id, account_id)
    if account is None:
        # Conta de outro usuário responde igual a inexistente, sem revelar que ela existe.
        raise AppError("ACCOUNT_NOT_FOUND", "Conta não encontrada", 404)
    return account


def import_csv(
    session: Session, user_id: UUID, account_id: UUID, file_name: str, content: bytes
) -> ImportBatch:
    """Importa em uma única transação: qualquer falha técnica desfaz lote, rejeições e linhas."""
    try:
        account = get_account_for_user(session, user_id, account_id)
        try:
            result = parse_csv(content)
        except CsvFormatError as exc:
            raise AppError(exc.code, _CSV_ERROR_MESSAGES.get(exc.code, str(exc)), 422) from exc

        batch = ImportBatch(
            account_id=account.id, file_name=file_name, status="processing", rows_total=result.total
        )
        session.add(batch)
        session.flush()
        session.add_all(
            ImportRejection(
                import_batch_id=batch.id,
                line_number=rejected.line_number,
                reason=rejected.reason,
                raw_line=rejected.raw_line,
            )
            for rejected in result.rejected
        )

        category_ids = repository.category_ids_by_slug(session)
        hashes = compute_row_hashes(account.id, result.rows)
        values = []
        for row, row_hash in zip(result.rows, hashes, strict=True):
            category_id = category_ids[categorize(row.description, row.amount_cents)]
            values.append(
                {
                    "account_id": account.id,
                    "import_batch_id": batch.id,
                    "date": row.date,
                    "description": row.description,
                    "amount_cents": row.amount_cents,
                    # Na importação a categoria exibida é a prevista; correções mudam só a exibida.
                    "category_id": category_id,
                    "predicted_category_id": category_id,
                    "category_source": "rule",
                    "category_confidence": None,
                    "is_recurring": False,
                    "anomaly_score": None,
                    "row_hash": row_hash,
                }
            )
        inserted = repository.insert_transactions(session, values)

        batch.rows_imported = inserted
        batch.rows_duplicated = len(result.rows) - inserted
        batch.rows_rejected = len(result.rejected)
        batch.status = "completed"
        # clock_timestamp marca o fim real; now() repetiria o início da transação.
        batch.completed_at = func.clock_timestamp()
        session.commit()
        return batch
    except BaseException:
        session.rollback()
        raise


def get_import_batch(
    session: Session, user_id: UUID, batch_id: UUID
) -> tuple[ImportBatch, list[ImportRejection]]:
    batch = repository.get_batch(session, user_id, batch_id)
    if batch is None:
        raise AppError("IMPORT_BATCH_NOT_FOUND", "Lote de importação não encontrado", 404)
    return batch, repository.list_rejections(session, batch.id)


def list_import_batches(
    session: Session, user_id: UUID, limit: int, offset: int
) -> tuple[list[ImportBatch], int]:
    return repository.list_batches(session, user_id, limit, offset)


def list_accounts(
    session: Session, user_id: UUID, limit: int, offset: int
) -> tuple[list[Account], int]:
    return repository.list_accounts(session, user_id, limit, offset)


def update_account(
    session: Session, user_id: UUID, account_id: UUID, changes: dict[str, Any]
) -> Account:
    """Aplica só os campos enviados; o saldo é referência informada, não saldo calculado."""
    try:
        account = get_account_for_user(session, user_id, account_id)
        for field, value in changes.items():
            setattr(account, field, value)
        session.commit()
        return account
    except BaseException:
        session.rollback()
        raise


def list_transactions(
    session: Session,
    user_id: UUID,
    *,
    account_id: UUID | None,
    date_from: date | None,
    date_to: date | None,
    category_id: UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[tuple[Transaction, Category]], int]:
    if account_id is not None:
        # Filtrar por conta alheia responde como conta inexistente, igual às demais rotas.
        get_account_for_user(session, user_id, account_id)
    return repository.list_transactions(
        session,
        user_id,
        account_id=account_id,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        limit=limit,
        offset=offset,
    )


def list_categories(session: Session, limit: int, offset: int) -> tuple[list[Category], int]:
    return repository.list_categories(session, limit, offset)
