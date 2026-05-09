"""Smart preference seeds for classroom planner draft creation.

Purpose:
    Convert profile-owned classroom planner preferences into the draft-local
    Smart flags used by authenticated seating and grouping workspaces.

Relationships:
    - Authenticated web routes build `DraftSmartPreferenceSeed` from
      `UserProfile`.
    - Draft lifecycle handlers resolve the seed only when creating a new draft,
      leaving existing active and historic drafts unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_DRAFT_SMART_ENABLED = True
DEFAULT_DRAFT_USE_HISTORY = True
DEFAULT_GROUPING_SEATING_DISTANCE_ENABLED = False


@dataclass(frozen=True, slots=True)
class DraftSmartPreferenceSeed:
    """Nullable authenticated preferences used to seed new drafts."""

    smart_enabled: bool | None = None
    use_history: bool | None = None
    grouping_seating_distance_enabled: bool | None = None


def resolve_draft_smart_settings(
    seed: DraftSmartPreferenceSeed | None,
) -> dict[str, bool]:
    """Return draft-local Smart settings from a nullable profile preference seed."""

    return {
        "smart_enabled": (
            seed.smart_enabled
            if seed and seed.smart_enabled is not None
            else DEFAULT_DRAFT_SMART_ENABLED
        ),
        "use_history": (
            seed.use_history if seed and seed.use_history is not None else DEFAULT_DRAFT_USE_HISTORY
        ),
        "grouping_seating_distance_enabled": (
            seed.grouping_seating_distance_enabled
            if seed and seed.grouping_seating_distance_enabled is not None
            else DEFAULT_GROUPING_SEATING_DISTANCE_ENABLED
        ),
    }
