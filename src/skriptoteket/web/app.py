from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from skriptoteket.config import Settings
from skriptoteket.di import create_container
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from skriptoteket.web.router import router as web_router


def create_app() -> FastAPI:
    settings = Settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.ENABLE_DOCS else None,
    )

    app.middleware("http")(error_handler_middleware)

    container = create_container(settings)
    setup_dishka(container, app)

    app.include_router(web_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
