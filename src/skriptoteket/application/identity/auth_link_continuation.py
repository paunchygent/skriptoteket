"""Auth-link continuation sanitizers and URL builders.

Purpose:
  Keep email-verification and password-reset links aligned with the frontend's
  `/auth/login` continuation contract by carrying only safe, same-origin
  destination hints and the known Klassrumskartan entry-origin nuance.

Relationships:
  - Consumed by identity handlers that generate verification and reset email
    links.
  - Mirrors the SPA auth-entry contract without depending on frontend code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

CLASSROOM_PLANNER_APP_ID = "classroom.group-seating-studio"
CLASSROOM_PLANNER_AUTHENTICATED_PATH = f"/apps/{CLASSROOM_PLANNER_APP_ID}"
AUTH_LOGIN_PATH = "/auth/login"
REMOVED_LEGACY_LOGIN_PATH = "/login"
CLASSROOM_PLANNER_ENTRY_ORIGIN_QUERY_KEY = "classroomPlannerEntryOrigin"

ClassroomPlannerEntryOrigin = Literal["dashboard", "catalog"]

_AUTH_ENTRY_URL_BASE = "https://skriptoteket.local"
_AUTH_ENTRY_LOOP_PATHS = frozenset({AUTH_LOGIN_PATH, REMOVED_LEGACY_LOGIN_PATH})


@dataclass(frozen=True)
class AuthLinkContinuation:
    """Sanitized continuation payload for auth-related links."""

    next_path: str | None = None
    classroom_planner_entry_origin: ClassroomPlannerEntryOrigin | None = None


def sanitize_auth_next_path(value: str | None) -> str | None:
    """Return one safe same-origin absolute app path or ``None``."""
    if not isinstance(value, str) or not value.startswith("/") or value.startswith("//"):
        return None

    parsed = urlparse(urljoin(_AUTH_ENTRY_URL_BASE, value))
    if parsed.path in _AUTH_ENTRY_LOOP_PATHS:
        return None

    return urlunparse(("", "", parsed.path, parsed.params, parsed.query, parsed.fragment))


def sanitize_classroom_planner_entry_origin(
    value: str | None,
) -> ClassroomPlannerEntryOrigin | None:
    """Return one supported classroom-planner origin hint or ``None``."""
    if value == "dashboard":
        return "dashboard"
    if value == "catalog":
        return "catalog"
    return None


def sanitize_auth_link_continuation(
    *,
    next_path: str | None,
    classroom_planner_entry_origin: str | None,
) -> AuthLinkContinuation:
    """Normalize one continuation so only safe auth-handoff hints remain."""
    sanitized_next_path = sanitize_auth_next_path(next_path)
    sanitized_origin = sanitize_classroom_planner_entry_origin(classroom_planner_entry_origin)

    if sanitized_next_path is None:
        return AuthLinkContinuation(next_path=None, classroom_planner_entry_origin=None)

    parsed = urlparse(urljoin(_AUTH_ENTRY_URL_BASE, sanitized_next_path))
    if parsed.path != CLASSROOM_PLANNER_AUTHENTICATED_PATH:
        sanitized_origin = None

    return AuthLinkContinuation(
        next_path=sanitized_next_path,
        classroom_planner_entry_origin=sanitized_origin,
    )


def append_auth_link_continuation(
    *,
    base_url: str,
    path: str,
    token_name: str,
    token_value: str,
    next_path: str | None,
    classroom_planner_entry_origin: str | None,
) -> str:
    """Build one verification/reset URL with the sanitized continuation payload."""
    continuation = sanitize_auth_link_continuation(
        next_path=next_path,
        classroom_planner_entry_origin=classroom_planner_entry_origin,
    )
    parsed = urlparse(urljoin(base_url, path))
    query_items = [(token_name, token_value)]

    if continuation.next_path is not None:
        query_items.append(("next", continuation.next_path))
    if continuation.classroom_planner_entry_origin is not None:
        query_items.append(
            (
                CLASSROOM_PLANNER_ENTRY_ORIGIN_QUERY_KEY,
                continuation.classroom_planner_entry_origin,
            )
        )

    existing_query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=False)
        if key not in {token_name, "next", CLASSROOM_PLANNER_ENTRY_ORIGIN_QUERY_KEY}
    ]

    return urlunparse(parsed._replace(query=urlencode(existing_query_items + query_items)))
