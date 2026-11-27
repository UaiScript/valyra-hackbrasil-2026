"""Rota HTTP do relatório semanal de notícias; só leitura, quem grava é a coleta agendada."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from valyra.alpha import news_service
from valyra.alpha.news import THEME_RULE
from valyra.alpha.news_schemas import NewsItemOut, NewsThemeOut, WeeklyNewsOut
from valyra.alpha.schemas import SourceOut
from valyra.core.db import get_session
from valyra.core.errors import error_responses

router = APIRouter(prefix="/api/v1/alpha", tags=["alpha"], responses=error_responses(422))

SessionDep = Annotated[Session, Depends(get_session)]


def _source(source) -> SourceOut:
    return SourceOut(slug=source.slug, name=source.name, url=source.url, license=source.license)


@router.get("/news/weekly", name="alpha_get_weekly_news", response_model=WeeklyNewsOut)
def get_weekly_news(
    session: SessionDep,
    as_of: Annotated[
        AwareDatetime | None,
        Query(description="Fim da semana do relatório, com fuso; ausente usa o instante atual"),
    ] = None,
) -> WeeklyNewsOut:
    now = datetime.now(UTC)
    # Mesmo critério do radar: corte no futuro não traz nada a mais.
    cut = now if as_of is None else min(as_of.astimezone(UTC), now)
    report = news_service.get_weekly_report(session, cut)
    return WeeklyNewsOut(
        as_of=report.as_of,
        week_start=report.week_start,
        rule=THEME_RULE,
        total_items=report.total,
        unmatched_items=report.unmatched,
        themes=[
            NewsThemeOut(
                key=view.theme.key,
                title=view.theme.title,
                why=view.theme.why,
                category_slugs=list(view.theme.category_slugs),
                items=[
                    NewsItemOut(
                        signal_key=item.signal_key,
                        title=item.title,
                        summary=item.summary,
                        url=item.url,
                        source=_source(item.source),
                        observation_date=item.observation_date,
                        published_at=item.published_at,
                        ingested_at=item.ingested_at,
                    )
                    for item in view.items
                ],
            )
            for view in report.themes
        ],
        sources=[_source(source) for source in report.sources],
        last_ingested_at=report.last_ingested_at,
    )
