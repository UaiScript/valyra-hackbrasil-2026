"""Rotas HTTP dos alertas; o nome de cada rota é o operationId do contrato."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from valyra.alerts import service
from valyra.alerts.schemas import AlertOut, AlertUpdate
from valyra.core.db import get_session
from valyra.core.deps import get_current_user_id
from valyra.core.errors import error_responses
from valyra.core.pagination import Page, PageParams

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"], responses=error_responses(422))

SessionDep = Annotated[Session, Depends(get_session)]
UserIdDep = Annotated[UUID, Depends(get_current_user_id)]


@router.get("", name="alerts_list", response_model=Page[AlertOut])
def list_alerts(
    page: Annotated[PageParams, Depends()], session: SessionDep, user_id: UserIdDep
) -> Page[AlertOut]:
    items, total = service.list_alerts(session, user_id, page.limit, page.offset)
    return Page[AlertOut](
        items=[AlertOut.model_validate(a) for a in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.patch(
    "/{id}", name="alerts_update", response_model=AlertOut, responses=error_responses(404)
)
def update_alert(id: UUID, body: AlertUpdate, session: SessionDep, user_id: UserIdDep) -> AlertOut:
    # body.status só aceita "read"; a validação já garantiu a única transição permitida.
    return AlertOut.model_validate(service.mark_read(session, user_id, id))
