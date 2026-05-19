"""PostgreSQL repository for Exam Converter correction sessions.

Purpose:
  Map the correction-session aggregate to owner/job-scoped PostgreSQL tables so
  Skriptoteket can persist teacher intent truth without giving Sir Convert
  durable-session responsibility.

Relationships:
  - Implements `ExamConverterCorrectionSessionRepositoryProtocol`.
  - Stores rows with `ExamConverterCorrectionSessionModel` and intent rows.
  - Verifies ownership against `ConversionHubJobModel` before writes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.curated_apps.exam_converter_correction_sessions import (
    ExamConverterCorrectionSession,
    ExamConverterCorrectionSourceBinding,
    ExamConverterCorrectionTarget,
    SourceBoundCorrectionIntent,
    correction_kind_from_value,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.infrastructure.db.models.conversion_hub_job import ConversionHubJobModel
from skriptoteket.infrastructure.db.models.exam_converter_correction_session import (
    ExamConverterCorrectionIntentModel,
    ExamConverterCorrectionSessionModel,
)
from skriptoteket.protocols.exam_converter_correction_sessions import (
    ExamConverterCorrectionSessionRepositoryProtocol,
)


class PostgreSQLExamConverterCorrectionSessionRepository(
    ExamConverterCorrectionSessionRepositoryProtocol
):
    """Persist Exam Converter correction sessions in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_owner_and_job(
        self,
        *,
        owner_user_id: UUID,
        conversion_hub_job_id: UUID,
    ) -> ExamConverterCorrectionSession | None:
        model = await self._get_session_model(
            owner_user_id=owner_user_id,
            conversion_hub_job_id=conversion_hub_job_id,
        )
        if model is None:
            return None
        return await self._to_session(model)

    async def save(
        self,
        *,
        session: ExamConverterCorrectionSession,
        expected_session_version: int,
    ) -> ExamConverterCorrectionSession:
        await self._assert_owned_job(
            owner_user_id=session.owner_user_id,
            conversion_hub_job_id=session.conversion_hub_job_id,
        )
        if expected_session_version < 0:
            raise validation_error(
                "expected_session_version must be >= 0",
                details={"expected_session_version": expected_session_version},
            )
        if session.session_version != expected_session_version + 1:
            raise validation_error(
                "Saved correction session must advance exactly one version.",
                details={
                    "session_id": str(session.id),
                    "expected_session_version": expected_session_version,
                    "saved_session_version": session.session_version,
                },
            )
        model = await self._get_session_model(
            owner_user_id=session.owner_user_id,
            conversion_hub_job_id=session.conversion_hub_job_id,
        )
        if model is None:
            self._assert_new_session_version(expected_session_version=expected_session_version)
            model = self._to_session_model(session)
            self._session.add(model)
        else:
            self._assert_current_version(
                model=model,
                expected_session_version=expected_session_version,
            )
            self._assert_same_source_binding(model=model, session=session)
            self._update_session_model(model=model, session=session)

        await self._session.flush()
        await self._replace_active_intents(
            session_id=model.id,
            intents=session.active_replay_intents(),
        )
        await self._session.flush()
        saved = await self.get_by_owner_and_job(
            owner_user_id=session.owner_user_id,
            conversion_hub_job_id=session.conversion_hub_job_id,
        )
        if saved is None:
            raise not_found("ExamConverterCorrectionSession", str(session.id))
        return saved

    async def _assert_owned_job(
        self,
        *,
        owner_user_id: UUID,
        conversion_hub_job_id: UUID,
    ) -> None:
        stmt = (
            select(ConversionHubJobModel.id)
            .where(ConversionHubJobModel.id == conversion_hub_job_id)
            .where(ConversionHubJobModel.owner_user_id == owner_user_id)
        )
        result = await self._session.execute(stmt)
        if result.scalar_one_or_none() is None:
            raise not_found("ConversionHubJob", str(conversion_hub_job_id))

    async def _get_session_model(
        self,
        *,
        owner_user_id: UUID,
        conversion_hub_job_id: UUID,
    ) -> ExamConverterCorrectionSessionModel | None:
        stmt = (
            select(ExamConverterCorrectionSessionModel)
            .where(ExamConverterCorrectionSessionModel.owner_user_id == owner_user_id)
            .where(
                ExamConverterCorrectionSessionModel.conversion_hub_job_id == conversion_hub_job_id
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _to_session(
        self,
        model: ExamConverterCorrectionSessionModel,
    ) -> ExamConverterCorrectionSession:
        active_intents = await self._load_active_intents(session_id=model.id)
        return ExamConverterCorrectionSession(
            id=model.id,
            owner_user_id=model.owner_user_id,
            conversion_hub_job_id=model.conversion_hub_job_id,
            source_binding=ExamConverterCorrectionSourceBinding(
                source_authoring_schema_version=model.source_authoring_schema_version,
                source_bundle_id=model.source_bundle_id,
                source_file_sha256=model.source_file_sha256,
                source_state_sha256=model.source_state_sha256,
                source_state_signature=model.source_state_signature,
            ),
            session_version=model.session_version,
            active_intents=active_intents,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def _load_active_intents(
        self,
        *,
        session_id: UUID,
    ) -> tuple[SourceBoundCorrectionIntent, ...]:
        stmt = (
            select(ExamConverterCorrectionIntentModel)
            .where(ExamConverterCorrectionIntentModel.session_id == session_id)
            .where(ExamConverterCorrectionIntentModel.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        intents = tuple(self._to_intent(model) for model in result.scalars().all())
        return tuple(sorted(intents, key=lambda intent: intent.replay_order_key))

    def _to_intent(self, model: ExamConverterCorrectionIntentModel) -> SourceBoundCorrectionIntent:
        return SourceBoundCorrectionIntent(
            intent_id=model.id,
            entry_id=model.entry_id,
            source_binding=ExamConverterCorrectionSourceBinding.model_validate(
                model.source_binding
            ),
            item_id=model.item_id,
            sequence=model.sequence,
            item_type=model.item_type,
            source_item_fingerprint=model.source_item_fingerprint,
            kind=correction_kind_from_value(model.correction_kind),
            target=ExamConverterCorrectionTarget.model_validate(model.target),
            payload=model.payload,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_session_model(
        self,
        session: ExamConverterCorrectionSession,
    ) -> ExamConverterCorrectionSessionModel:
        binding = session.source_binding
        model = ExamConverterCorrectionSessionModel(
            id=session.id,
            owner_user_id=session.owner_user_id,
            conversion_hub_job_id=session.conversion_hub_job_id,
            source_authoring_schema_version=binding.source_authoring_schema_version,
            source_bundle_id=binding.source_bundle_id,
            source_file_sha256=binding.source_file_sha256,
            source_state_sha256=binding.source_state_sha256,
            source_state_signature=binding.source_state_signature,
            session_version=session.session_version,
        )
        if session.created_at is not None:
            model.created_at = session.created_at
        if session.updated_at is not None:
            model.updated_at = session.updated_at
        return model

    def _update_session_model(
        self,
        *,
        model: ExamConverterCorrectionSessionModel,
        session: ExamConverterCorrectionSession,
    ) -> None:
        model.session_version = session.session_version

    async def _replace_active_intents(
        self,
        *,
        session_id: UUID,
        intents: tuple[SourceBoundCorrectionIntent, ...],
    ) -> None:
        desired_by_target = {intent.target_key: intent for intent in intents}
        existing_by_target = await self._load_active_intent_models_by_target(session_id=session_id)
        now = datetime.now(timezone.utc)
        for target_key, model in existing_by_target.items():
            desired = desired_by_target.get(target_key)
            if desired is None or desired.intent_id != model.id:
                model.is_active = False
                model.deactivated_at = now
                model.updated_at = now

        for intent in intents:
            existing = existing_by_target.get(intent.target_key)
            if existing is not None and existing.id == intent.intent_id:
                continue
            self._session.add(self._to_intent_model(session_id=session_id, intent=intent))

    async def _load_active_intent_models_by_target(
        self,
        *,
        session_id: UUID,
    ) -> dict[str, ExamConverterCorrectionIntentModel]:
        stmt = (
            select(ExamConverterCorrectionIntentModel)
            .where(ExamConverterCorrectionIntentModel.session_id == session_id)
            .where(ExamConverterCorrectionIntentModel.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        return {model.target_key: model for model in result.scalars().all()}

    def _to_intent_model(
        self,
        *,
        session_id: UUID,
        intent: SourceBoundCorrectionIntent,
    ) -> ExamConverterCorrectionIntentModel:
        model = ExamConverterCorrectionIntentModel(
            id=intent.intent_id,
            session_id=session_id,
            entry_id=intent.entry_id,
            correction_kind=intent.kind.value,
            target_key=intent.target_key,
            item_id=intent.item_id,
            sequence=intent.sequence,
            item_type=intent.item_type,
            source_item_fingerprint=intent.source_item_fingerprint,
            source_binding=intent.source_binding.model_dump(mode="json"),
            target=intent.target.model_dump(mode="json", exclude_none=True),
            payload=_payload_with_kind(intent),
        )
        if intent.created_at is not None:
            model.created_at = intent.created_at
        if intent.updated_at is not None:
            model.updated_at = intent.updated_at
        return model

    def _assert_new_session_version(self, *, expected_session_version: int) -> None:
        if expected_session_version != 0:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="Exam Converter correction session version conflict",
                details={
                    "expected_session_version": expected_session_version,
                    "current_session_version": 0,
                },
            )

    def _assert_current_version(
        self,
        *,
        model: ExamConverterCorrectionSessionModel,
        expected_session_version: int,
    ) -> None:
        if model.session_version != expected_session_version:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="Exam Converter correction session version conflict",
                details={
                    "session_id": str(model.id),
                    "expected_session_version": expected_session_version,
                    "current_session_version": model.session_version,
                },
            )

    def _assert_same_source_binding(
        self,
        *,
        model: ExamConverterCorrectionSessionModel,
        session: ExamConverterCorrectionSession,
    ) -> None:
        current = ExamConverterCorrectionSourceBinding(
            source_authoring_schema_version=model.source_authoring_schema_version,
            source_bundle_id=model.source_bundle_id,
            source_file_sha256=model.source_file_sha256,
            source_state_sha256=model.source_state_sha256,
            source_state_signature=model.source_state_signature,
        )
        if current != session.source_binding:
            raise validation_error(
                "Correction session source binding cannot change.",
                details={
                    "session_id": str(model.id),
                    "current_source_state_sha256": current.source_state_sha256,
                    "submitted_source_state_sha256": session.source_binding.source_state_sha256,
                },
            )


def _payload_with_kind(intent: SourceBoundCorrectionIntent) -> dict[str, object]:
    payload: dict[str, object] = dict(intent.payload)
    kind = payload.get("kind")
    if kind is not None and kind != intent.kind.value:
        raise validation_error(
            "Correction payload kind does not match intent kind.",
            details={"entry_id": intent.entry_id, "kind": intent.kind.value, "payload_kind": kind},
        )
    payload["kind"] = intent.kind.value
    return payload
