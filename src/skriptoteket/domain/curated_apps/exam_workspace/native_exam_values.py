"""Answer, response and review value types for native exam items."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from skriptoteket.domain.curated_apps.exam_workspace.answer_spelling import (
    filter_answer_spelling_candidates,
    normalize_answer,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchPair,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    CHOICE_ID_PATTERN,
    GAP_ID_PATTERN,
    SHA256_PATTERN,
    NativeAnswerKeyOrigin,
    NativeItemReviewState,
    NativeParseOrigin,
)


class NativeChoice(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    choice_id: str = Field(pattern=CHOICE_ID_PATTERN)
    text: str = Field(min_length=1)


class NativeGap(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_serialization_defaults_required=True,
    )

    gap_id: str = Field(pattern=GAP_ID_PATTERN)
    accepted_values: tuple[str, ...] = ()
    excluded_automatic_values: tuple[str, ...] = ()
    automatic_values: tuple[str, ...] = ()

    @field_validator("accepted_values")
    @classmethod
    def _non_empty_values(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            if not value.strip():
                raise ValueError("accepted_values entries must be non-empty")
        return values

    @field_validator("automatic_values")
    @classmethod
    def _bounded_automatic_values(
        cls, values: tuple[str, ...], info: ValidationInfo
    ) -> tuple[str, ...]:
        """Keep only bounded spellings of an accepted value; drop the rest at save (D7).

        The saved document is normalized, never rejected: a value outside the A10
        distance, a duplicate of an accepted value, or a fourth spelling of one
        accepted value is dropped, and an accepted value's removal drops the
        automatic values that depended on it in the same save.
        """
        accepted = info.data.get("accepted_values") or ()
        excluded = {
            normalize_answer(value) for value in info.data.get("excluded_automatic_values", ())
        }
        candidates = tuple(value for value in values if normalize_answer(value) not in excluded)
        return filter_answer_spelling_candidates(accepted, candidates)


class NativeAnswerKey(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    origin: NativeAnswerKeyOrigin
    correct_choice_ids: tuple[str, ...] = ()
    match_pairs: tuple[NativeMatchPair, ...] = ()


class NativeGapAcceptedValues(BaseModel):
    """The accepted values one AI suggestion proposes for one gap."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    gap_id: str = Field(pattern=GAP_ID_PATTERN)
    accepted_values: tuple[str, ...] = Field(min_length=1)

    @field_validator("accepted_values")
    @classmethod
    def _non_empty_values(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            if not value.strip():
                raise ValueError("accepted_values entries must be non-empty")
        return values


class NativeAnswerKeySuggestion(BaseModel):
    """One AI answer-key suggestion kept on its question (TASK-SKRIPT-39-04-07).

    Holds the proposed key, a SHA-256 fingerprint of the question's
    answer-relevant content when the suggestion was made, and the provider
    lineage that produced it. It lives apart from the item's answer key so
    it survives the teacher accepting or replacing that key.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    correct_choice_ids: tuple[str, ...] = ()
    match_pairs: tuple[NativeMatchPair, ...] = ()
    gap_accepted_values: tuple[NativeGapAcceptedValues, ...] = ()
    fingerprint: str = Field(pattern=SHA256_PATTERN)
    provider_profile_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    prompt_template_version: str = Field(min_length=1)


class NativeItemReview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    state: NativeItemReviewState
    parse_origin: NativeParseOrigin
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    reasons: tuple[str, ...] = ()
