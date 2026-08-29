"""PostgreSQL repository for machine-proposed answer-key overlays.

Purpose:
    Persist the machine-proposed ingestion overlay documents that carry
    answer-key proposals for in-process conversions.

Relationships:
    Implements ``ExamAnswerKeyProposedOverlayRepositoryProtocol`` on a
    request-scoped ``AsyncSession``; commit/rollback is owned by the UoW.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyProposedOverlay,
)
from skriptoteket.infrastructure.db.models.exam_answer_key_proposed_overlay import (
    ExamAnswerKeyProposedOverlayModel,
)
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyProposedOverlayRepositoryProtocol


class PostgreSQLExamAnswerKeyProposedOverlayRepository(
    ExamAnswerKeyProposedOverlayRepositoryProtocol
):
    """Postgres proposal records for machine-proposed overlays."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        proposed_overlay: ExamAnswerKeyProposedOverlay,
    ) -> ExamAnswerKeyProposedOverlay:
        model = ExamAnswerKeyProposedOverlayModel(
            id=proposed_overlay.id,
            enrichment_job_id=proposed_overlay.enrichment_job_id,
            conversion_job_id=proposed_overlay.conversion_job_id,
            owner_user_id=proposed_overlay.owner_user_id,
            source_file_sha256=proposed_overlay.source_file_sha256,
            source_ir_sha256=proposed_overlay.source_ir_sha256,
            provider_profile_id=proposed_overlay.provider_profile_id,
            model=proposed_overlay.model,
            overlay_json=proposed_overlay.overlay_json,
            created_at=proposed_overlay.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return ExamAnswerKeyProposedOverlay.model_validate(model)

    async def get_by_conversion_job_id(
        self,
        *,
        conversion_job_id: UUID,
    ) -> ExamAnswerKeyProposedOverlay | None:
        stmt = select(ExamAnswerKeyProposedOverlayModel).where(
            ExamAnswerKeyProposedOverlayModel.conversion_job_id == conversion_job_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return ExamAnswerKeyProposedOverlay.model_validate(model) if model else None
