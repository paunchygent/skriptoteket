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
from collections.abc import Callable
from dataclasses import dataclass, field
from unittest.mock import Mock
from urllib.parse import urlparse

import pytest
from playwright.sync_api import Page

from scripts._playwright_auth import login_via_auth_entry


class _FakeLocator:
    def __init__(self, *, visible: bool | Callable[[], bool] = False) -> None:
        self._visible = visible

    @property
    def first(self) -> "_FakeLocator":
        return self

    def count(self) -> int:
        return 1 if self.is_visible() else 0

    def is_visible(self) -> bool:
        return self._visible() if callable(self._visible) else self._visible


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
