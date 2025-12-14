from __future__ import annotations

from typing import AsyncIterator

import httpx
import pytest
from dishka import Scope, make_async_container, provide
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.config import Settings
from skriptoteket.di import AppProvider
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from skriptoteket.web.router import router as web_router


@pytest.fixture
def test_app(db_session: AsyncSession) -> FastAPI:
    """
    Creates a FastAPI app instance with a Dishka container that overrides
    the database session dependency to use the test's transaction-bound session.
    """
    settings = Settings()

    # Subclass AppProvider to override the 'session' provider
    class TestAppProvider(AppProvider):
        @provide(scope=Scope.REQUEST)
        async def session(self) -> AsyncIterator[AsyncSession]:
            # Yield the session from the pytest fixture.
            # We do NOT close it here; pytest fixture handles that.
            yield db_session

    # Create container with our test provider
    container = make_async_container(TestAppProvider(settings))

    # Construct app (mirroring src/skriptoteket/web/app.py logic)
    app = FastAPI(
        title="Test App",
        version="0.0.0",
    )

    app.middleware("http")(error_handler_middleware)

    # Setup Dishka with our test container
    setup_dishka(container, app)

    app.include_router(web_router)

    return app


@pytest.fixture
async def client(test_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=test_app),
                base_url="http://test",
            ) as c:
                yield c
