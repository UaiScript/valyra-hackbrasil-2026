"""Fontes e sinais Alpha (ADR-0012); `signals` só recebe inserções."""

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from valyra.core.db import Base


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (UniqueConstraint("slug"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    slug: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String)
    license: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        UniqueConstraint("signal_key", "revision_id"),
        CheckConstraint("revision_id >= 1", name="revision_positive"),
        CheckConstraint(
            "kind IN ('macro_indicator', 'climate_anomaly', 'crop_estimate', 'export', "
            "'price_move', 'news_event')",
            name="kind_values",
        ),
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1", name="confidence_range"
        ),
        Index("ix_signals_signal_key_published_at", "signal_key", "published_at"),
        Index("ix_signals_published_at", "published_at"),
        Index("ix_signals_kind", "kind"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    signal_key: Mapped[str] = mapped_column(String)
    revision_id: Mapped[int] = mapped_column(Integer)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(Text)
    observation_date: Mapped[date_type] = mapped_column(Date)
    # Indicador genérico acompanhado de unidade, nunca dinheiro (ADR-0012, consequências).
    value: Mapped[Decimal | None] = mapped_column(Numeric)
    unit: Mapped[str | None] = mapped_column(String)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_at_estimated: Mapped[bool] = mapped_column(Boolean)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
