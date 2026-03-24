"""Shared callback contract helpers for seating-export Sir Convert webhooks.

Purpose:
    Centralize the canonical shared callback-path rules for Klassrumskartan
    seating exports so job submission, reconciliation, and operator tooling all
    reason about the same upstream webhook contract.

Relationships:
    - Used by seating export-job orchestration when binding the shared webhook.
    - Used by production reconciliation tooling to validate canonical callback
      targeting deterministically.
"""

from __future__ import annotations

from urllib.parse import urlparse

SEATING_EXPORT_SHARED_WEBHOOK_PATH = (
    "/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs"
)
SEATING_EXPORT_WEBHOOK_EVENT_TYPES = (
    "job.succeeded",
    "job.failed",
    "job.canceled",
)


def build_seating_export_callback_url(*, callback_base_url: str) -> str:
    """Return the canonical shared callback URL for seating exports."""

    return f"{callback_base_url.rstrip('/')}{SEATING_EXPORT_SHARED_WEBHOOK_PATH}"


def is_seating_export_shared_callback_url(*, callback_url: str) -> bool:
    """Return whether a callback URL targets the shared seating-export route."""

    return urlparse(callback_url).path == SEATING_EXPORT_SHARED_WEBHOOK_PATH
