from pathlib import Path

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from skriptoteket.config import Settings
from skriptoteket.di import create_container
from skriptoteket.observability.logging import configure_logging
from skriptoteket.web.middleware.correlation import CorrelationMiddleware
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from skriptoteket.web.router import router as web_router


def create_app() -> FastAPI:
    settings = Settings()
    configure_logging(
        service_name=settings.SERVICE_NAME,
        environment=settings.ENVIRONMENT,
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
    )

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.ENABLE_DOCS else None,
    )

    app.add_middleware(CorrelationMiddleware)
    app.middleware("http")(error_handler_middleware)

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    container = create_container(settings)
    setup_dishka(container, app)

    app.include_router(web_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
