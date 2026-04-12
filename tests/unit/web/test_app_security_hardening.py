"""Security-surface tests for the production web app.

Purpose:
    Verify low-risk app-level hardening that protects the public edge even when
    nginx configuration drifts.

Relationships:
    - Exercises `skriptoteket.config.Settings` defaults.
    - Verifies `skriptoteket.web.middleware.security_headers`.
    - Verifies `skriptoteket.web.app.create_app` wiring.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.testclient import TestClient

from skriptoteket.config import Settings
from skriptoteket.web import app as web_app
from skriptoteket.web.middleware.correlation import CorrelationMiddleware
from skriptoteket.web.middleware.security_headers import SecurityHeadersMiddleware


def test_settings_disable_docs_by_default_in_production() -> None:
    settings = Settings.model_construct(ENVIRONMENT="production", ENABLE_DOCS=None)
    assert settings.enable_docs is False


def test_settings_keep_docs_enabled_by_default_outside_production() -> None:
    settings = Settings.model_construct(ENVIRONMENT="development", ENABLE_DOCS=None)
    assert settings.enable_docs is True


def test_settings_parse_allowed_hosts_csv() -> None:
    settings = Settings.model_construct(ALLOWED_HOSTS="localhost, api.example.org ,localhost")
    assert settings.allowed_hosts == frozenset(
        {"localhost", "api.example.org", "skriptoteket_web", "skriptoteket-web"}
    )


def test_security_headers_middleware_adds_expected_headers() -> None:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/ping")
    async def ping() -> JSONResponse:
        return JSONResponse({"ok": True})

    with TestClient(app) as client:
        response = client.get("/ping")

    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == "geolocation=(), camera=(), microphone=()"


def test_create_app_disables_docs_and_openapi_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings.model_construct(
        APP_NAME="Skriptoteket",
        APP_VERSION="0.2.0",
        ENVIRONMENT="production",
        ENABLE_DOCS=None,
        ALLOWED_HOSTS="localhost,127.0.0.1,skriptoteket.hule.education",
    )
    _patch_create_app_dependencies(monkeypatch=monkeypatch, settings=settings)

    app = web_app.create_app()
    route_paths = {
        path for route in app.routes if isinstance(path := getattr(route, "path", None), str)
    }

    assert "/docs" not in route_paths
    assert "/redoc" not in route_paths
    assert "/openapi.json" not in route_paths


def test_create_app_registers_host_validation_and_security_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings.model_construct(
        APP_NAME="Skriptoteket",
        APP_VERSION="0.2.0",
        ENVIRONMENT="production",
        ENABLE_DOCS=None,
        ALLOWED_HOSTS="localhost,127.0.0.1,skriptoteket.hule.education",
    )
    _patch_create_app_dependencies(monkeypatch=monkeypatch, settings=settings)

    app = web_app.create_app()

    middleware_by_class = {entry.cls: entry for entry in app.user_middleware}
    trusted_host_entry = next(
        entry for entry in app.user_middleware if entry.cls is TrustedHostMiddleware
    )
    assert CorrelationMiddleware in middleware_by_class
    assert SecurityHeadersMiddleware in middleware_by_class
    assert TrustedHostMiddleware in middleware_by_class
    assert set(cast(Sequence[str], trusted_host_entry.kwargs["allowed_hosts"])) == {
        "localhost",
        "127.0.0.1",
        "skriptoteket.hule.education",
    }


def test_create_app_rejects_testserver_host_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings.model_construct(
        APP_NAME="Skriptoteket",
        APP_VERSION="0.2.0",
        ENVIRONMENT="production",
        ENABLE_DOCS=None,
        ALLOWED_HOSTS="localhost,127.0.0.1,::1,skriptoteket.hule.education",
    )
    _patch_create_app_dependencies(monkeypatch=monkeypatch, settings=settings)

    app = web_app.create_app()

    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/healthz", headers={"host": "testserver"})

    assert response.status_code == 400


def _patch_create_app_dependencies(
    *,
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    monkeypatch.setattr(web_app, "Settings", lambda: settings)
    monkeypatch.setattr(web_app, "configure_logging", lambda **_: None)
    monkeypatch.setattr(web_app, "init_tracing", lambda *_: None)
    monkeypatch.setattr(web_app, "create_container", lambda _settings: object())
    monkeypatch.setattr(web_app, "setup_dishka", lambda *args, **kwargs: None)

    async def _fake_check_smtp(_settings: Settings) -> tuple[str, None]:
        return ("healthy", None)

    async def _fake_ensure_database_revision_is_current(_settings: Settings) -> None:
        return None

    monkeypatch.setattr(web_app, "check_smtp", _fake_check_smtp)
    monkeypatch.setattr(
        web_app,
        "ensure_database_revision_is_current",
        _fake_ensure_database_revision_is_current,
    )
