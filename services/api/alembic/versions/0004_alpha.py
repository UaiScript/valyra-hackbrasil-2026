"""Fontes e sinais do Alternative Alpha (ADR-0012).

`signals` é somente inserção: revisão nova é linha nova com `revision_id` maior, e um
trigger recusa UPDATE/DELETE. Assim o corte `as_of` reconstrói o que era conhecido em
cada instante, sem depender de histórico em outra tabela.

Revision ID: 0004_alpha
Revises: 0003_budgets
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_alpha"
down_revision = "0003_budgets"
branch_labels = None
depends_on = None

KINDS = (
    "macro_indicator",
    "climate_anomaly",
    "crop_estimate",
    "export",
    "price_move",
    "news_event",
)


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("license", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sources")),
        sa.UniqueConstraint("slug", name=op.f("uq_sources_slug")),
    )
    kinds = ", ".join(f"'{kind}'" for kind in KINDS)
    op.create_table(
        "signals",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("signal_key", sa.String(), nullable=False),
        sa.Column("revision_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at_estimated", sa.Boolean(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_url", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("revision_id >= 1", name=op.f("ck_signals_revision_positive")),
        sa.CheckConstraint(f"kind IN ({kinds})", name=op.f("ck_signals_kind_values")),
        sa.CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1",
            name=op.f("ck_signals_confidence_range"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="RESTRICT",
            name=op.f("fk_signals_source_id_sources"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_signals")),
        sa.UniqueConstraint(
            "signal_key", "revision_id", name=op.f("uq_signals_signal_key_revision_id")
        ),
    )
    op.create_index(
        op.f("ix_signals_signal_key_published_at"), "signals", ["signal_key", "published_at"]
    )
    op.create_index(op.f("ix_signals_published_at"), "signals", ["published_at"])
    op.create_index(op.f("ix_signals_kind"), "signals", ["kind"])
    # Revisões são fatos publicados: corrigir é inserir, nunca reescrever o passado.
    op.execute(
        """
        CREATE FUNCTION signals_insert_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'signals é somente inserção; grave uma nova revisão';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        "CREATE TRIGGER signals_insert_only BEFORE UPDATE OR DELETE ON signals "
        "FOR EACH ROW EXECUTE FUNCTION signals_insert_only();"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS signals_insert_only ON signals;")
    op.execute("DROP FUNCTION IF EXISTS signals_insert_only();")
    op.drop_index(op.f("ix_signals_kind"), table_name="signals")
    op.drop_index(op.f("ix_signals_published_at"), table_name="signals")
    op.drop_index(op.f("ix_signals_signal_key_published_at"), table_name="signals")
    op.drop_table("signals")
    op.drop_table("sources")
