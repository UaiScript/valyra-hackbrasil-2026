"""Acesso a dados do Finance; não faz commit, quem controla a transação é o service."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from valyra.finance.models import (
    Account,
    Budget,
    Category,
    ImportBatch,
    ImportRejection,
    Transaction,
)

# 5000 linhas × 12 colunas = 60000 parâmetros, perto do teto de 65535 por comando do PostgreSQL;
# blocos mantêm folga quando novas colunas forem gravadas na importação.
_INSERT_CHUNK = 1000


def get_account(session: Session, user_id: UUID, account_id: UUID) -> Account | None:
    return session.scalar(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    )


def category_ids_by_slug(session: Session) -> dict[str, UUID]:
    return {
        slug: category_id
        for slug, category_id in session.execute(select(Category.slug, Category.id))
    }


def insert_transactions(session: Session, values: list[dict]) -> int:
    """Insere ignorando hashes já existentes na conta; devolve quantas linhas entraram."""
    inserted = 0
    for start in range(0, len(values), _INSERT_CHUNK):
        statement = (
            insert(Transaction)
            .values(values[start : start + _INSERT_CHUNK])
            .on_conflict_do_nothing(index_elements=[Transaction.account_id, Transaction.row_hash])
            .returning(Transaction.id)
        )
        inserted += len(session.execute(statement).all())
    return inserted


def _batches_of_user(user_id: UUID):
    return (
        select(ImportBatch)
        .join(Account, Account.id == ImportBatch.account_id)
        .where(Account.user_id == user_id)
    )


def get_batch(session: Session, user_id: UUID, batch_id: UUID) -> ImportBatch | None:
    return session.scalar(_batches_of_user(user_id).where(ImportBatch.id == batch_id))


def list_rejections(session: Session, batch_id: UUID) -> list[ImportRejection]:
    return list(
        session.scalars(
            select(ImportRejection)
            .where(ImportRejection.import_batch_id == batch_id)
            .order_by(ImportRejection.line_number)
        )
    )


def list_batches(
    session: Session, user_id: UUID, limit: int, offset: int
) -> tuple[list[ImportBatch], int]:
    query = _batches_of_user(user_id)
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    # id desempata lotes criados na mesma transação, mantendo a paginação estável.
    items = session.scalars(
        query.order_by(ImportBatch.created_at.desc(), ImportBatch.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(items), total or 0


def _page(session: Session, query: Select, limit: int, offset: int) -> tuple[list, int]:
    total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    return list(session.execute(query.limit(limit).offset(offset)).all()), total or 0


def list_accounts(
    session: Session, user_id: UUID, limit: int, offset: int
) -> tuple[list[Account], int]:
    query = select(Account).where(Account.user_id == user_id).order_by(Account.name, Account.id)
    rows, total = _page(session, query, limit, offset)
    return [row[0] for row in rows], total


def list_categories(session: Session, limit: int, offset: int) -> tuple[list[Category], int]:
    query = select(Category).order_by(Category.kind, Category.name, Category.id)
    rows, total = _page(session, query, limit, offset)
    return [row[0] for row in rows], total


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
    anomaly_threshold: Decimal,
    limit: int,
    offset: int,
) -> tuple[list[tuple[Transaction, Category]], int]:
    query = (
        select(Transaction, Category)
        .join(Account, Account.id == Transaction.account_id)
        .join(Category, Category.id == Transaction.category_id)
        .where(Account.user_id == user_id)
    )
    if account_id is not None:
        query = query.where(Transaction.account_id == account_id)
    # Limites inclusivos; intervalo invertido simplesmente não encontra linhas.
    if date_from is not None:
        query = query.where(Transaction.date >= date_from)
    if date_to is not None:
        query = query.where(Transaction.date <= date_to)
    if category_id is not None:
        query = query.where(Transaction.category_id == category_id)
    if is_recurring is not None:
        query = query.where(Transaction.is_recurring.is_(is_recurring))
    if is_anomaly is True:
        query = query.where(Transaction.anomaly_score >= anomaly_threshold)
    elif is_anomaly is False:
        # Sem score não há anomalia: NULL entra no grupo "não atípico".
        query = query.where(
            or_(Transaction.anomaly_score.is_(None), Transaction.anomaly_score < anomaly_threshold)
        )
    # created_at e id desempatam transações do mesmo dia, mantendo a paginação estável.
    query = query.order_by(
        Transaction.date.desc(), Transaction.created_at.desc(), Transaction.id.desc()
    )
    rows, total = _page(session, query, limit, offset)
    return [(row[0], row[1]) for row in rows], total


def get_transaction(session: Session, user_id: UUID, transaction_id: UUID) -> Transaction | None:
    # Propriedade vem da conta; a trava evita duas correções concorrentes sobrescreverem às cegas.
    return session.scalar(
        select(Transaction)
        .join(Account, Account.id == Transaction.account_id)
        .where(Transaction.id == transaction_id, Account.user_id == user_id)
        .with_for_update(of=Transaction)
    )


def get_category(session: Session, category_id: UUID) -> Category | None:
    return session.get(Category, category_id)


def list_user_accounts(session: Session, user_id: UUID) -> list[Account]:
    return list(
        session.scalars(select(Account).where(Account.user_id == user_id).order_by(Account.id))
    )


def list_movements(
    session: Session, account_ids: list[UUID], after: date, until: date
) -> list[tuple[UUID, date, int, UUID]]:
    """Movimentações com `after < date <= until`: só as colunas usadas pelos cálculos."""
    if not account_ids:
        return []
    rows = session.execute(
        select(
            Transaction.account_id,
            Transaction.date,
            Transaction.amount_cents,
            Transaction.category_id,
        ).where(
            Transaction.account_id.in_(account_ids),
            Transaction.date > after,
            Transaction.date <= until,
        )
    )
    return [(row[0], row[1], row[2], row[3]) for row in rows]


def get_categories(session: Session, category_ids: list[UUID]) -> dict[UUID, Category]:
    if not category_ids:
        return {}
    categories = session.scalars(select(Category).where(Category.id.in_(category_ids)))
    return {category.id: category for category in categories}


@dataclass(frozen=True)
class SignalInput:
    id: UUID
    date: date
    amount_cents: int
    description: str
    category_id: UUID
    is_recurring: bool
    recurrence_key: str | None
    anomaly_score: Decimal | None


def list_signal_inputs(session: Session, account_id: UUID) -> list[SignalInput]:
    """Todas as transações da conta, de qualquer lote, com os sinais gravados hoje."""
    rows = session.execute(
        select(
            Transaction.id,
            Transaction.date,
            Transaction.amount_cents,
            Transaction.description,
            Transaction.category_id,
            Transaction.is_recurring,
            Transaction.recurrence_key,
            Transaction.anomaly_score,
        ).where(Transaction.account_id == account_id)
    )
    return [SignalInput(*row) for row in rows]


def update_signals(session: Session, changes: list[dict]) -> None:
    """UPDATE em lote por chave primária: id, is_recurring, recurrence_key e anomaly_score."""
    if changes:
        session.execute(update(Transaction), changes)


def list_budgets(session: Session, user_id: UUID) -> list[tuple[Budget, Category]]:
    rows = session.execute(
        select(Budget, Category)
        .join(Category, Category.id == Budget.category_id)
        .where(Budget.user_id == user_id)
        .order_by(Category.name, Category.id)
    )
    return [(row[0], row[1]) for row in rows]


def upsert_budget(session: Session, user_id: UUID, category_id: UUID, limit_cents: int) -> None:
    # ON CONFLICT evita corrida entre dois PUT simultâneos para a mesma categoria.
    statement = insert(Budget).values(
        user_id=user_id, category_id=category_id, limit_cents=limit_cents
    )
    session.execute(
        statement.on_conflict_do_update(
            index_elements=[Budget.user_id, Budget.category_id],
            set_={"limit_cents": limit_cents, "updated_at": func.now()},
        )
    )


def delete_budget(session: Session, user_id: UUID, category_id: UUID) -> bool:
    budget = session.scalar(
        select(Budget).where(Budget.user_id == user_id, Budget.category_id == category_id)
    )
    if budget is None:
        return False
    session.delete(budget)
    return True


def list_completed_batches(session: Session, account_id: UUID) -> list[tuple[UUID, datetime]]:
    rows = session.execute(
        select(ImportBatch.id, ImportBatch.completed_at)
        .where(ImportBatch.account_id == account_id, ImportBatch.status == "completed")
        .order_by(ImportBatch.created_at, ImportBatch.id)
    )
    return [(row[0], row[1]) for row in rows]
