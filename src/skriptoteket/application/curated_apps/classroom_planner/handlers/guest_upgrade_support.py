"""Shared support types for Klassrumskartan guest-upgrade orchestration.

This module holds the small helper models and deterministic utility
functions shared by the authenticated guest-upgrade collaborators so the main
handler can stay focused on orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from skriptoteket.domain.curated_apps.classroom_planner.models import RoomTemplate, Roster


@dataclass(frozen=True, slots=True)
class MappedRoster:
    """Describe one resolved roster plus guest-to-owner student identity mapping."""

    roster: Roster
    student_id_map: dict[str, str]
    was_created: bool


@dataclass(frozen=True, slots=True)
class MappedTemplate:
    """Describe one resolved room template plus guest-to-owner seat identity mapping."""

    template: RoomTemplate
    seat_id_map: dict[str, str]
    was_created: bool


def parse_guest_datetime(value: str, *, fallback: datetime) -> datetime:
    """Parse guest-snapshot timestamps while tolerating invalid local payloads."""

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return fallback


def build_preview_uuid(*, snapshot_id: str, entity_type: str, local_id: str) -> UUID:
    """Build deterministic preview-only UUIDs without mutating real owner state."""

    return uuid5(NAMESPACE_URL, f"guest-upgrade:{snapshot_id}:{entity_type}:{local_id}")
