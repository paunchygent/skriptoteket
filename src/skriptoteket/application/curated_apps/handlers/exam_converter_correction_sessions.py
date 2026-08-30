"""Application handlers for Exam Converter correction sessions.

Purpose:
  Orchestrate owner-scoped read, replacement, and revert use cases for durable
  correction-session truth without exposing persistence or HTTP concerns.

Relationships:
  - Uses Conversion Hub job ownership as the parent authorization boundary.
  - Uses the correction-session aggregate and repository from PR-0333.
  - Called by PR-0334 FastAPI routes.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.application.curated_apps.exam_converter_correction_sessions import (
    ExamConverterCorrectionSessionResponse,
    ReplaceExamConverterCorrectionIntentsRequest,
    RevertExamConverterCorrectionIntentRequest,
)
from skriptoteket.domain.curated_apps.exam_converter_correction_sessions import (
    ExamConverterCorrectionSession,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.conversion_hub import ConversionHubJobRepositoryProtocol
from skriptoteket.protocols.exam_converter_correction_sessions import (
    ExamConverterCorrectionMutationRepositoryProtocol,
    ExamConverterCorrectionSessionRepositoryProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class _BaseExamConverterCorrectionSessionHandler:
    """Shared owner loading for correction-session handlers."""

    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        sessions: ExamConverterCorrectionSessionRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._jobs = jobs
        self._sessions = sessions
        self._uow = uow

    async def _assert_owned_job(self, *, actor: User, job_id: UUID) -> None:
        job = await self._jobs.get_by_id(job_id=job_id)
        if job is None or job.owner_user_id != actor.id:
            raise not_found("ConversionHubJob", str(job_id))

    async def _load_owned_session(
        self,
        *,
        actor: User,
        job_id: UUID,
    ) -> ExamConverterCorrectionSession | None:
        await self._assert_owned_job(actor=actor, job_id=job_id)
        return await self._sessions.get_by_owner_and_job(
            owner_user_id=actor.id,
            conversion_hub_job_id=job_id,
        )

    def _require_expected_version(
        self,
        *,
        expected_session_version: int | None,
        current_session: ExamConverterCorrectionSession | None,
    ) -> int:
        if expected_session_version is not None:
            return expected_session_version
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Expected correction session version is required.",
            details={
                "current_session_version": (
                    current_session.session_version if current_session is not None else 0
                ),
                "session_id": str(current_session.id) if current_session is not None else None,
            },
        )


class GetExamConverterCorrectionSessionHandler(_BaseExamConverterCorrectionSessionHandler):
    """Load the current owner-scoped correction-session active set."""

    async def handle(
        self,
        *,
        actor: User,
        job_id: UUID,
    ) -> ExamConverterCorrectionSessionResponse:
        async with self._uow:
            session = await self._load_owned_session(actor=actor, job_id=job_id)
        if session is None:
            return ExamConverterCorrectionSessionResponse.empty(
                owner_user_id=actor.id,
                conversion_hub_job_id=job_id,
            )
        return ExamConverterCorrectionSessionResponse.from_domain(session)


class _BaseExamConverterCorrectionMutationHandler(_BaseExamConverterCorrectionSessionHandler):
    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        sessions: ExamConverterCorrectionMutationRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        super().__init__(jobs=jobs, sessions=sessions, uow=uow)
        self._mutation_sessions = sessions

    async def _load_locked_session(
        self, *, actor: User, job_id: UUID
    ) -> ExamConverterCorrectionSession | None:
        await self._mutation_sessions.lock_owned_job(
            owner_user_id=actor.id,
            conversion_hub_job_id=job_id,
        )
        return await self._sessions.get_by_owner_and_job(
            owner_user_id=actor.id,
            conversion_hub_job_id=job_id,
        )


class ReplaceExamConverterCorrectionIntentsHandler(_BaseExamConverterCorrectionMutationHandler):
    """Replace active correction targets through one atomic session write."""

    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        sessions: ExamConverterCorrectionMutationRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        super().__init__(jobs=jobs, sessions=sessions, uow=uow)
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        job_id: UUID,
        request: ReplaceExamConverterCorrectionIntentsRequest,
    ) -> ExamConverterCorrectionSessionResponse:
        async with self._uow:
            current = await self._load_locked_session(actor=actor, job_id=job_id)
            expected = self._require_expected_version(
                expected_session_version=request.expected_session_version,
                current_session=current,
            )
            session = current or ExamConverterCorrectionSession(
                id=self._id_generator.new_uuid(),
                owner_user_id=actor.id,
                conversion_hub_job_id=job_id,
                source_binding=request.intents[0].source_binding,
                session_version=0,
            )
            updated = session.replace_intents(
                intents=tuple(
                    intent.to_domain(intent_id=self._id_generator.new_uuid())
                    for intent in request.intents
                ),
                expected_session_version=expected,
            )
            saved = await self._sessions.save(
                session=updated,
                expected_session_version=expected,
            )
        return ExamConverterCorrectionSessionResponse.from_domain(saved)


class RevertExamConverterCorrectionIntentHandler(_BaseExamConverterCorrectionMutationHandler):
    """Delete or deactivate one active correction intent."""

    async def handle(
        self,
        *,
        actor: User,
        job_id: UUID,
        request: RevertExamConverterCorrectionIntentRequest,
    ) -> ExamConverterCorrectionSessionResponse:
        async with self._uow:
            current = await self._load_locked_session(actor=actor, job_id=job_id)
            expected = self._require_expected_version(
                expected_session_version=request.expected_session_version,
                current_session=current,
            )
            if current is None:
                raise not_found("ExamConverterCorrectionSession", str(job_id))
            updated = current.revert_target(
                target_key=request.target_key,
                expected_session_version=expected,
            )
            saved = await self._sessions.save(
                session=updated,
                expected_session_version=expected,
            )
        return ExamConverterCorrectionSessionResponse.from_domain(saved)
