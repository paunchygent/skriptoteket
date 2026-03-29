"""Integration tests for websocket Dishka resolution under Starlette middleware.

Purpose:
    Prove the explicit websocket DI path used by ST-07-07 works with the real
    `starlette-dishka` middleware instead of a synthetic stand-in object.

Relationships:
    - Covers `skriptoteket.web.dishka_dependencies.resolve_from_websocket`.
    - Complements HTTP route proofs in `test_observability_routes.py`.
"""

from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette_dishka import setup_dishka

from skriptoteket.config import Settings
from skriptoteket.web.dishka_dependencies import resolve_from_websocket


class WebSocketSettingsProvider(Provider):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings

    @provide(scope=Scope.SESSION)
    def settings(self) -> Settings:
        return self._settings


def _build_app(settings: Settings) -> FastAPI:
    app = FastAPI()

    @app.websocket("/ws/settings")
    async def websocket_settings(websocket: WebSocket) -> None:
        await websocket.accept()
        resolved = await resolve_from_websocket(websocket, Settings)
        await websocket.send_json(
            {
                "app_name": resolved.APP_NAME,
                "has_container": hasattr(websocket.state, "dishka_container"),
            }
        )
        await websocket.close()

    container = make_async_container(WebSocketSettingsProvider(settings))
    setup_dishka(container, app)
    return app


def test_websocket_resolution_uses_starlette_dishka_state() -> None:
    settings = Settings.model_construct(
        APP_NAME="Skriptoteket",
        APP_VERSION="0.2.0",
        SERVICE_NAME="skriptoteket",
        ENVIRONMENT="test",
        ARTIFACTS_ROOT=Settings().ARTIFACTS_ROOT,
    )
    app = _build_app(settings)

    with TestClient(app) as client, client.websocket_connect("/ws/settings") as websocket:
        payload = websocket.receive_json()

    assert payload == {
        "app_name": "Skriptoteket",
        "has_container": True,
    }
