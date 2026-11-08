"""Saúde real do PostgreSQL sem expor destinos ou erros da conexão."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from valyra.core.db import get_session

router = APIRouter()


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    postgres: Literal["ok", "error"]


@router.get(
    "/health",
    name="system_health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse}},
)
def health(session: Annotated[Session, Depends(get_session)]) -> HealthResponse | JSONResponse:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "degraded", "postgres": "error"})
    return HealthResponse(status="ok", postgres="ok")
