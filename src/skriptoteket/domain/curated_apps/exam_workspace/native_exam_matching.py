"""Matching-kind answer-key invariants for native exam items."""

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    MATCH_LEFT_ID_PATTERN,
    MATCH_RIGHT_ID_PATTERN,
)


class NativeMatchLeft(BaseModel):
    """One entry of the list the student matches from."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    left_id: str = Field(pattern=MATCH_LEFT_ID_PATTERN)
    text: str = Field(min_length=1)


class NativeMatchRight(BaseModel):
    """One entry of the list the student matches to."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    right_id: str = Field(pattern=MATCH_RIGHT_ID_PATTERN)
    text: str = Field(min_length=1)


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
    """Every left entry is paired once; unpaired right entries are distractors."""
    if correct_choice_ids:
        raise ValueError("matching items key pairs, not choices")
    left_ids = {entry.left_id for entry in left}
    right_ids = {entry.right_id for entry in right}
    paired_left = [pair.left_id for pair in pairs]
    paired_right = [pair.right_id for pair in pairs]
    if set(paired_left) - left_ids or set(paired_right) - right_ids:
        raise ValueError("match pairs must refer to declared entries")
    if sorted(paired_left) != sorted(left_ids):
        raise ValueError("a keyed matching item pairs every left entry exactly once")
    if len(set(paired_right)) != len(paired_right):
        raise ValueError("a keyed matching item pairs each right entry at most once")
