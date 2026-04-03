"""Unit tests for anonymous public helper throttling."""

from __future__ import annotations

from datetime import datetime, timedelta

from skriptoteket.infrastructure.security.public_helper_request_throttle import (
    InMemoryPublicHelperRequestThrottle,
)


def test_public_helper_throttle_allows_requests_under_limit() -> None:
    throttle = InMemoryPublicHelperRequestThrottle(max_requests=2, window_seconds=60)
    now = datetime(2026, 4, 3, 12, 0, 0)

    decision = throttle.evaluate_request(
        app_id="classroom.group-seating-studio",
        helper_name="roster_import_preview",
        client_ip="203.0.113.4",
        user_agent="pytest",
        now=now,
    )

    assert decision.is_rate_limited is False
    assert decision.retry_after_seconds is None


def test_public_helper_throttle_returns_retry_after_when_window_is_exhausted() -> None:
    throttle = InMemoryPublicHelperRequestThrottle(max_requests=2, window_seconds=60)
    now = datetime(2026, 4, 3, 12, 0, 0)

    throttle.record_request(
        app_id="classroom.group-seating-studio",
        helper_name="roster_import_preview",
        client_ip="203.0.113.4",
        user_agent="pytest",
        now=now,
    )
    throttle.record_request(
        app_id="classroom.group-seating-studio",
        helper_name="roster_import_preview",
        client_ip="203.0.113.4",
        user_agent="pytest",
        now=now + timedelta(seconds=1),
    )

    decision = throttle.evaluate_request(
        app_id="classroom.group-seating-studio",
        helper_name="roster_import_preview",
        client_ip="203.0.113.4",
        user_agent="pytest",
        now=now + timedelta(seconds=30),
    )

    assert decision.is_rate_limited is True
    assert decision.retry_after_seconds == 30


def test_public_helper_throttle_prunes_expired_requests() -> None:
    throttle = InMemoryPublicHelperRequestThrottle(max_requests=1, window_seconds=60)
    now = datetime(2026, 4, 3, 12, 0, 0)

    throttle.record_request(
        app_id="classroom.group-seating-studio",
        helper_name="roster_import_preview",
        client_ip="203.0.113.4",
        user_agent="pytest",
        now=now,
    )

    decision = throttle.evaluate_request(
        app_id="classroom.group-seating-studio",
        helper_name="roster_import_preview",
        client_ip="203.0.113.4",
        user_agent="pytest",
        now=now + timedelta(seconds=61),
    )

    assert decision.is_rate_limited is False
