from __future__ import annotations

from typing import AsyncIterator

import httpx
import pytest
from dishka import Scope, make_async_container, provide
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.config import Settings
from skriptoteket.di import InfrastructureProvider
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from skriptoteket.web.router import router as web_router


@pytest.fixture
def test_app(db_session: AsyncSession) -> FastAPI:
    """
    Creates a FastAPI app instance with a Dishka container that overrides
    the database session dependency to use the test's transaction-bound session.
    """
    settings = Settings()

    # Subclass InfrastructureProvider to override the 'session' provider
    class TestInfrastructureProvider(InfrastructureProvider):
        @provide(scope=Scope.REQUEST)
        async def session(self) -> AsyncIterator[AsyncSession]:
            # Start a SAVEPOINT for the request so that app rollbacks (e.g. on CONFLICT)
            # don't wipe out test fixture data that lives in the outer transaction.
            #
            # We also re-create the SAVEPOINT after each commit/rollback so handlers
            # that use multiple UoWs inside a single request remain isolated.
            await db_session.begin_nested()

            def _restart_savepoint(session, transaction) -> None:
                if (
                    transaction.nested
                    and transaction.parent is not None
                    and not transaction.parent.nested
                ):
                    session.begin_nested()

            event.listen(db_session.sync_session, "after_transaction_end", _restart_savepoint)
            try:
                # Yield the session from the pytest fixture.
                # We do NOT close it here; pytest fixture handles that.
                yield db_session
            finally:
                event.remove(db_session.sync_session, "after_transaction_end", _restart_savepoint)
                nested = db_session.get_nested_transaction()
                if nested is not None:
                    await nested.rollback()

    # Import the domain providers
    from skriptoteket.di import (
        CatalogProvider,
        IdentityProvider,
        ScriptingProvider,
        SuggestionsProvider,
    )

    # Create container with test infrastructure + all domain providers
    container = make_async_container(
        TestInfrastructureProvider(settings),
        IdentityProvider(),
        CatalogProvider(),
        ScriptingProvider(),
        SuggestionsProvider(),
    )

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
