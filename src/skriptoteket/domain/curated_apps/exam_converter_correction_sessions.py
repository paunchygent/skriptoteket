"""Exam Converter correction-session aggregate.

Purpose:
  Own source-bound teacher correction intent semantics for authenticated Exam
  Converter workflows while Sir Convert remains a stateless replay applicator.

Relationships:
  - Governed by ADR-0087 and ST-21-04.
  - Persisted by the correction-session repository.
  - Replayed later through the HuleEdu/Sir Convert unified correction edge.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from typing import Final
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error


class ExamConverterCorrectionIntentKind(StrEnum):
    """Supported durable Exam Converter correction intent kinds."""

    CANDIDATE_SUPPRESSION = "candidate_suppression"
    ITEM_TEXT_PATCH = "item_text_patch"
    POINT_CORRECTION = "point_correction"
    MANUAL_CHOICE_ANSWER_KEY = "manual_choice_answer_key"
    MANUAL_GAP_OPEN_CLOZE_ANSWER_KEY = "manual_gap_open_cloze_answer_key"


KIND_REPLAY_ORDER: Final[dict[ExamConverterCorrectionIntentKind, int]] = {
    ExamConverterCorrectionIntentKind.CANDIDATE_SUPPRESSION: 0,
    ExamConverterCorrectionIntentKind.ITEM_TEXT_PATCH: 1,
    ExamConverterCorrectionIntentKind.POINT_CORRECTION: 2,
    ExamConverterCorrectionIntentKind.MANUAL_CHOICE_ANSWER_KEY: 3,
    ExamConverterCorrectionIntentKind.MANUAL_GAP_OPEN_CLOZE_ANSWER_KEY: 4,
}


class ExamConverterCorrectionSourceBinding(BaseModel):
    """Producer-issued source binding that every durable correction intent carries."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_authoring_schema_version: str = Field(min_length=1)
    source_bundle_id: str | None = None
    source_file_sha256: str | None = None
    source_state_sha256: str = Field(min_length=1)
    source_state_signature: str = Field(min_length=1)

    @field_validator(
        "source_authoring_schema_version",
        "source_state_sha256",
        "source_state_signature",
    )
    @classmethod
    def _strip_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("source binding fields must be non-empty")
        return normalized

    @field_validator("source_bundle_id", "source_file_sha256")
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("optional source binding fields must be null or non-empty")
        return normalized


class ExamConverterCorrectionTarget(BaseModel):
    """Kind-specific item-local target identity for one correction intent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    interaction_id: str | None = None
    text_field: str | None = None
    text_field_target_id: str | None = None
    candidate_lineage_id: str | None = None
    candidate_payload_digest: str | None = None

    @field_validator(
        "interaction_id",
        "text_field",
        "text_field_target_id",
        "candidate_lineage_id",
        "candidate_payload_digest",
    )
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("target fields must be null or non-empty")
        return normalized


class SourceBoundCorrectionIntent(BaseModel):
    """One active or persisted teacher correction intent bound to producer source state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    intent_id: UUID
    entry_id: str = Field(min_length=1)
    source_binding: ExamConverterCorrectionSourceBinding
    item_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    item_type: str = Field(min_length=1)
    source_item_fingerprint: str = Field(min_length=1)
    kind: ExamConverterCorrectionIntentKind
    target: ExamConverterCorrectionTarget
    payload: dict[str, JsonValue]
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("entry_id", "item_id", "item_type", "source_item_fingerprint")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("correction intent fields must be non-empty")
        return normalized

    @property
    def target_key(self) -> str:
        """Return the aggregate-unique active target key for this intent."""

        item_scope = (
            f"{self.item_id}:{self.sequence}:{self.item_type}:{self.source_item_fingerprint}"
        )
        if self.kind is ExamConverterCorrectionIntentKind.POINT_CORRECTION:
            return f"{self.kind.value}:{item_scope}"
        if self.kind in {
            ExamConverterCorrectionIntentKind.MANUAL_CHOICE_ANSWER_KEY,
            ExamConverterCorrectionIntentKind.MANUAL_GAP_OPEN_CLOZE_ANSWER_KEY,
        }:
            return f"{self.kind.value}:{item_scope}:{_require_target_field(self, 'interaction_id')}"
        if self.kind is ExamConverterCorrectionIntentKind.ITEM_TEXT_PATCH:
            text_field = _require_target_field(self, "text_field")
            target_id = self.target.text_field_target_id or "-"
            return f"{self.kind.value}:{item_scope}:{text_field}:{target_id}"
        lineage = _require_target_field(self, "candidate_lineage_id")
        digest = _require_target_field(self, "candidate_payload_digest")
        return f"{self.kind.value}:{item_scope}:{lineage}:{digest}"

    @property
    def replay_order_key(self) -> tuple[int, str, int, str, str]:
        """Return deterministic replay ordering metadata for active intents."""

        return (
            self.sequence,
            self.item_id,
            KIND_REPLAY_ORDER[self.kind],
            self.target_key,
            self.entry_id,
        )


class ExamConverterCorrectionSession(BaseModel):
    """Current-set aggregate for one teacher-owned Conversion Hub correction session."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    owner_user_id: UUID
    conversion_hub_job_id: UUID
    source_binding: ExamConverterCorrectionSourceBinding
    session_version: int = Field(ge=0)
    active_intents: tuple[SourceBoundCorrectionIntent, ...] = ()
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def replace_intents(
        self,
        *,
        intents: tuple[SourceBoundCorrectionIntent, ...],
        expected_session_version: int,
    ) -> "ExamConverterCorrectionSession":
        """Replace or supersede active intents and increment the session version.

        Args:
            intents: Source-bound intents submitted as one logical write.
            expected_session_version: Optimistic concurrency token supplied by the caller.

        Returns:
            Updated current-set aggregate.

        Raises:
            DomainError: On stale version or invalid active-set semantics.
        """

        self._assert_expected_version(expected_session_version=expected_session_version)
        _assert_batch_unique(intents=intents)
        self._assert_intents_bound_to_session(intents=intents)

        active = {intent.target_key: intent for intent in self.active_intents}
        for intent in intents:
            active[intent.target_key] = intent

        return self._next_version(active_intents=tuple(active.values()))

    def replace_intent(
        self,
        *,
        intent: SourceBoundCorrectionIntent,
        expected_session_version: int,
    ) -> "ExamConverterCorrectionSession":
        """Replace or supersede one active correction intent."""

        return self.replace_intents(
            intents=(intent,),
            expected_session_version=expected_session_version,
        )

    def revert_target(
        self,
        *,
        target_key: str,
        expected_session_version: int,
    ) -> "ExamConverterCorrectionSession":
        """Remove an active correction target from the current set."""

        self._assert_expected_version(expected_session_version=expected_session_version)
        if not target_key.strip():
            raise validation_error("target_key is required")
        active = {intent.target_key: intent for intent in self.active_intents}
        if target_key not in active:
            raise DomainError(
                code=ErrorCode.NOT_FOUND,
                message="Correction intent target not found",
                details={"session_id": str(self.id), "target_key": target_key},
            )
        active.pop(target_key)
        return self._next_version(active_intents=tuple(active.values()))

    def active_replay_intents(self) -> tuple[SourceBoundCorrectionIntent, ...]:
        """Return active intents in ADR-0087 deterministic replay order."""

        return tuple(sorted(self.active_intents, key=lambda intent: intent.replay_order_key))

    def _assert_expected_version(self, *, expected_session_version: int) -> None:
        if expected_session_version < 0:
            raise validation_error(
                "expected_session_version must be >= 0",
                details={"expected_session_version": expected_session_version},
            )
        if expected_session_version != self.session_version:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="Exam Converter correction session version conflict",
                details={
                    "session_id": str(self.id),
                    "expected_session_version": expected_session_version,
                    "current_session_version": self.session_version,
                },
            )

    def _assert_intents_bound_to_session(
        self,
        *,
        intents: tuple[SourceBoundCorrectionIntent, ...],
    ) -> None:
        for intent in intents:
            if intent.source_binding != self.source_binding:
                raise validation_error(
                    "Correction intent source binding does not match session.",
                    details={
                        "session_id": str(self.id),
                        "entry_id": intent.entry_id,
                        "source_state_sha256": intent.source_binding.source_state_sha256,
                    },
                )

    def _next_version(
        self,
        *,
        active_intents: tuple[SourceBoundCorrectionIntent, ...],
    ) -> "ExamConverterCorrectionSession":
        _assert_active_set_compatible(intents=active_intents)
        return self.model_copy(
            update={
                "session_version": self.session_version + 1,
                "active_intents": tuple(
                    sorted(active_intents, key=lambda intent: intent.replay_order_key)
                ),
            }
        )


def correction_kind_from_value(value: str) -> ExamConverterCorrectionIntentKind:
    """Parse a correction kind while keeping matching blocked."""

    try:
        return ExamConverterCorrectionIntentKind(value)
    except ValueError as exc:
        raise validation_error(
            "Unsupported Exam Converter correction kind.",
            details={
                "kind": value,
                "supported_kinds": [kind.value for kind in ExamConverterCorrectionIntentKind],
            },
        ) from exc


def _require_target_field(intent: SourceBoundCorrectionIntent, field_name: str) -> str:
    value = getattr(intent.target, field_name)
    if not isinstance(value, str):
        raise validation_error(
            "Correction target is missing required kind-specific identity.",
            details={"entry_id": intent.entry_id, "kind": intent.kind.value, "field": field_name},
        )
    return value


def _assert_batch_unique(*, intents: Sequence[SourceBoundCorrectionIntent]) -> None:
    target_keys: set[str] = set()
    for intent in intents:
        _assert_no_duplicate_target(intent=intent, target_keys=target_keys)


def _assert_active_set_compatible(*, intents: Sequence[SourceBoundCorrectionIntent]) -> None:
    _assert_batch_unique(intents=intents)


def _assert_no_duplicate_target(
    *,
    intent: SourceBoundCorrectionIntent,
    target_keys: set[str],
) -> None:
    target_key = intent.target_key
    if target_key in target_keys:
        raise validation_error(
            "Duplicate active correction target in submitted batch.",
            details={"target_key": target_key, "entry_id": intent.entry_id},
        )
    target_keys.add(target_key)
