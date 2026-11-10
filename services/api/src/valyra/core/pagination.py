"""Tipos compartilhados das futuras listagens, conforme Issue #9."""

from fastapi import Query
from pydantic import BaseModel


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


class PageParams:
    def __init__(self, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)) -> None:
        self.limit = limit
        self.offset = offset
