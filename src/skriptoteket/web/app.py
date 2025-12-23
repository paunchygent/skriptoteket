from pathlib import Path

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from skriptoteket.config import Settings
from skriptoteket.di import create_container
from skriptoteket.observability.logging import configure_logging
from skriptoteket.observability.tracing import init_tracing
from skriptoteket.web.middleware.correlation import CorrelationMiddleware
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from skriptoteket.web.middleware.metrics import metrics_middleware
from skriptoteket.web.middleware.tracing import tracing_middleware
from skriptoteket.web.router import router as web_router
from skriptoteket.web.routes.observability import router as observability_router


def create_app() -> FastAPI:
    settings = Settings()
    configure_logging(
        service_name=settings.SERVICE_NAME,
        environment=settings.ENVIRONMENT,
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
    )

    # Initialize tracing (opt-in via OTEL_TRACING_ENABLED env var)
    if settings.OTEL_TRACING_ENABLED:
        init_tracing(settings.SERVICE_NAME)

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.ENABLE_DOCS else None,
    )

    # Middleware order: tracing → metrics → correlation → error_handler
    # (registered in reverse order of execution)
    app.add_middleware(CorrelationMiddleware)
    app.middleware("http")(error_handler_middleware)
    app.middleware("http")(metrics_middleware)
    app.middleware("http")(tracing_middleware)

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    container = create_container(settings)
    setup_dishka(container, app)

    # Observability endpoints (public, no auth)
    app.include_router(observability_router)

    # Application routes
    app.include_router(web_router)

    return app


app = create_app()
