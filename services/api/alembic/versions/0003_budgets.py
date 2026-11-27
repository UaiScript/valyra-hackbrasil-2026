"""Orçamento mensal por categoria de saída.

Um limite por usuário e categoria, em centavos positivos; o consumo do mês é calculado na
leitura a partir das transações realizadas, sem coluna derivada para manter em sincronia.

Revision ID: 0003_budgets
Revises: 0002_alerts
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_budgets"
down_revision = "0002_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "budgets",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("limit_cents", sa.BigInteger(), nullable=False),
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
        sa.CheckConstraint("limit_cents > 0", name=op.f("ck_budgets_positive_limit")),
        sa.CheckConstraint("updated_at >= created_at", name=op.f("ck_budgets_timestamps_order")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="RESTRICT", name=op.f("fk_budgets_user_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            ondelete="RESTRICT",
            name=op.f("fk_budgets_category_id_categories"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_budgets")),
        sa.UniqueConstraint("user_id", "category_id", name=op.f("uq_budgets_user_id_category_id")),
    )
    op.create_index(op.f("ix_budgets_category_id"), "budgets", ["category_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_budgets_category_id"), table_name="budgets")
    op.drop_table("budgets")
