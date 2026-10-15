"""Fritext rubric criteria and their whole-point value contract (Q12)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NativeExamCriterion(BaseModel):
    """One Fritext rubric criterion: its text and its whole points (Q12)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(min_length=1)
    points: int = Field(ge=1)

    @field_validator("points", mode="before")
    @classmethod
    def _whole_points_not_bool(cls, points: object) -> object:
        if isinstance(points, bool):
            raise ValueError("criterion points must be a whole number")
        return points

    @field_validator("text")
    @classmethod
    def _non_empty_text(cls, text: str) -> str:
        if not text.strip():
            raise ValueError("criterion text must be non-empty")
        return text
