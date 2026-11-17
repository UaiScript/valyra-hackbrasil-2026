"""Envelope HTTP definido na Issue #9, sem criar códigos do domínio Finance."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any]


class ErrorResponse(BaseModel):
    """Forma única de toda resposta de erro; declarada no OpenAPI por error_responses()."""

    error: ErrorBody


_DESCRIPTIONS = {
    404: "Recurso não encontrado",
    413: "Arquivo acima do limite",
    422: "Entrada inválida",
}


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    # Declarar o 422 explicitamente impede o FastAPI de injetar HTTPValidationError,
    # schema que não corresponde ao envelope devolvido pelo handler de validação.
    return {
        status: {"model": ErrorResponse, "description": _DESCRIPTIONS[status]}
        for status in status_codes
    }


class AppError(Exception):
    def __init__(
        self, code: str, message: str, status_code: int, details: dict | None = None
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {"code": exc.code, "message": exc.message, "details": exc.details or {}}
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Contextos de validadores podem conter exceções Python, não serializáveis em JSON.
        errors = jsonable_encoder(exc.errors(), custom_encoder={Exception: str})
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Entrada inválida",
                    "details": {"errors": errors},
                }
            },
        )
