"""Alertas persistidos, por enquanto só de pressão de caixa (Issue #47).

market_signal, signal_id e asset_id entram com o Alpha, quando signals/assets existirem: a
migração do Alpha acrescenta as colunas, as FKs e amplia o CHECK de kind.

Revision ID: 0002_alerts
Revises: 0001_finance_inicial
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_alerts"
down_revision = "0001_finance_inicial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default=sa.text("'new'"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column("dedup_key", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('cash_pressure')", name=op.f("ck_alerts_kind_values")),
        sa.CheckConstraint(
            "severity IN ('info', 'warning')", name=op.f("ck_alerts_severity_values")
        ),
        sa.CheckConstraint("status IN ('new', 'read')", name=op.f("ck_alerts_status_values")),
        sa.CheckConstraint(
            "(status = 'read') = (read_at IS NOT NULL)", name=op.f("ck_alerts_read_at_status")
        ),
        sa.CheckConstraint(
            "kind <> 'cash_pressure' OR account_id IS NOT NULL",
            name=op.f("ck_alerts_cash_pressure_account"),
        ),
        sa.CheckConstraint("read_at >= created_at", name=op.f("ck_alerts_read_after_created")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="RESTRICT", name=op.f("fk_alerts_user_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            ondelete="RESTRICT",
            name=op.f("fk_alerts_account_id_accounts"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alerts")),
        sa.UniqueConstraint("user_id", "dedup_key", name=op.f("uq_alerts_user_id_dedup_key")),
    )
    op.create_index(
        op.f("ix_alerts_user_id_status_created_at"), "alerts", ["user_id", "status", "created_at"]
    )
    op.create_index(op.f("ix_alerts_account_id"), "alerts", ["account_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_alerts_account_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_user_id_status_created_at"), table_name="alerts")
    op.drop_table("alerts")
