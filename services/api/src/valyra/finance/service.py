"""Casos de uso do Finance: importação (#14), consultas (#15), correção (#42), resumo (#43),
recorrência (#44), gastos atípicos (#45) e projeção de caixa (#46)."""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from valyra.core import clock
from valyra.core.errors import AppError
from valyra.finance import repository
from valyra.finance.analytics import (
    ANOMALY_THRESHOLD,
    MonthSummary,
    Projection,
    anomaly_scores,
    detect_recurrences,
    month_bounds,
    project_cash,
    realized_balance_cents,
    recurring_series,
    summarize_month,
    variable_daily_cents,
)
from valyra.finance.domain import (
    CsvFormatError,
    categorize,
    category_kind_matches,
    compute_row_hashes,
    normalize_description,
    parse_csv,
)
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
        # Na mesma transação da importação: falha no recálculo desfaz também as linhas novas.
        _refresh_signals(session, account.id)

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


def _refresh_signals(session: Session, account_id: UUID) -> None:
    """Recalcula recorrência e gasto atípico da conta inteira e grava só o que mudou."""
    rows = repository.list_signal_inputs(session, account_id)
    recurring = detect_recurrences(
        (row.id, row.date, row.amount_cents, normalize_description(row.description)) for row in rows
    )
    scores = anomaly_scores((row.id, row.amount_cents, row.category_id) for row in rows)
    # Gravar só a diferença mantém updated_at intacto quando reimportar não muda nada; uma
    # ocorrência nova também pode desmarcar uma série ou mudar o score do grupo inteiro.
    changes = []
    for row in rows:
        new = {
            "is_recurring": row.id in recurring,
            "recurrence_key": recurring.get(row.id),
            "anomaly_score": scores.get(row.id),
        }
        if (row.is_recurring, row.recurrence_key, row.anomaly_score) != tuple(new.values()):
            changes.append({"id": row.id, **new})
    repository.update_signals(session, changes)


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


def update_transaction_category(
    session: Session, user_id: UUID, transaction_id: UUID, category_id: UUID
) -> tuple[Transaction, Category]:
    """Correção pelo usuário: muda a categoria exibida e mantém a sugestão original."""
    try:
        transaction = repository.get_transaction(session, user_id, transaction_id)
        if transaction is None:
            # Transação de outro usuário responde igual a inexistente, sem revelar que existe.
            raise AppError("TRANSACTION_NOT_FOUND", "Transação não encontrada", 404)
        category = repository.get_category(session, category_id)
        if category is None:
            raise AppError("CATEGORY_NOT_FOUND", "Categoria não encontrada", 404)
        if not category_kind_matches(category.kind, transaction.amount_cents):
            raise AppError(
                "CATEGORY_KIND_MISMATCH",
                "O tipo da categoria não corresponde ao sinal da transação",
                422,
            )
        # predicted_category_id e category_confidence registram a sugestão original e
        # não mudam: comparar sugestão e correção é o que permite avaliar a categorização.
        transaction.category_id = category.id
        transaction.category_source = "user"
        # O score depende da categoria: a origem perde e o destino ganha uma saída. Recalcular a
        # conta inteira equivale a recalcular os dois grupos, pois os demais não mudam.
        session.flush()
        _refresh_signals(session, transaction.account_id)
        session.commit()
        return transaction, category
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
    is_recurring: bool | None,
    is_anomaly: bool | None,
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
        is_recurring=is_recurring,
        is_anomaly=is_anomaly,
        # O limiar é regra do analytics; o repository só o aplica na consulta.
        anomaly_threshold=ANOMALY_THRESHOLD,
        limit=limit,
        offset=offset,
    )


def list_categories(session: Session, limit: int, offset: int) -> tuple[list[Category], int]:
    return repository.list_categories(session, limit, offset)


@dataclass(frozen=True)
class Summary:
    account_id: UUID | None
    month: str
    today: date
    realized_balance_cents: int | None
    month_summary: MonthSummary
    categories: dict[UUID, Category]


def get_summary(
    session: Session, user_id: UUID, account_id: UUID | None, month: str | None
) -> Summary:
    """Saldo realizado de hoje e totais do mês; sem conta, considera todas as do usuário."""
    if account_id is not None:
        accounts = [get_account_for_user(session, user_id, account_id)]
    else:
        accounts = repository.list_user_accounts(session, user_id)
    today = clock.get_today()
    first, last = month_bounds(month, today)

    # Uma leitura cobre as duas janelas: (referência, hoje] do realizado e o mês até hoje.
    after = min([first - timedelta(days=1), *(a.balance_as_of for a in accounts)])
    movements = repository.list_movements(session, [a.id for a in accounts], after, today)

    balances = [
        realized_balance_cents(
            account.balance_cents,
            account.balance_as_of,
            ((d, amount) for acc_id, d, amount, _ in movements if acc_id == account.id),
            today,
        )
        for account in accounts
    ]
    # Uma conta com referência futura torna a soma desconhecida, não menor.
    realized = None if None in balances else sum(balances)

    month_summary = summarize_month(
        ((d, amount, category_id) for _, d, amount, category_id in movements), first, last, today
    )
    categories = repository.get_categories(
        session, [total.category_id for total in month_summary.categories]
    )
    return Summary(
        account_id=account_id,
        month=f"{first.year:04d}-{first.month:02d}",
        today=today,
        realized_balance_cents=realized,
        month_summary=month_summary,
        categories=categories,
    )


@dataclass(frozen=True)
class AccountProjection:
    account_id: UUID
    today: date
    projection: Projection


def get_projection(
    session: Session, user_id: UUID, account_id: UUID, days: int
) -> AccountProjection:
    """Projeção diária de caixa da conta; só leitura, nada é gravado (ADR-0010, seção 5)."""
    account = get_account_for_user(session, user_id, account_id)
    today = clock.get_today()
    rows = repository.list_signal_inputs(session, account.id)
    start = realized_balance_cents(
        account.balance_cents,
        account.balance_as_of,
        ((row.date, row.amount_cents) for row in rows),
        today,
    )
    if start is None:
        # Referência posterior a hoje: o fechamento não permite reconstruir o saldo atual.
        raise AppError(
            "BALANCE_UNAVAILABLE",
            "Saldo de referência posterior a hoje; não é possível projetar",
            422,
        )
    series = recurring_series(
        (row.date, row.amount_cents, row.description, row.recurrence_key)
        for row in rows
        if row.is_recurring
    )
    variable = variable_daily_cents(
        ((row.date, row.amount_cents, row.is_recurring) for row in rows), today
    )
    return AccountProjection(
        account_id=account.id,
        today=today,
        projection=project_cash(start, today, days, series, variable),
    )
