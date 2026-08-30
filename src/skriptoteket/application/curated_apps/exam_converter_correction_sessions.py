"""Exam Converter correction-session application contracts.

Purpose:
  Shape authenticated API request and response models for Skriptoteket-owned
  durable correction intents before replay or frontend rendering consumes them.

Relationships:
  - Wraps the correction-session domain aggregate for web/API handlers.
  - Used by PR-0334 routes and generated OpenAPI frontend types.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skriptoteket.domain.curated_apps.exam_converter_correction_sessions import (
    ExamConverterCorrectionIntentKind,
    ExamConverterCorrectionSession,
    ExamConverterCorrectionSourceBinding,
    ExamConverterCorrectionTarget,
    SourceBoundCorrectionIntent,
    correction_kind_from_value,
)


class ExamConverterCorrectionIntentWrite(BaseModel):
    """Boundary model for one source-bound correction intent write."""

    model_config = ConfigDict(extra="forbid")

    entry_id: str = Field(min_length=1)
    source_binding: ExamConverterCorrectionSourceBinding
    item_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    item_type: str = Field(min_length=1)
    source_item_fingerprint: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    target: ExamConverterCorrectionTarget = Field(default_factory=ExamConverterCorrectionTarget)
    payload: dict[str, JsonValue]

    def to_domain(self, *, intent_id: UUID) -> SourceBoundCorrectionIntent:
        """Convert the request into a domain intent with a server-owned id."""

        return SourceBoundCorrectionIntent(
            intent_id=intent_id,
            entry_id=self.entry_id,
            source_binding=self.source_binding,
            item_id=self.item_id,
            sequence=self.sequence,
            item_type=self.item_type,
            source_item_fingerprint=self.source_item_fingerprint,
            kind=correction_kind_from_value(self.kind),
            target=self.target,
            payload=self.payload,
        )


class ExamConverterCorrectionIntentResponse(BaseModel):
    """Current active correction intent returned to clients."""

    model_config = ConfigDict(extra="forbid")

    intent_id: UUID
    entry_id: str
    source_binding: ExamConverterCorrectionSourceBinding
    item_id: str
    sequence: int
    item_type: str
    source_item_fingerprint: str
    kind: ExamConverterCorrectionIntentKind
    target: ExamConverterCorrectionTarget
    target_key: str
    payload: dict[str, JsonValue]

    @classmethod
    def from_domain(
        cls,
        intent: SourceBoundCorrectionIntent,
    ) -> "ExamConverterCorrectionIntentResponse":
        """Build an API read model from one domain intent."""

        return cls(
            intent_id=intent.intent_id,
            entry_id=intent.entry_id,
            source_binding=intent.source_binding,
            item_id=intent.item_id,
            sequence=intent.sequence,
            item_type=intent.item_type,
            source_item_fingerprint=intent.source_item_fingerprint,
            kind=intent.kind,
            target=intent.target,
            target_key=intent.target_key,
            payload=intent.payload,
        )


class ExamConverterCorrectionSessionResponse(BaseModel):
    """Owner-scoped current correction-session state."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID | None
    owner_user_id: UUID
    conversion_hub_job_id: UUID
    source_binding: ExamConverterCorrectionSourceBinding | None
    session_version: int
    active_intents: list[ExamConverterCorrectionIntentResponse]

    @classmethod
    def empty(
        cls,
        *,
        owner_user_id: UUID,
        conversion_hub_job_id: UUID,
    ) -> "ExamConverterCorrectionSessionResponse":
        """Return a readback shape for a job without a created session yet."""

        return cls(
            session_id=None,
            owner_user_id=owner_user_id,
            conversion_hub_job_id=conversion_hub_job_id,
            source_binding=None,
            session_version=0,
            active_intents=[],
        )

    @classmethod
    def from_domain(
        cls,
        session: ExamConverterCorrectionSession,
    ) -> "ExamConverterCorrectionSessionResponse":
        """Build an API read model from the current aggregate state."""

        return cls(
            session_id=session.id,
            owner_user_id=session.owner_user_id,
            conversion_hub_job_id=session.conversion_hub_job_id,
            source_binding=session.source_binding,
            session_version=session.session_version,
            active_intents=[
                ExamConverterCorrectionIntentResponse.from_domain(intent)
                for intent in session.active_replay_intents()
            ],
        )


class ReplaceExamConverterCorrectionIntentsRequest(BaseModel):
    """Replace active correction targets through one optimistic batch write."""

    model_config = ConfigDict(extra="forbid")

    expected_session_version: int = Field(ge=0)
    intents: list[ExamConverterCorrectionIntentWrite] = Field(min_length=1)


class RevertExamConverterCorrectionIntentRequest(BaseModel):
    """Delete/revert request for one active correction target."""

    model_config = ConfigDict(extra="forbid")

    expected_session_version: int | None = Field(default=None, ge=0)
    target_key: str = Field(min_length=1)
