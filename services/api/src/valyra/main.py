"""Composição HTTP: health, Finance, alertas (#47), radar Alpha e explicações IA."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from valyra.ai.router import router as ai_router
from valyra.alerts.router import router as alerts_router
from valyra.alpha.forecast_router import router as alpha_forecast_router
from valyra.alpha.news_router import router as alpha_news_router
from valyra.alpha.router import router as alpha_router
from valyra.core.config import get_settings
from valyra.core.demo_profiles import PROFILE_HEADER
from valyra.core.errors import register_error_handlers
from valyra.core.health import router as health_router
from valyra.core.openapi import operation_id
from valyra.finance.router import router as finance_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Valyra API", version="0.1.0", generate_unique_id_function=operation_id)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origin],
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        # O cabeçalho do perfil da demo dispara preflight; sem liberá-lo o navegador bloqueia.
        allow_headers=["Content-Type", PROFILE_HEADER],
    )
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(finance_router)
    app.include_router(alerts_router)
    app.include_router(alpha_router)
    app.include_router(alpha_news_router)
    app.include_router(alpha_forecast_router)
    app.include_router(ai_router)
    return app
