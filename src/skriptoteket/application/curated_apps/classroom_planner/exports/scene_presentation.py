"""Presentation normalization for classroom-planner seating export scenes.

Purpose:
    Normalize mutable room-template fixtures into one deterministic,
    presentation-ready export seam that owns localized labels, wall annotation
    placement metadata, coalescing rules, and grayscale-first contrast inputs.

Relationships:
    - Called by `translator.py` after room geometry has been converted into
      logical grid units.
    - Produces only renderer-independent export models from `models.py`.
    - Mirrors the frontend seating/preview presentation invariants so PDF
      export and preview stay aligned without duplicating heuristics per surface.
"""

from __future__ import annotations

from collections.abc import Iterable

from .models import (
    PosterSceneFixture,
    PosterSceneFixtureKind,
    PosterSceneFixturePlacement,
    PosterSceneFixtureTone,
    PosterSceneLabelOrientation,
    PosterSceneWallSide,
)

_CANONICAL_LABELS: dict[PosterSceneFixtureKind, str | None] = {
    PosterSceneFixtureKind.WHITEBOARD: "Whiteboard",
    PosterSceneFixtureKind.TEACHER_DESK: "Kateder",
    PosterSceneFixtureKind.DOOR: "Dörr",
    PosterSceneFixtureKind.WINDOW: "Fönster",
    PosterSceneFixtureKind.BENCH: "Bänk",
    PosterSceneFixtureKind.TABLE: None,
}

_FIXTURE_TONES: dict[PosterSceneFixtureKind, PosterSceneFixtureTone] = {
    PosterSceneFixtureKind.WHITEBOARD: PosterSceneFixtureTone.OUTLINE,
    PosterSceneFixtureKind.TEACHER_DESK: PosterSceneFixtureTone.STRONG,
    PosterSceneFixtureKind.DOOR: PosterSceneFixtureTone.OUTLINE,
    PosterSceneFixtureKind.WINDOW: PosterSceneFixtureTone.OUTLINE,
    PosterSceneFixtureKind.BENCH: PosterSceneFixtureTone.MUTED,
    PosterSceneFixtureKind.TABLE: PosterSceneFixtureTone.OUTLINE,
}


def normalize_scene_fixtures(
    fixtures: Iterable[PosterSceneFixture],
) -> list[PosterSceneFixture]:
    """Normalize localized labels, coalescing, and presentation metadata."""

    normalized = [_normalize_fixture(fixture) for fixture in fixtures]
    mergeable = {
        PosterSceneFixtureKind.BENCH: _merge_bench_fixtures,
        PosterSceneFixtureKind.WHITEBOARD: _merge_whiteboard_fixtures,
    }

    merged: list[PosterSceneFixture] = []
    consumed_ids: set[str] = set()
    for kind, merger in mergeable.items():
        kind_fixtures = [fixture for fixture in normalized if fixture.kind is kind]
        merged_kind = merger(kind_fixtures)
        merged.extend(merged_kind)
        for fixture in kind_fixtures:
            consumed_ids.add(fixture.fixture_id)

    passthrough = [fixture for fixture in normalized if fixture.fixture_id not in consumed_ids]
    return sorted(
        [*passthrough, *merged],
        key=lambda fixture: (
            fixture.placement.value,
            fixture.wall_side.value if fixture.wall_side is not None else "",
            fixture.y,
            fixture.x,
            fixture.kind.value,
            fixture.fixture_id,
        ),
    )


def _normalize_fixture(fixture: PosterSceneFixture) -> PosterSceneFixture:
    """Apply canonical label and presentation metadata to one fixture."""

    placement = (
        PosterSceneFixturePlacement.WALL
        if fixture.wall_side is not None
        else PosterSceneFixturePlacement.FLOOR
    )
    label = _CANONICAL_LABELS[fixture.kind]
    label_orientation = (
        PosterSceneLabelOrientation.VERTICAL
        if fixture.wall_side in {PosterSceneWallSide.LEFT, PosterSceneWallSide.RIGHT}
        else PosterSceneLabelOrientation.HORIZONTAL
    )
    return fixture.model_copy(
        update={
            "source_fixture_ids": fixture.source_fixture_ids or (fixture.fixture_id,),
            "placement": placement,
            "label": label,
            "label_orientation": label_orientation,
            "tone": _FIXTURE_TONES[fixture.kind],
        }
    )


def _merge_bench_fixtures(fixtures: list[PosterSceneFixture]) -> list[PosterSceneFixture]:
    """Coalesce horizontally contiguous benches on the same row."""

    ordered = sorted(
        fixtures,
        key=lambda fixture: (fixture.y, fixture.height, fixture.x, fixture.fixture_id),
    )
    return _merge_contiguous_fixtures(
        fixtures=ordered,
        can_merge=_can_merge_benches,
        merge_axis="x",
    )


def _merge_whiteboard_fixtures(fixtures: list[PosterSceneFixture]) -> list[PosterSceneFixture]:
    """Coalesce contiguous whiteboards that stay on one wall side."""

    ordered = sorted(
        fixtures,
        key=lambda fixture: (
            fixture.wall_side.value if fixture.wall_side is not None else "",
            fixture.x,
            fixture.y,
            fixture.fixture_id,
        ),
    )
    return _merge_contiguous_fixtures(
        fixtures=ordered,
        can_merge=_can_merge_whiteboards,
        merge_axis="wall",
    )


def _merge_contiguous_fixtures(
    *,
    fixtures: list[PosterSceneFixture],
    can_merge,
    merge_axis: str,
) -> list[PosterSceneFixture]:
    """Merge already sorted fixtures while preserving stable source ordering."""

    if not fixtures:
        return []

    merged: list[PosterSceneFixture] = []
    current = fixtures[0]
    for candidate in fixtures[1:]:
        if can_merge(current, candidate):
            current = _merge_fixture_pair(
                current=current,
                candidate=candidate,
                merge_axis=merge_axis,
            )
            continue
        merged.append(current)
        current = candidate
    merged.append(current)
    return merged


def _merge_fixture_pair(
    *,
    current: PosterSceneFixture,
    candidate: PosterSceneFixture,
    merge_axis: str,
) -> PosterSceneFixture:
    """Produce one merged fixture whose label centers on the full merged span."""

    source_ids = (*current.source_fixture_ids, *candidate.source_fixture_ids)
    fixture_id = "__".join(source_ids)
    if merge_axis == "x":
        merged_x = min(current.x, candidate.x)
        merged_width = max(current.x + current.width, candidate.x + candidate.width) - merged_x
        return current.model_copy(
            update={
                "fixture_id": fixture_id,
                "source_fixture_ids": source_ids,
                "x": merged_x,
                "width": merged_width,
            }
        )

    if current.wall_side in {PosterSceneWallSide.TOP, PosterSceneWallSide.BOTTOM}:
        merged_x = min(current.x, candidate.x)
        merged_width = max(current.x + current.width, candidate.x + candidate.width) - merged_x
        return current.model_copy(
            update={
                "fixture_id": fixture_id,
                "source_fixture_ids": source_ids,
                "x": merged_x,
                "width": merged_width,
            }
        )

    merged_y = min(current.y, candidate.y)
    merged_height = max(current.y + current.height, candidate.y + candidate.height) - merged_y
    return current.model_copy(
        update={
            "fixture_id": fixture_id,
            "source_fixture_ids": source_ids,
            "y": merged_y,
            "height": merged_height,
        }
    )


def _can_merge_benches(current: PosterSceneFixture, candidate: PosterSceneFixture) -> bool:
    """Return whether two benches meet the locked presentation invariants."""

    return (
        current.kind is PosterSceneFixtureKind.BENCH
        and candidate.kind is PosterSceneFixtureKind.BENCH
        and current.y == candidate.y
        and current.height == candidate.height
        and current.x + current.width == candidate.x
    )


def _can_merge_whiteboards(current: PosterSceneFixture, candidate: PosterSceneFixture) -> bool:
    """Return whether two whiteboards can present as one wall span."""

    if (
        current.kind is not PosterSceneFixtureKind.WHITEBOARD
        or candidate.kind is not PosterSceneFixtureKind.WHITEBOARD
        or current.wall_side is None
        or current.wall_side != candidate.wall_side
        or current.label_orientation != candidate.label_orientation
    ):
        return False

    if current.wall_side in {PosterSceneWallSide.TOP, PosterSceneWallSide.BOTTOM}:
        return (
            current.y == candidate.y
            and current.height == candidate.height
            and current.x + current.width == candidate.x
        )

    return (
        current.x == candidate.x
        and current.width == candidate.width
        and current.y + current.height == candidate.y
    )
