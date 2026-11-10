"""Composição HTTP mínima; endpoints Finance permanecem nas Issues #14/#15."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from valyra.core.config import get_settings
from valyra.core.errors import register_error_handlers
from valyra.core.health import router
from valyra.core.openapi import operation_id


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Valyra API", version="0.1.0", generate_unique_id_function=operation_id)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origin],
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    register_error_handlers(app)
    app.include_router(router)
    return app
