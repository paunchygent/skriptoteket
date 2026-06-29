"""Shared Playwright auth route-recovery tests.

Domain purpose:
    Prove authenticated browser proof helpers can recover when HuleEdu login
    succeeds but the browser lands away from the requested app route.

Relationships:
    Exercises `scripts._playwright_auth` without launching a browser so route
    proof scripts can depend on the shared-auth recovery contract.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from unittest.mock import Mock
from urllib.parse import urlparse

import pytest
from playwright.sync_api import Page

from scripts._playwright_auth import login_via_auth_entry


class _FakeLocator:
    def __init__(
        self,
        *,
        visible: bool | Callable[[], bool] = False,
        enabled: bool = True,
        on_click: Callable[[], None] | None = None,
    ) -> None:
        self._visible = visible
        self._enabled = enabled
        self._on_click = on_click
        self.filled_values: list[str] = []

    @property
    def first(self) -> "_FakeLocator":
        return self

    def count(self) -> int:
        return 1 if self.is_visible() else 0

    def is_visible(self) -> bool:
        return self._visible() if callable(self._visible) else self._visible

    def is_enabled(self) -> bool:
        return self._enabled

    def fill(self, value: str) -> None:
        self.filled_values.append(value)

    def click(self) -> None:
        if self._on_click is not None:
            self._on_click()


@dataclass
class _FakePageState:
    url: str = ""
    visited_urls: list[str] = field(default_factory=list)
    waits: list[int] = field(default_factory=list)
    target_route_wait_count: int = 0


def _fake_page(*, route_ready_after_target_waits: int = 0) -> tuple[Page, _FakePageState]:
    state = _FakePageState()
    page = Mock(spec=Page)

    def goto(url: str, *, wait_until: str) -> None:
        state.url = url
        state.visited_urls.append(url)
        assert wait_until == "domcontentloaded"

    def get_by_role(role: str, *, name: re.Pattern[str]) -> _FakeLocator:
        assert role in {"heading", "link"}
        assert isinstance(name, re.Pattern)
        return _FakeLocator()

    def locator(selector: str) -> _FakeLocator:
        if selector == '[data-test="transcript-workflow-rail-shell"]':
            return _FakeLocator(
                visible=lambda: (
                    urlparse(state.url).path == "/apps/audio-transcription"
                    and state.target_route_wait_count >= route_ready_after_target_waits
                )
            )
        return _FakeLocator()

    def wait_for_timeout(timeout: int) -> None:
        if urlparse(state.url).path == "/apps/audio-transcription":
            state.target_route_wait_count += 1
        state.waits.append(timeout)

    page.goto.side_effect = goto
    page.get_by_role.side_effect = get_by_role
    page.locator.side_effect = locator
    page.wait_for_timeout.side_effect = wait_for_timeout
    page.title.return_value = "HuleEdu"
    return page, state


class _FakeExpectation:
    def __init__(self, target: _FakeLocator) -> None:
        self._target = target

    def to_be_visible(self, *, timeout: int | None = None) -> None:
        assert timeout is None or timeout >= 0
        assert self._target.is_visible()

    def to_be_enabled(self, *, timeout: int | None = None) -> None:
        assert timeout is None or timeout >= 0
        assert self._target.is_enabled()

    def or_(self, other: _FakeLocator) -> "_FakeOrExpectation":
        return _FakeOrExpectation(self._target, other)


class _FakeOrExpectation:
    def __init__(self, first: _FakeLocator, second: _FakeLocator) -> None:
        self._first = first
        self._second = second

    def to_be_visible(self, *, timeout: int | None = None) -> None:
        assert timeout is None or timeout >= 0
        assert self._first.is_visible() or self._second.is_visible()


class _FakeLoginResponse:
    def __init__(
        self,
        *,
        status: int,
        body: str,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.status = status
        self.url = "https://auth.hule.education/v1/auth/login"
        self.headers = dict(headers or {})
        self._body = body

    def text(self) -> str:
        return self._body

    def json(self) -> object:
        import json

        return json.loads(self._body)


@dataclass
class _FakeRateLimitState:
    responses: list[_FakeLoginResponse]
    url: str = ""
    visited_urls: list[str] = field(default_factory=list)
    waits: list[int] = field(default_factory=list)
    submitted_responses: list[_FakeLoginResponse] = field(default_factory=list)

    @property
    def logged_in(self) -> bool:
        return bool(self.submitted_responses and self.submitted_responses[-1].status == 200)

    def submit_login(self) -> None:
        response = self.responses.pop(0)
        self.submitted_responses.append(response)


class _FakeResponseContext:
    def __init__(self, state: _FakeRateLimitState) -> None:
        self._state = state

    def __enter__(self) -> "_FakeResponseContext":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    @property
    def value(self) -> _FakeLoginResponse:
        return self._state.submitted_responses[-1]


def _fake_rate_limit_page(
    responses: list[_FakeLoginResponse],
) -> tuple[Page, _FakeRateLimitState]:
    state = _FakeRateLimitState(responses=list(responses))
    page = Mock(spec=Page)
    email_input = _FakeLocator(visible=True)
    password_input = _FakeLocator(visible=True)
    login_button = _FakeLocator(visible=True, on_click=state.submit_login)
    success_locator = _FakeLocator(visible=lambda: state.logged_in)

    def goto(url: str, *, wait_until: str) -> None:
        state.url = url
        state.visited_urls.append(url)
        assert wait_until == "domcontentloaded"

    def get_by_role(role: str, *, name: re.Pattern[str]) -> _FakeLocator:
        assert isinstance(name, re.Pattern)
        if role == "button":
            return login_button
        return _FakeLocator()

    def locator(selector: str) -> _FakeLocator:
        if selector == "#email":
            return email_input
        if selector == "#password":
            return password_input
        if selector == '[data-test="proof-ready"]':
            return success_locator
        return _FakeLocator()

    page.goto.side_effect = goto
    page.get_by_role.side_effect = get_by_role
    page.locator.side_effect = locator
    page.expect_response.side_effect = lambda *_args, **_kwargs: _FakeResponseContext(state)
    page.wait_for_timeout.side_effect = state.waits.append
    page.title.return_value = "HuleEdu"
    return page, state


def test_auth_helper_recovers_to_requested_route_when_session_exists() -> None:
    page, state = _fake_page()

    login_via_auth_entry(
        page,
        base_url="https://skriptoteket.hule.education",
        email="teacher@example.invalid",
        password="secret",
        next_path="/apps/audio-transcription",
        success_heading_pattern=r"Transkribera samtal",
        success_selector='[data-test="transcript-workflow-rail-shell"]',
        recover_to_next_path=True,
        form_timeout_ms=0,
    )

    assert state.visited_urls == [
        "https://skriptoteket.hule.education/auth/login?next=/apps/audio-transcription",
        "https://skriptoteket.hule.education/apps/audio-transcription",
    ]


def test_auth_helper_waits_for_requested_route_ready_selector_after_recovery() -> None:
    page, state = _fake_page(route_ready_after_target_waits=2)

    login_via_auth_entry(
        page,
        base_url="https://skriptoteket.hule.education",
        email="teacher@example.invalid",
        password="secret",
        next_path="/apps/audio-transcription",
        success_heading_pattern=r"Transkribera samtal",
        success_selector='[data-test="transcript-workflow-rail-shell"]',
        recover_to_next_path=True,
        form_timeout_ms=0,
        success_timeout_ms=500,
    )

    assert state.visited_urls == [
        "https://skriptoteket.hule.education/auth/login?next=/apps/audio-transcription",
        "https://skriptoteket.hule.education/apps/audio-transcription",
    ]
    assert state.target_route_wait_count == 2


def test_auth_helper_preserves_strict_failure_without_recovery_opt_in() -> None:
    page, state = _fake_page()

    with pytest.raises(
        AssertionError,
        match="Neither the auth-entry form nor the expected post-login destination became visible",
    ):
        login_via_auth_entry(
            page,
            base_url="https://skriptoteket.hule.education",
            email="teacher@example.invalid",
            password="secret",
            next_path="/apps/audio-transcription",
            success_heading_pattern=r"Transkribera samtal",
            form_timeout_ms=0,
        )

    assert state.visited_urls == [
        "https://skriptoteket.hule.education/auth/login?next=/apps/audio-transcription"
    ]


def test_auth_helper_can_opt_into_bounded_huleedu_rate_limit_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("scripts._playwright_auth.expect", _FakeExpectation)
    page, state = _fake_rate_limit_page(
        [
            _FakeLoginResponse(
                status=400,
                body='{"error_code":"RATE_LIMIT","limit":5,"window_seconds":60}',
            ),
            _FakeLoginResponse(status=200, body='{"ok":true}'),
        ]
    )

    login_via_auth_entry(
        page,
        base_url="https://skriptoteket.hule.education",
        email="teacher@example.invalid",
        password="secret-password",
        next_path="/apps/exam-converter",
        success_heading_pattern=r"Konvertera prov",
        success_selector='[data-test="proof-ready"]',
        attempts=2,
        rate_limit_backoff=True,
        rate_limit_backoff_max_ms=1_250,
    )

    assert state.waits == [1_250]
    assert [response.status for response in state.submitted_responses] == [400, 200]
    assert state.visited_urls == [
        "https://skriptoteket.hule.education/auth/login?next=/apps/exam-converter",
        "https://skriptoteket.hule.education/auth/login?next=/apps/exam-converter",
    ]


def test_auth_helper_rate_limit_failure_text_redacts_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("scripts._playwright_auth.expect", _FakeExpectation)
    page, _state = _fake_rate_limit_page(
        [
            _FakeLoginResponse(
                status=400,
                body=(
                    '{"error_code":"RATE_LIMIT","limit":5,"window_seconds":60,'
                    '"detail":"teacher@example.invalid secret-password"}'
                ),
            ),
        ]
    )

    with pytest.raises(AssertionError) as exc_info:
        login_via_auth_entry(
            page,
            base_url="https://skriptoteket.hule.education",
            email="teacher@example.invalid",
            password="secret-password",
            next_path="/apps/exam-converter",
            success_heading_pattern=r"Konvertera prov",
            success_selector='[data-test="proof-ready"]',
            attempts=1,
            rate_limit_backoff=True,
            rate_limit_backoff_max_ms=1_250,
        )

    message = str(exc_info.value)
    assert "RATE_LIMIT" in message
    assert "limit=5" in message
    assert "teacher@example.invalid" not in message
    assert "secret-password" not in message
