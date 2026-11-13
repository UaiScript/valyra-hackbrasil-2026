"""Acesso a dados do Finance; não faz commit, quem controla a transação é o service."""

from datetime import date
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from valyra.finance.models import Account, Category, ImportBatch, ImportRejection, Transaction

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
    # created_at e id desempatam transações do mesmo dia, mantendo a paginação estável.
    query = query.order_by(
        Transaction.date.desc(), Transaction.created_at.desc(), Transaction.id.desc()
    )
    rows, total = _page(session, query, limit, offset)
    return [(row[0], row[1]) for row in rows], total
