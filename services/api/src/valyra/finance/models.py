"""Seis tabelas iniciais: User fica em core.db; as outras cinco ficam aqui."""

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from valyra.core.db import Base


class MoneyCents(TypeDecorator[int]):
    """BIGINT com bind estrito, inclusive em inserts em lote que não usam validadores ORM."""

    impl = BigInteger
    cache_ok = True

    def process_bind_param(self, value: int | None, dialect: Dialect) -> int | None:
        if value is not None and type(value) is not int:
            raise ValueError("Dinheiro exige inteiro em centavos, sem conversão de precisão")
        return value


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("updated_at >= created_at", name="timestamps_order"),
        Index("ix_accounts_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String)
    # Dinheiro é inteiro em centavos; não há conversão de reais nesta camada.
    balance_cents: Mapped[int] = mapped_column(MoneyCents)
    balance_as_of: Mapped[date_type] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )


class ImportBatch(Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        UniqueConstraint("id", "account_id"),
        CheckConstraint("status IN ('processing', 'completed', 'failed')", name="status_values"),
        CheckConstraint(
            "rows_total >= 0 AND rows_imported >= 0 "
            "AND rows_duplicated >= 0 AND rows_rejected >= 0",
            name="nonnegative_counts",
        ),
        # O cast antes da soma impede overflow intermediário de INTEGER.
        CheckConstraint(
            "CAST(rows_imported AS BIGINT) + rows_duplicated + rows_rejected <= rows_total",
            name="counts_within_total",
        ),
        CheckConstraint(
            "status <> 'completed' OR "
            "CAST(rows_imported AS BIGINT) + rows_duplicated + rows_rejected = rows_total",
            name="completed_counts",
        ),
        CheckConstraint(
            "(status = 'processing' AND completed_at IS NULL) OR "
            "(status IN ('completed', 'failed') AND completed_at IS NOT NULL)",
            name="status_completion",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= created_at", name="completion_order"
        ),
        Index("ix_import_batches_account_id", "account_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"))
    file_name: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, server_default=text("'processing'"))
    rows_total: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    rows_imported: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    rows_duplicated: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    rows_rejected: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ImportRejection(Base):
    __tablename__ = "import_rejections"
    __table_args__ = (
        UniqueConstraint("import_batch_id", "line_number"),
        CheckConstraint("line_number > 0", name="positive_line_number"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    import_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE")
    )
    line_number: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String)
    raw_line: Mapped[str] = mapped_column(Text)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("slug"),
        CheckConstraint("kind IN ('expense', 'income')", name="kind_values"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    slug: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        # Uma FK simples de lote não impediria usar lote de outra conta.
        ForeignKeyConstraint(
            ["import_batch_id", "account_id"],
            ["import_batches.id", "import_batches.account_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("account_id", "row_hash"),
        CheckConstraint("amount_cents <> 0", name="nonzero_amount"),
        CheckConstraint(
            "category_source IN ('rule', 'model', 'user')", name="category_source_values"
        ),
        CheckConstraint(
            "category_confidence IS NULL OR category_confidence BETWEEN 0 AND 1",
            name="category_confidence_range",
        ),
        CheckConstraint(
            "anomaly_score IS NULL OR anomaly_score BETWEEN 0 AND 1", name="anomaly_score_range"
        ),
        CheckConstraint("updated_at >= created_at", name="timestamps_order"),
        Index("ix_transactions_account_id_date", "account_id", "date"),
        Index("ix_transactions_category_id", "category_id"),
        Index("ix_transactions_import_batch_id_account_id", "import_batch_id", "account_id"),
        Index("ix_transactions_predicted_category_id", "predicted_category_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"))
    import_batch_id: Mapped[UUID] = mapped_column()
    date: Mapped[date_type] = mapped_column(Date)
    description: Mapped[str] = mapped_column(Text)
    amount_cents: Mapped[int] = mapped_column(MoneyCents)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    # Sugestão original: correções futuras alteram só category_id e category_source.
    predicted_category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT")
    )
    category_source: Mapped[str] = mapped_column(String)
    category_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    is_recurring: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    recurrence_key: Mapped[str | None] = mapped_column(String)
    anomaly_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    row_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )
