"""Application export models for Klassrumskartan seating artifacts.

Purpose:
    Define renderer-independent export contracts for seating artifacts so the
    application layer can prepare deterministic poster-scene data without
    coupling the planner domain to HTML/CSS or PDF delivery details.

Relationships:
    - Populated by `translator.py` in the same package.
    - Returned by the seating export handler for web serialization.
    - Designed to become the canonical input to the later export-specific
      HTML/CSS renderer owned by PR-0119.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SeatingExportKind(StrEnum):
    """Enumerate the teacher-facing seating export kinds."""

    PDF = "pdf"


class SeatingExportLayoutId(StrEnum):
    """Enumerate stable seating export layout identifiers."""

    PRETTY_BRUTALIST_POSTER = "pretty_brutalist_poster"


class PosterSceneWallSide(StrEnum):
    """Enumerate logical wall sides for wall-bound room markers."""

    TOP = "top"
    RIGHT = "right"
    BOTTOM = "bottom"
    LEFT = "left"


class PosterSceneFixtureKind(StrEnum):
    """Enumerate fixture kinds surfaced to the poster renderer."""

    WHITEBOARD = "whiteboard"
    TEACHER_DESK = "teacher_desk"
    DOOR = "door"
    WINDOW = "window"
    BENCH = "bench"
    TABLE = "table"


class PosterSceneFixtureVariant(StrEnum):
    """Describe optional visual variants inside one poster fixture kind."""

    ROUND = "round"
    SQUARE = "square"


class PosterSceneRoom(BaseModel):
    """Describe the logical room grid used for poster composition."""

    model_config = ConfigDict(frozen=True)

    grid_cols: int = Field(ge=1)
    grid_rows: int = Field(ge=1)


class PosterSceneSeat(BaseModel):
    """Describe one logical seat placement on the poster scene."""

    model_config = ConfigDict(frozen=True)

    seat_id: str
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    zone: str | None = None
    student_id: str | None = None
    label: str | None = None


class PosterSceneFixture(BaseModel):
    """Describe one logical room marker on the poster scene."""

    model_config = ConfigDict(frozen=True)

    fixture_id: str
    kind: PosterSceneFixtureKind
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    wall_side: PosterSceneWallSide | None = None
    label: str | None = None
    variant: PosterSceneFixtureVariant | None = None


class SeatingPosterScene(BaseModel):
    """Describe the standalone classroom poster scene for one seating draft."""

    model_config = ConfigDict(frozen=True)

    room: PosterSceneRoom
    seats: list[PosterSceneSeat]
    fixtures: list[PosterSceneFixture]


class PreparedSeatingExportContract(BaseModel):
    """Describe the public export contract prepared for one seating draft."""

    model_config = ConfigDict(frozen=True)

    seating_draft_id: UUID
    roster_id: UUID
    roster_name: str
    template_id: UUID
    template_name: str
    export_kind: SeatingExportKind
    layout_id: SeatingExportLayoutId
    poster_scene: SeatingPosterScene
