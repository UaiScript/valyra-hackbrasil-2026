"""Schema inicial aprovado do Finance, sem dependência dos modelos atuais.

Revision ID: 0001_finance_inicial
Revises: None
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_finance_inicial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("balance_cents", sa.BigInteger(), nullable=False),
        sa.Column("balance_as_of", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("updated_at >= created_at", name=op.f("ck_accounts_timestamps_order")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="RESTRICT", name=op.f("fk_accounts_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_accounts")),
    )
    op.create_index(op.f("ix_accounts_user_id"), "accounts", ["user_id"])
    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("kind IN ('expense', 'income')", name=op.f("ck_categories_kind_values")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
        sa.UniqueConstraint("slug", name=op.f("uq_categories_slug")),
    )
    op.create_table(
        "import_batches",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default=sa.text("'processing'"), nullable=False),
        sa.Column("rows_total", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("rows_imported", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("rows_duplicated", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("rows_rejected", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('processing', 'completed', 'failed')",
            name=op.f("ck_import_batches_status_values"),
        ),
        sa.CheckConstraint(
            "rows_total >= 0 AND rows_imported >= 0 "
            "AND rows_duplicated >= 0 AND rows_rejected >= 0",
            name=op.f("ck_import_batches_nonnegative_counts"),
        ),
        sa.CheckConstraint(
            "CAST(rows_imported AS BIGINT) + rows_duplicated + rows_rejected <= rows_total",
            name=op.f("ck_import_batches_counts_within_total"),
        ),
        sa.CheckConstraint(
            "status <> 'completed' OR "
            "CAST(rows_imported AS BIGINT) + rows_duplicated + rows_rejected = rows_total",
            name=op.f("ck_import_batches_completed_counts"),
        ),
        sa.CheckConstraint(
            "(status = 'processing' AND completed_at IS NULL) OR "
            "(status IN ('completed', 'failed') AND completed_at IS NOT NULL)",
            name=op.f("ck_import_batches_status_completion"),
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= created_at",
            name=op.f("ck_import_batches_completion_order"),
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            ondelete="RESTRICT",
            name=op.f("fk_import_batches_account_id_accounts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_batches")),
        sa.UniqueConstraint("id", "account_id", name=op.f("uq_import_batches_id_account_id")),
    )
    op.create_index(op.f("ix_import_batches_account_id"), "import_batches", ["account_id"])
    op.create_table(
        "import_rejections",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("import_batch_id", sa.Uuid(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("raw_line", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "line_number > 0", name=op.f("ck_import_rejections_positive_line_number")
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            ondelete="CASCADE",
            name=op.f("fk_import_rejections_import_batch_id_import_batches"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_rejections")),
        sa.UniqueConstraint(
            "import_batch_id",
            "line_number",
            name=op.f("uq_import_rejections_import_batch_id_line_number"),
        ),
    )
    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("import_batch_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("predicted_category_id", sa.Uuid(), nullable=False),
        sa.Column("category_source", sa.String(), nullable=False),
        sa.Column("category_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("is_recurring", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("recurrence_key", sa.String(), nullable=True),
        sa.Column("anomaly_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("row_hash", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("amount_cents <> 0", name=op.f("ck_transactions_nonzero_amount")),
        sa.CheckConstraint(
            "category_source IN ('rule', 'model', 'user')",
            name=op.f("ck_transactions_category_source_values"),
        ),
        sa.CheckConstraint(
            "category_confidence IS NULL OR category_confidence BETWEEN 0 AND 1",
            name=op.f("ck_transactions_category_confidence_range"),
        ),
        sa.CheckConstraint(
            "anomaly_score IS NULL OR anomaly_score BETWEEN 0 AND 1",
            name=op.f("ck_transactions_anomaly_score_range"),
        ),
        sa.CheckConstraint(
            "updated_at >= created_at", name=op.f("ck_transactions_timestamps_order")
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            ondelete="RESTRICT",
            name=op.f("fk_transactions_account_id_accounts"),
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id", "account_id"],
            ["import_batches.id", "import_batches.account_id"],
            ondelete="RESTRICT",
            name=op.f("fk_transactions_import_batch_id_import_batches"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            ondelete="RESTRICT",
            name=op.f("fk_transactions_category_id_categories"),
        ),
        sa.ForeignKeyConstraint(
            ["predicted_category_id"],
            ["categories.id"],
            ondelete="RESTRICT",
            name=op.f("fk_transactions_predicted_category_id_categories"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transactions")),
        sa.UniqueConstraint(
            "account_id", "row_hash", name=op.f("uq_transactions_account_id_row_hash")
        ),
    )
    op.create_index(op.f("ix_transactions_account_id_date"), "transactions", ["account_id", "date"])
    op.create_index(op.f("ix_transactions_category_id"), "transactions", ["category_id"])
    op.create_index(
        op.f("ix_transactions_import_batch_id_account_id"),
        "transactions",
        ["import_batch_id", "account_id"],
    )
    op.create_index(
        op.f("ix_transactions_predicted_category_id"), "transactions", ["predicted_category_id"]
    )


def downgrade() -> None:
    # Só para banco descartável: respeita a ordem inversa das dependências.
    for table in (
        "transactions",
        "import_rejections",
        "import_batches",
        "categories",
        "accounts",
        "users",
    ):
        op.drop_table(table)
