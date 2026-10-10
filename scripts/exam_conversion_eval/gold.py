"""Source-authored gold schema for TASK-SKRIPT-39-05-02 G1-G3."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

GoldKind = Literal[
    "free_text", "single_choice", "multiple_response", "gap_fill", "matching", "review"
]


def _nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("text must be non-empty")
    return value


class GoldGap(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    accepted_values: tuple[str, ...]

    @field_validator("accepted_values")
    @classmethod
    def _answers(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            _nonblank(value)
        return values


class GoldPair(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    left: str
    right: str

    @field_validator("left", "right")
    @classmethod
    def _text(cls, value: str) -> str:
        return _nonblank(value)


class GoldItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_label: str
    kind: GoldKind
    points: int | float | None = None
    prompt: str
    choices: tuple[str, ...] = ()
    correct_choices: tuple[str, ...] = ()
    gaps: tuple[GoldGap, ...] = ()
    pairs: tuple[GoldPair, ...] = ()
    teacher_questions: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @field_validator("source_label", "prompt")
    @classmethod
    def _text(cls, value: str) -> str:
        return _nonblank(value)

    @field_validator("choices", "correct_choices", "teacher_questions", "notes")
    @classmethod
    def _texts(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            _nonblank(value)
        return values

    @field_validator("points", mode="before")
    @classmethod
    def _points(cls, value: object) -> object:
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError("points must be a positive finite number or None")
        return value

    @model_validator(mode="after")
    def _kind_fields(self) -> GoldItem:
        choices = [" ".join(value.split()) for value in self.choices]
        if len(set(choices)) != len(choices):
            raise ValueError("choices must be unique after whitespace normalisation")
        if self.prompt.count("[___]") != len(self.gaps):
            raise ValueError("prompt gap markers must equal gaps count")
        if self.kind in ("single_choice", "multiple_response"):
            if len(self.choices) < 2 or self.gaps or self.pairs:
                raise ValueError("choice items need at least two choices and no gaps or pairs")
            if set(self.correct_choices) - set(self.choices):
                raise ValueError("correct_choices must refer to choice texts")
            if len(set(self.correct_choices)) != len(self.correct_choices):
                raise ValueError("correct_choices must be unique")
            if self.kind == "single_choice":
                if len(self.correct_choices) > 1 or (
                    not self.correct_choices and not self.teacher_questions
                ):
                    raise ValueError(
                        "single_choice needs exactly one correct choice unless unresolved"
                    )
            elif not self.correct_choices and not self.teacher_questions:
                raise ValueError("multiple_response needs correct choices unless unresolved")
        elif self.kind == "gap_fill":
            if not self.gaps or self.choices or self.correct_choices or self.pairs:
                raise ValueError("gap_fill needs gaps and no choices or pairs")
            if any(not gap.accepted_values for gap in self.gaps) and not self.teacher_questions:
                raise ValueError("empty accepted_values need teacher_questions")
        elif self.kind == "matching":
            if not self.pairs or self.choices or self.correct_choices or self.gaps:
                raise ValueError("matching needs pairs and no choices or gaps")
        elif self.choices or self.correct_choices or self.gaps or self.pairs:
            raise ValueError("free_text and review carry no keyed data")
        return self


class GoldExam(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["exam_conversion_gold_v1"] = "exam_conversion_gold_v1"
    source_filename: str
    source_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    title: str
    confirmed: bool = False
    confirmation_note: str | None = None
    items: tuple[GoldItem, ...] = Field(min_length=1)
    notes: tuple[str, ...] = ()

    @field_validator("source_filename")
    @classmethod
    def _filename(cls, value: str) -> str:
        if "/" in value or "\\" in value or not value.endswith(".docx") or value == ".docx":
            raise ValueError("source_filename must be a basename ending in .docx")
        return _nonblank(value)

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _nonblank(value)

    @model_validator(mode="after")
    def _exam_fields(self) -> GoldExam:
        labels = [item.source_label for item in self.items]
        if len(set(labels)) != len(labels):
            raise ValueError("source_label must be unique per exam")
        if self.confirmed and (
            not self.confirmation_note
            or not self.confirmation_note.strip()
            or any(item.teacher_questions for item in self.items)
        ):
            raise ValueError("confirmed gold needs confirmation_note and no teacher_questions")
        return self
