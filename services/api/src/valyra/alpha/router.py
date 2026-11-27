"""Rotas HTTP do Alpha: só leitura; quem grava sinais é a coleta agendada (ADR-0012)."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from valyra.alpha import service
from valyra.alpha.domain import format_decimal
from valyra.alpha.schemas import (
    DerivedSignalOut,
    HistoryPointOut,
    IndicatorOut,
    PointOut,
    RadarOut,
    SourceOut,
)
from valyra.core.db import get_session
from valyra.core.errors import error_responses

router = APIRouter(prefix="/api/v1/alpha", tags=["alpha"], responses=error_responses(422))

SessionDep = Annotated[Session, Depends(get_session)]


def _point(point: service.Point) -> PointOut:
    return PointOut(
        signal_key=point.signal_key,
        revision_id=point.revision_id,
        observation_date=point.observation_date,
        value=format_decimal(point.value),
        published_at=point.published_at,
        published_at_estimated=point.published_at_estimated,
        ingested_at=point.ingested_at,
        source_url=point.source_url,
    )


@router.get("/radar", name="alpha_get_radar", response_model=RadarOut)
def get_radar(
    session: SessionDep,
    as_of: Annotated[
        AwareDatetime | None,
        Query(description="Corte do replay, com fuso; ausente usa o instante atual"),
    ] = None,
) -> RadarOut:
    now = datetime.now(UTC)
    # Corte no futuro não traz nada a mais e confundiria o rótulo da tela.
    cut = now if as_of is None else min(as_of.astimezone(UTC), now)
    radar = service.get_radar(session, cut)
    return RadarOut(
        as_of=radar.as_of,
        last_ingested_at=radar.last_ingested_at,
        indicators=[
            IndicatorOut(
                key=view.series.key,
                title=view.series.title,
                unit=view.series.unit,
                unit_label=view.series.unit_label,
                kind=view.series.kind,
                source=SourceOut(
                    slug=view.source.slug,
                    name=view.source.name,
                    url=view.source.url,
                    license=view.source.license,
                ),
                latest=_point(view.history[-1]),
                previous=_point(view.history[-2]) if len(view.history) > 1 else None,
                history=[
                    HistoryPointOut(
                        observation_date=p.observation_date, value=format_decimal(p.value)
                    )
                    for p in view.history
                ],
            )
            for view in radar.indicators
        ],
        signals=[
            DerivedSignalOut(
                key=s.key,
                title=s.title,
                summary=s.summary,
                observation_date=s.observation_date,
                published_at=s.published_at,
                rule=s.rule,
                evidence_keys=list(s.evidence_keys),
            )
            for s in radar.signals
        ],
    )
