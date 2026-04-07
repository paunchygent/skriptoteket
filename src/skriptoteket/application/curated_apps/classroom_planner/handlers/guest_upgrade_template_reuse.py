"""Exact-match room-template reuse helpers for Klassrumskartan guest upgrades.

This module isolates canonical template-signature and seat-remap logic used by
`guest_upgrade_assets.py` so the authenticated upgrade asset importer can stay
focused on non-destructive import policy instead of coordinate-matching details.
"""

from __future__ import annotations

from collections.abc import Iterable

from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    GuestUpgradeTemplatePayload,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RoomFixture,
    RoomTemplate,
    Seat,
)

TemplateSignature = tuple[
    str,
    int | None,
    int | None,
    tuple[tuple[int, int, str], ...],
    tuple[tuple[str, int, int, int, int, str], ...],
]


def seat_signature(seat: Seat) -> tuple[int, int, str]:
    """Return the portable seat-match signature used for exact template reuse."""

    return (seat.x, seat.y, seat.zone or "")


def fixture_signature(fixture: RoomFixture) -> tuple[str, int, int, int, int, str]:
    """Return the portable fixture-match signature used for exact template reuse."""

    return (
        fixture.type.value,
        fixture.x,
        fixture.y,
        fixture.width,
        fixture.height,
        fixture.label or "",
    )


def guest_template_signature(template: GuestUpgradeTemplatePayload) -> TemplateSignature:
    """Return the canonical exact-match signature for one guest template payload."""

    return (
        template.name,
        template.grid_cols,
        template.grid_rows,
        tuple(sorted(seat_signature(seat) for seat in template.seats)),
        tuple(sorted(fixture_signature(fixture) for fixture in template.fixtures)),
    )


def room_template_signature(template: RoomTemplate) -> TemplateSignature:
    """Return the canonical exact-match signature for one persisted room template."""

    return (
        template.name,
        template.grid_cols,
        template.grid_rows,
        tuple(sorted(seat_signature(seat) for seat in template.seats)),
        tuple(sorted(fixture_signature(fixture) for fixture in template.fixtures)),
    )


def build_reused_template_seat_id_map(
    *,
    guest_template: GuestUpgradeTemplatePayload,
    template: RoomTemplate,
) -> dict[str, str] | None:
    """Build the deterministic guest-to-owner seat id map for one exact template match."""

    guest_seats = sorted(guest_template.seats, key=seat_signature)
    template_seats = sorted(template.seats, key=seat_signature)
    if len(guest_seats) != len(template_seats):
        return None

    seat_id_map: dict[str, str] = {}
    for guest_seat, template_seat in zip(guest_seats, template_seats, strict=True):
        if seat_signature(guest_seat) != seat_signature(template_seat):
            return None
        seat_id_map[guest_seat.id] = template_seat.id
    return seat_id_map


def find_reusable_template_match(
    *,
    guest_template: GuestUpgradeTemplatePayload,
    existing_templates: Iterable[RoomTemplate],
) -> tuple[RoomTemplate, dict[str, str]] | None:
    """Return one exact reusable template match and its seat-id map, if any."""

    for template in existing_templates:
        if guest_template_signature(guest_template) != room_template_signature(template):
            continue
        seat_id_map = build_reused_template_seat_id_map(
            guest_template=guest_template,
            template=template,
        )
        if seat_id_map is not None:
            return template, seat_id_map
    return None
