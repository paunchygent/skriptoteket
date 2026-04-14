"""Unit tests for PR-0254 HuleEdu provider-lane preflight.

Purpose:
    Verify that the retained Skriptoteket cutover proof fails provider surface
    problems before Playwright navigation.

Relationships:
    - Exercises `scripts.playwright_pr_0254_auth_cutover` preflight helpers.
    - Complements the manifest tests for `PR-0254` retained evidence.
"""

from __future__ import annotations

import pytest

from scripts._pr_0254_auth_cutover_browser import LoopbackLane
from scripts.playwright_pr_0254_auth_cutover import (
    ProviderLanePreflightError,
    _preflight_provider_lanes,
)


def _lane(name: str, *, host: str, login_origin: str) -> LoopbackLane:
    return LoopbackLane(
        name=name,  # type: ignore[arg-type]
        base_url=f"http://{host}:5173",
        huleedu_login_origin=login_origin,
        huleedu_auth_origin=f"http://{host}:8080",
    )


def test_preflight_passes_when_gateway_and_login_ui_are_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both required provider surfaces returning 200 allows browser launch."""

    monkeypatch.setattr("scripts.playwright_pr_0254_auth_cutover._http_status", lambda _url: 200)

    _preflight_provider_lanes(
        [_lane("localhost", host="localhost", login_origin="http://localhost:5174")]
    )


def test_preflight_classifies_127_login_refusal_as_provider_regression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing 127 login UI is a HuleEdu provider-lane failure."""

    def fake_status(url: str) -> int:
        if url == "http://127.0.0.1:5174/login":
            raise ProviderLanePreflightError(f"{url} failed: connection refused")
        return 200

    monkeypatch.setattr("scripts.playwright_pr_0254_auth_cutover._http_status", fake_status)

    with pytest.raises(ProviderLanePreflightError, match="HuleEdu provider regression") as exc:
        _preflight_provider_lanes(
            [
                _lane("localhost", host="localhost", login_origin="http://localhost:5174"),
                _lane("127", host="127.0.0.1", login_origin="http://127.0.0.1:5174"),
            ]
        )

    assert "auth-integration fe-dev" in str(exc.value)
    assert "http://127.0.0.1:5174/login" in str(exc.value)
