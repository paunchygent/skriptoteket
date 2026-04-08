from __future__ import annotations

from skriptoteket.application.identity.auth_link_continuation import (
    append_auth_link_continuation,
    sanitize_auth_link_continuation,
)


def test_sanitize_auth_link_continuation_drops_external_and_looping_targets() -> None:
    assert (
        sanitize_auth_link_continuation(
            next_path="https://example.com/phish",
            classroom_planner_entry_origin="dashboard",
        ).next_path
        is None
    )

    assert (
        sanitize_auth_link_continuation(
            next_path="/auth/login",
            classroom_planner_entry_origin="dashboard",
        ).next_path
        is None
    )


def test_sanitize_auth_link_continuation_keeps_origin_only_for_classroom_planner() -> None:
    continuation = sanitize_auth_link_continuation(
        next_path="/apps/classroom.group-seating-studio",
        classroom_planner_entry_origin="dashboard",
    )
    assert continuation.next_path == "/apps/classroom.group-seating-studio"
    assert continuation.classroom_planner_entry_origin == "dashboard"

    non_planner = sanitize_auth_link_continuation(
        next_path="/browse",
        classroom_planner_entry_origin="dashboard",
    )
    assert non_planner.next_path == "/browse"
    assert non_planner.classroom_planner_entry_origin is None


def test_append_auth_link_continuation_merges_existing_query_without_duplicate_fields() -> None:
    assert (
        append_auth_link_continuation(
            base_url="http://127.0.0.1:5173",
            path="/verify-email?locale=sv",
            token_name="token",
            token_value="verification-token",
            next_path="/browse",
            classroom_planner_entry_origin="dashboard",
        )
        == "http://127.0.0.1:5173/verify-email?locale=sv&token=verification-token&next=%2Fbrowse"
    )
