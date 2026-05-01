"""Spatial seating-scene HTML helpers for Klassrumskartan share artifacts.

Purpose:
    Render static, CSS-only classroom-map markup from the canonical seating
    `poster_scene` export contract used by PDF and share-link artifacts.

Relationships:
    - Used by `share_renderer.py` for immutable seating share pages.
    - Consumes renderer-independent models from the application export layer.
    - Does not emit JavaScript, app API calls, or browser-supplied HTML/CSS.
"""

from __future__ import annotations

from html import escape

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    PosterSceneFixture,
    PosterSceneFixtureKind,
    PosterSceneFixturePlacement,
    PosterSceneFixtureVariant,
    PosterSceneLabelOrientation,
    PosterSceneSeat,
    PosterSceneWallSide,
    PreparedSeatingExportContract,
)

ROOM_GRID_UNIT_PX = 96
ROOM_WALL_BAND_PX = 28
ROOM_WALL_THICKNESS_PX = 18

SEATING_SHARE_CSS = """
.share-subtitle {
  color: #1c2e4a;
  font-size: 1rem;
  font-weight: 700;
  margin: -12px 0 6px;
}
.share-description {
  color: #4f5f75;
  font-size: 0.92rem;
  line-height: 1.45;
  margin: 0 0 22px;
}
.room-frame {
  background: #fff;
  border: 1px solid #1c2e4a;
  box-shadow: 4px 4px 0 #1c2e4a;
}
.room-viewport {
  display: flex;
  justify-content: center;
  overflow-x: auto;
  padding: clamp(0.75rem, 2vw, 1.5rem);
}
.room-surface {
  position: relative;
  inline-size: clamp(min(58rem, var(--room-surface-width)), 100%, var(--room-surface-width));
  aspect-ratio: var(--room-surface-aspect);
  container-type: inline-size;
  flex: 0 0 auto;
  background: #fafaf6;
  border: 1px solid rgba(28, 46, 74, 0.42);
}
.room-floor {
  position: absolute;
  background-color: #fff;
  border: 1px solid #1c2e4a;
}
.room-fixture,
.room-seat {
  position: absolute;
  z-index: 2;
}
.room-fixture {
  align-items: center;
  display: flex;
  justify-content: center;
  text-align: center;
}
.room-fixture__label {
  color: rgba(28, 46, 74, 0.68);
  font-size: clamp(0.42rem, 1.05vw, 0.72rem);
  font-weight: 800;
  letter-spacing: 0.08em;
  line-height: 1;
  overflow: hidden;
  text-transform: uppercase;
  white-space: nowrap;
}
.room-fixture--wall {
  background: #fff;
  border: 1px solid #1c2e4a;
  border-radius: 2px;
}
.room-fixture--whiteboard::after {
  background: rgba(28, 46, 74, 0.35);
  border-radius: 999px;
  bottom: 1px;
  content: "";
  height: 3px;
  left: 6px;
  position: absolute;
  right: 6px;
}
.room-fixture--teacher-desk,
.room-fixture--strong {
  background: rgba(28, 46, 74, 0.86);
  border: 2px solid #1c2e4a;
  border-radius: 2px;
}
.room-fixture--teacher-desk .room-fixture__label,
.room-fixture--strong .room-fixture__label {
  color: #fff;
}
.room-fixture--bench {
  background: transparent;
  display: block;
  position: absolute;
}
.room-fixture--bench .room-bench-body {
  background: rgba(28, 46, 74, 0.12);
  border: 1px solid rgba(28, 46, 74, 0.25);
  border-radius: 4px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.45);
  bottom: 33%;
  left: 0.375rem;
  position: absolute;
  right: 0.375rem;
  top: 33%;
}
.room-fixture--table {
  background: rgba(28, 46, 74, 0.04);
  border: 1px solid rgba(28, 46, 74, 0.55);
}
.room-fixture--round {
  border-radius: 999px;
}
.room-fixture--label-vertical .room-fixture__label {
  writing-mode: vertical-rl;
}
.room-seat {
  align-items: center;
  display: flex;
  flex-direction: column;
  justify-content: center;
  transform: translateY(-8%);
  z-index: 3;
}
.room-seat__token {
  align-items: center;
  aspect-ratio: 1;
  background: #fff;
  border: 1px solid #1c2e4a;
  border-radius: 999px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  inline-size: 90%;
  padding: 0.1rem;
  text-align: center;
}
.room-seat__name-line {
  color: #1c2e4a;
  display: block;
  font-size: clamp(0.58rem, 1.58cqw, 0.92rem);
  font-weight: 500;
  line-height: 1.02;
  max-inline-size: 94%;
  overflow: hidden;
  overflow-wrap: anywhere;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.room-seat--empty .room-seat__token {
  background: rgba(255, 255, 255, 0.72);
  border-color: rgba(28, 46, 74, 0.35);
  border-style: dashed;
}
.room-seat--empty .room-seat__name-line {
  color: rgba(28, 46, 74, 0.48);
}
@media (max-width: 767px) {
  .share-page {
    padding: 18px 12px 28px;
  }
  .share-title {
    font-size: clamp(1.6rem, 8vw, 2.2rem);
  }
  .room-frame {
    box-shadow: none;
  }
  .room-viewport {
    justify-content: flex-start;
    padding: 0.5rem;
  }
  .room-fixture--wall .room-fixture__label {
    display: none;
  }
  .room-fixture--bench .room-bench-body {
    bottom: 38%;
    top: 38%;
  }
}
@media print {
  .room-frame {
    box-shadow: none;
  }
  .room-viewport {
    overflow: visible;
    padding: 0;
  }
  .room-surface {
    inline-size: 100%;
  }
}
""".strip()


def render_seating_scene_body(*, prepared_export: PreparedSeatingExportContract) -> str:
    """Render the seating share body as one static spatial classroom map."""

    scene = prepared_export.poster_scene
    surface = _build_surface(scene.room.grid_cols, scene.room.grid_rows)
    room_style = (
        f"--room-grid-cols:{scene.room.grid_cols};"
        f"--room-grid-rows:{scene.room.grid_rows};"
        f"--room-surface-width:{surface.width}px;"
        f"--room-surface-aspect:{surface.width} / {surface.height};"
    )
    return "\n".join(
        [
            '<section class="room-frame" aria-label="Delat sittschema">',
            '<div class="room-viewport">',
            f'<div class="room-surface" style="{room_style}">',
            _render_floor(surface=surface),
            *[_render_fixture(fixture, surface=surface) for fixture in scene.fixtures],
            *[_render_seat(seat, surface=surface) for seat in scene.seats],
            "</div>",
            "</div>",
            "</section>",
        ]
    )


class _RoomSurface:
    """Describe the static pixel coordinate system used by CSS percentages."""

    def __init__(self, *, grid_cols: int, grid_rows: int) -> None:
        self.width = (grid_cols * ROOM_GRID_UNIT_PX) + (ROOM_WALL_BAND_PX * 2)
        self.height = (grid_rows * ROOM_GRID_UNIT_PX) + (ROOM_WALL_BAND_PX * 2)
        self.floor_width = grid_cols * ROOM_GRID_UNIT_PX
        self.floor_height = grid_rows * ROOM_GRID_UNIT_PX

    def style_from_frame(self, *, x: int, y: int, width: int, height: int) -> str:
        """Return an absolute frame style in surface-relative percentages."""

        return (
            f"left:{_pct(x, self.width)}%;"
            f"top:{_pct(y, self.height)}%;"
            f"width:{_pct(width, self.width)}%;"
            f"height:{_pct(height, self.height)}%;"
        )


def _build_surface(grid_cols: int, grid_rows: int) -> _RoomSurface:
    """Build the static coordinate system for one exported room."""

    return _RoomSurface(grid_cols=grid_cols, grid_rows=grid_rows)


def _render_floor(*, surface: _RoomSurface) -> str:
    """Render the classroom floor layer inside the wall band."""

    style = surface.style_from_frame(
        x=ROOM_WALL_BAND_PX,
        y=ROOM_WALL_BAND_PX,
        width=surface.floor_width,
        height=surface.floor_height,
    )
    return f'<div class="room-floor" style="{style}"></div>'


def _render_fixture(fixture: PosterSceneFixture, *, surface: _RoomSurface) -> str:
    """Render one room fixture from the normalized poster scene."""

    x, y, width, height = _fixture_frame(fixture, surface=surface)
    style = surface.style_from_frame(x=x, y=y, width=width, height=height)
    label = escape(fixture.label) if fixture.label else ""
    classes = _fixture_classes(fixture)
    body = (
        '<div class="room-bench-body"></div>'
        if fixture.kind is PosterSceneFixtureKind.BENCH
        else ""
    )
    show_label = fixture.kind is not PosterSceneFixtureKind.BENCH and bool(label)
    label_markup = f'<span class="room-fixture__label">{label}</span>' if show_label else ""
    return f'<div class="{" ".join(classes)}" style="{style}">{body}{label_markup}</div>'


def _fixture_frame(
    fixture: PosterSceneFixture,
    *,
    surface: _RoomSurface,
) -> tuple[int, int, int, int]:
    """Convert grid coordinates into the share-page pixel coordinate system."""

    if fixture.placement is PosterSceneFixturePlacement.FLOOR:
        return (
            ROOM_WALL_BAND_PX + (fixture.x * ROOM_GRID_UNIT_PX),
            ROOM_WALL_BAND_PX + (fixture.y * ROOM_GRID_UNIT_PX),
            fixture.width * ROOM_GRID_UNIT_PX,
            fixture.height * ROOM_GRID_UNIT_PX,
        )

    if fixture.wall_side is None:
        raise ValueError(f"Wall fixture is missing wall_side: {fixture.fixture_id}")

    if fixture.wall_side is PosterSceneWallSide.TOP:
        return (
            ROOM_WALL_BAND_PX + (fixture.x * ROOM_GRID_UNIT_PX),
            ROOM_WALL_BAND_PX - ROOM_WALL_THICKNESS_PX,
            fixture.width * ROOM_GRID_UNIT_PX,
            ROOM_WALL_THICKNESS_PX,
        )
    if fixture.wall_side is PosterSceneWallSide.BOTTOM:
        return (
            ROOM_WALL_BAND_PX + (fixture.x * ROOM_GRID_UNIT_PX),
            ROOM_WALL_BAND_PX + surface.floor_height,
            fixture.width * ROOM_GRID_UNIT_PX,
            ROOM_WALL_THICKNESS_PX,
        )
    if fixture.wall_side is PosterSceneWallSide.LEFT:
        return (
            ROOM_WALL_BAND_PX - ROOM_WALL_THICKNESS_PX,
            ROOM_WALL_BAND_PX + (fixture.y * ROOM_GRID_UNIT_PX),
            ROOM_WALL_THICKNESS_PX,
            fixture.height * ROOM_GRID_UNIT_PX,
        )
    return (
        ROOM_WALL_BAND_PX + surface.floor_width,
        ROOM_WALL_BAND_PX + (fixture.y * ROOM_GRID_UNIT_PX),
        ROOM_WALL_THICKNESS_PX,
        fixture.height * ROOM_GRID_UNIT_PX,
    )


def _fixture_classes(fixture: PosterSceneFixture) -> list[str]:
    """Return stable CSS classes for one fixture kind and presentation tone."""

    kind = fixture.kind.value.replace("_", "-")
    classes = [
        "room-fixture",
        f"room-fixture--{kind}",
        f"room-fixture--{fixture.tone.value}",
    ]
    if fixture.placement is PosterSceneFixturePlacement.WALL:
        classes.append("room-fixture--wall")
    if fixture.label_orientation is PosterSceneLabelOrientation.VERTICAL:
        classes.append("room-fixture--label-vertical")
    if fixture.variant is PosterSceneFixtureVariant.ROUND:
        classes.append("room-fixture--round")
    return classes


def _render_seat(
    seat: PosterSceneSeat,
    *,
    surface: _RoomSurface,
) -> str:
    """Render one occupied or empty seat token."""

    classes = ["room-seat"]
    if seat.label is None:
        classes.append("room-seat--empty")
    style = surface.style_from_frame(
        x=ROOM_WALL_BAND_PX + (seat.x * ROOM_GRID_UNIT_PX),
        y=ROOM_WALL_BAND_PX + (seat.y * ROOM_GRID_UNIT_PX),
        width=ROOM_GRID_UNIT_PX,
        height=ROOM_GRID_UNIT_PX,
    )
    if seat.label is None:
        return (
            f'<article class="{" ".join(classes)}" style="{style}" aria-label="Tom plats">'
            '<div class="room-seat__token"></div>'
            "</article>"
        )

    escaped_label = escape(seat.label)
    first_name, second_line = _student_name_lines(seat.label)
    return (
        f'<article class="{" ".join(classes)}" style="{style}" '
        f'aria-label="{escaped_label}" title="{escaped_label}">'
        '<div class="room-seat__token">'
        f'<span class="room-seat__name-line">{escape(first_name)}</span>'
        f'<span class="room-seat__name-line">{escape(second_line)}</span>'
        "</div>"
        "</article>"
    )


def _pct(value: int, whole: int) -> str:
    """Return a stable percentage scalar for inline geometry styles."""

    return f"{(value / whole) * 100:.6f}".rstrip("0").rstrip(".")


def _student_name_lines(value: str) -> tuple[str, str]:
    """Return first-name plus surname-or-initial lines for one seat token."""

    words = [word for word in value.replace("-", " ").split() if word]
    if not words:
        return value, ""

    first_name = words[0]
    if len(words) == 1:
        return first_name, ""

    last_name = words[-1]
    if len(last_name) <= 9:
        return first_name, last_name
    return first_name, f"{last_name[0].upper()}."
