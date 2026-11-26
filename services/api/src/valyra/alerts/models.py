"""Tabela alerts (modelagem, seção 6), só com cash_pressure até o Alpha."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from valyra.core.db import Base


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        # market_signal entra com o Alpha, junto com signal_id/asset_id e suas FKs.
        CheckConstraint("kind IN ('cash_pressure')", name="kind_values"),
        CheckConstraint("severity IN ('info', 'warning')", name="severity_values"),
        CheckConstraint("status IN ('new', 'read')", name="status_values"),
        CheckConstraint("(status = 'read') = (read_at IS NOT NULL)", name="read_at_status"),
        CheckConstraint(
            "kind <> 'cash_pressure' OR account_id IS NOT NULL", name="cash_pressure_account"
        ),
        CheckConstraint("read_at >= created_at", name="read_after_created"),
        # A deduplicação por usuário é o que torna a geração idempotente.
        UniqueConstraint("user_id", "dedup_key"),
        Index("ix_alerts_user_id_status_created_at", "user_id", "status", "created_at"),
        Index("ix_alerts_account_id", "account_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, server_default=text("'new'"))
    title: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    # Snapshot das evidências na geração; não muda se a projeção mudar depois. none_as_null
    # faz None virar NULL do SQL (barrado pelo NOT NULL), e não o literal JSON null.
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB(none_as_null=True))
    # FK por nome de tabela: o banco garante a conta sem o código importar Finance.
    account_id: Mapped[UUID | None] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"))
    dedup_key: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
