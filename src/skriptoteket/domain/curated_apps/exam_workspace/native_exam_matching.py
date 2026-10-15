"""Matching-kind answer-key invariants for native exam items."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    validate_text_only_body,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    MATCH_LEFT_ID_PATTERN,
    MATCH_RIGHT_ID_PATTERN,
)


class NativeMatchLeft(BaseModel):
    """One entry of the list the student matches from, with its source formatting."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    left_id: str = Field(pattern=MATCH_LEFT_ID_PATTERN)
    body: tuple[NativeParagraph, ...] = Field(min_length=1)

    @field_validator("body")
    @classmethod
    def _text_only_body(cls, body: tuple[NativeParagraph, ...]) -> tuple[NativeParagraph, ...]:
        validate_text_only_body(body, surface="match entry")
        return body


class NativeMatchRight(BaseModel):
    """One entry of the list the student matches to, with its source formatting."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    right_id: str = Field(pattern=MATCH_RIGHT_ID_PATTERN)
    body: tuple[NativeParagraph, ...] = Field(min_length=1)

    @field_validator("body")
    @classmethod
    def _text_only_body(cls, body: tuple[NativeParagraph, ...]) -> tuple[NativeParagraph, ...]:
        validate_text_only_body(body, surface="match entry")
        return body


class NativeMatchPair(BaseModel):
    """One correct directed pair: a left entry and the right entry it matches."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    left_id: str = Field(pattern=MATCH_LEFT_ID_PATTERN)
    right_id: str = Field(pattern=MATCH_RIGHT_ID_PATTERN)


def validate_matching_pairs(
    pairs: tuple[NativeMatchPair, ...],
    left: tuple[NativeMatchLeft, ...],
    right: tuple[NativeMatchRight, ...],
    correct_choice_ids: tuple[str, ...],
) -> None:
    """Every row is covered; repeated row and column participation is allowed."""
    if correct_choice_ids:
        raise ValueError("matching items key pairs, not choices")
    left_ids = {entry.left_id for entry in left}
    right_ids = {entry.right_id for entry in right}
    paired_left = [pair.left_id for pair in pairs]
    paired_right = [pair.right_id for pair in pairs]
    if set(paired_left) - left_ids or set(paired_right) - right_ids:
        raise ValueError("match pairs must refer to declared entries")
    if set(paired_left) != left_ids:
        raise ValueError("a keyed matching item pairs every left entry at least once")
    cells = {(pair.left_id, pair.right_id) for pair in pairs}
    if len(cells) != len(pairs):
        raise ValueError("a keyed matching item pairs a left and right entry at most once")
