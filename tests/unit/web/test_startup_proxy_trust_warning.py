"""Startup warning when production proxy trust is loopback-only.

Uvicorn reads its trusted-proxy set from the `FORWARDED_ALLOW_IPS` environment
variable (default `127.0.0.1`). When production keeps only loopback trusted,
the nginx-proxy hop is never trusted and the guest limiter shares one caller
key across all guests, so startup warns once with the operator hint.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from structlog.testing import capture_logs

from skriptoteket.config import Settings
from skriptoteket.web import app as web_app

_WARNING_EVENT = "public_guest_limiter_proxy_trust_loopback_only"


def test_production_without_forwarded_allow_ips_warns_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FORWARDED_ALLOW_IPS", raising=False)

    with capture_logs() as logs:
        web_app.warn_when_proxy_trust_is_loopback_only(settings=Settings(ENVIRONMENT="production"))

    warnings = [entry for entry in logs if entry.get("event") == _WARNING_EVENT]
    assert len(warnings) == 1
    record = repr(warnings[0])
    assert "127.0.0.1" not in record
    assert "::1" not in record


def test_production_with_loopback_only_value_warns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "127.0.0.1, ::1")

    with capture_logs() as logs:
        web_app.warn_when_proxy_trust_is_loopback_only(settings=Settings(ENVIRONMENT="production"))

    assert len([entry for entry in logs if entry.get("event") == _WARNING_EVENT]) == 1


def test_production_with_proxy_cidr_stays_silent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "172.18.0.0/16")

    with capture_logs() as logs:
        web_app.warn_when_proxy_trust_is_loopback_only(settings=Settings(ENVIRONMENT="production"))

    assert [entry for entry in logs if entry.get("event") == _WARNING_EVENT] == []


def test_development_without_forwarded_allow_ips_stays_silent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FORWARDED_ALLOW_IPS", raising=False)

    with capture_logs() as logs:
        web_app.warn_when_proxy_trust_is_loopback_only(settings=Settings(ENVIRONMENT="development"))

    assert [entry for entry in logs if entry.get("event") == _WARNING_EVENT] == []


async def _no_database_check(settings: Settings) -> None:
    return None


async def _healthy_smtp(settings: Settings) -> tuple[str, None]:
    return ("healthy", None)


async def test_lifespan_warns_when_production_proxy_trust_is_loopback_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The FastAPI lifespan actually calls the proxy-trust warning on startup."""
    monkeypatch.delenv("FORWARDED_ALLOW_IPS", raising=False)
    monkeypatch.setattr(web_app, "ensure_database_revision_is_current", _no_database_check)
    monkeypatch.setattr(web_app, "check_smtp", _healthy_smtp)

    with capture_logs() as logs:
        async with web_app._build_lifespan(settings=Settings(ENVIRONMENT="production"))(FastAPI()):
            pass

    assert len([entry for entry in logs if entry.get("event") == _WARNING_EVENT]) == 1
