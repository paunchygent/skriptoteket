"""PostgreSQL repository for Klassrumskartan share artifacts.

Purpose:
    Map the dedicated share artifact table to typed application models while
    keeping share-link persistence separate from export jobs, Vault artifacts,
    and mutable classroom-planner drafts.

Relationships:
    - Implements `ClassroomPlannerShareArtifactRepositoryProtocol`.
    - Uses `ClassroomPlannerShareArtifactModel` from the DB model package.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.classroom_planner.shares import (
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactSource,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.infrastructure.db.models.classroom_planner_share_artifact import (
    ClassroomPlannerShareArtifactModel,
)
from skriptoteket.protocols.classroom_planner_shares import (
    ClassroomPlannerShareArtifactRepositoryProtocol,
)


class PostgreSQLClassroomPlannerShareArtifactRepository(
    ClassroomPlannerShareArtifactRepositoryProtocol
):
    """Persist immutable classroom-planner share artifacts in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_model(
        self,
        artifact: ClassroomPlannerShareArtifact,
    ) -> ClassroomPlannerShareArtifactModel:
        return ClassroomPlannerShareArtifactModel(
            id=artifact.id,
            token_hash=artifact.token_hash,
            source=artifact.source.value,
            draft_kind=artifact.draft_kind.value,
            owner_user_id=artifact.owner_user_id,
            draft_id=artifact.draft_id,
            roster_id=artifact.roster_id,
            template_id=artifact.template_id,
            source_revision=artifact.source_revision,
            title=artifact.title,
            slug=artifact.slug,
            public_path=artifact.public_path,
            preview_description=artifact.preview_description,
            renderer_version=artifact.renderer_version,
            presentation_schema_version=artifact.presentation_schema_version,
            presentation_hash=artifact.presentation_hash,
            content_hash=artifact.content_hash,
            presentation_payload=artifact.presentation_payload,
            rendered_html=artifact.rendered_html,
            rendered_css=artifact.rendered_css,
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
            revoked_at=artifact.revoked_at,
            expires_at=artifact.expires_at,
        )

    def _to_artifact(
        self,
        model: ClassroomPlannerShareArtifactModel,
    ) -> ClassroomPlannerShareArtifact:
        return ClassroomPlannerShareArtifact(
            id=model.id,
            token_hash=model.token_hash,
            source=ClassroomPlannerShareArtifactSource(model.source),
            draft_kind=PlanDraftKind(model.draft_kind),
            owner_user_id=model.owner_user_id,
            draft_id=model.draft_id,
            roster_id=model.roster_id,
            template_id=model.template_id,
            source_revision=model.source_revision,
            title=model.title,
            slug=model.slug,
            public_path=model.public_path,
            preview_description=model.preview_description,
            renderer_version=model.renderer_version,
            presentation_schema_version=model.presentation_schema_version,
            presentation_hash=model.presentation_hash,
            content_hash=model.content_hash,
            presentation_payload=model.presentation_payload,
            rendered_html=model.rendered_html,
            rendered_css=model.rendered_css,
            created_at=model.created_at,
            updated_at=model.updated_at,
            revoked_at=model.revoked_at,
            expires_at=model.expires_at,
        )

    async def create(
        self,
        *,
        artifact: ClassroomPlannerShareArtifact,
    ) -> ClassroomPlannerShareArtifact:
        model = self._to_model(artifact)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_artifact(model)

    async def get_by_id(self, *, share_id: UUID) -> ClassroomPlannerShareArtifact | None:
        model = await self._session.get(ClassroomPlannerShareArtifactModel, share_id)
        return self._to_artifact(model) if model else None

    async def get_by_token_hash(
        self,
        *,
        token_hash: str,
    ) -> ClassroomPlannerShareArtifact | None:
        result = await self._session.execute(
            select(ClassroomPlannerShareArtifactModel).where(
                ClassroomPlannerShareArtifactModel.token_hash == token_hash
            )
        )
        model = result.scalar_one_or_none()
        return self._to_artifact(model) if model else None

    async def list_for_owner_draft(
        self,
        *,
        owner_user_id: UUID,
        draft_id: UUID,
        draft_kind: PlanDraftKind,
    ) -> list[ClassroomPlannerShareArtifact]:
        result = await self._session.execute(
            select(ClassroomPlannerShareArtifactModel)
            .where(
                ClassroomPlannerShareArtifactModel.owner_user_id == owner_user_id,
                ClassroomPlannerShareArtifactModel.draft_id == draft_id,
                ClassroomPlannerShareArtifactModel.draft_kind == draft_kind.value,
            )
            .order_by(
                ClassroomPlannerShareArtifactModel.created_at.desc(),
                ClassroomPlannerShareArtifactModel.updated_at.desc(),
            )
        )
        return [self._to_artifact(model) for model in result.scalars().all()]

    async def revoke_owned(
        self,
        *,
        share_id: UUID,
        owner_user_id: UUID,
        revoked_at: datetime,
    ) -> ClassroomPlannerShareArtifact | None:
        model = await self._session.get(ClassroomPlannerShareArtifactModel, share_id)
        if model is None or model.owner_user_id != owner_user_id:
            return None
        model.revoked_at = revoked_at
        model.updated_at = revoked_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_artifact(model)

    async def revoke_for_draft_lifecycle(
        self,
        *,
        owner_user_id: UUID,
        draft_id: UUID,
        draft_kind: PlanDraftKind,
        revoked_at: datetime,
    ) -> int:
        share_ids = await self._share_ids_matching(
            owner_user_id=owner_user_id,
            draft_id=draft_id,
            draft_kind=draft_kind,
        )
        if not share_ids:
            return 0
        await self._session.execute(
            update(ClassroomPlannerShareArtifactModel)
            .where(
                ClassroomPlannerShareArtifactModel.id.in_(share_ids),
            )
            .values(
                draft_id=None,
                revoked_at=revoked_at,
                updated_at=revoked_at,
            )
        )
        await self._session.flush()
        return len(share_ids)

    async def revoke_for_roster_lifecycle(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        revoked_at: datetime,
    ) -> int:
        share_ids = await self._share_ids_matching(
            owner_user_id=owner_user_id,
            roster_id=roster_id,
        )
        if not share_ids:
            return 0
        await self._session.execute(
            update(ClassroomPlannerShareArtifactModel)
            .where(
                ClassroomPlannerShareArtifactModel.id.in_(share_ids),
            )
            .values(
                draft_id=None,
                roster_id=None,
                revoked_at=revoked_at,
                updated_at=revoked_at,
            )
        )
        await self._session.flush()
        return len(share_ids)

    async def revoke_for_template_lifecycle(
        self,
        *,
        owner_user_id: UUID,
        template_id: UUID,
        revoked_at: datetime,
    ) -> int:
        share_ids = await self._share_ids_matching(
            owner_user_id=owner_user_id,
            template_id=template_id,
        )
        if not share_ids:
            return 0
        await self._session.execute(
            update(ClassroomPlannerShareArtifactModel)
            .where(
                ClassroomPlannerShareArtifactModel.id.in_(share_ids),
            )
            .values(
                draft_id=None,
                template_id=None,
                revoked_at=revoked_at,
                updated_at=revoked_at,
            )
        )
        await self._session.flush()
        return len(share_ids)

    async def revoke_for_owner_lifecycle(
        self,
        *,
        owner_user_id: UUID,
        revoked_at: datetime,
        detach_owner: bool,
    ) -> int:
        values: dict[str, object] = {
            "revoked_at": revoked_at,
            "updated_at": revoked_at,
        }
        if detach_owner:
            values["owner_user_id"] = None
            values["draft_id"] = None
            values["roster_id"] = None
            values["template_id"] = None

        share_ids = await self._share_ids_matching(owner_user_id=owner_user_id)
        if not share_ids:
            return 0

        await self._session.execute(
            update(ClassroomPlannerShareArtifactModel)
            .where(ClassroomPlannerShareArtifactModel.id.in_(share_ids))
            .values(**values)
        )
        await self._session.flush()
        return len(share_ids)

    async def _share_ids_matching(
        self,
        *,
        owner_user_id: UUID,
        draft_id: UUID | None = None,
        draft_kind: PlanDraftKind | None = None,
        roster_id: UUID | None = None,
        template_id: UUID | None = None,
    ) -> list[UUID]:
        conditions = [ClassroomPlannerShareArtifactModel.owner_user_id == owner_user_id]
        if draft_id is not None:
            conditions.append(ClassroomPlannerShareArtifactModel.draft_id == draft_id)
        if draft_kind is not None:
            conditions.append(ClassroomPlannerShareArtifactModel.draft_kind == draft_kind.value)
        if roster_id is not None:
            conditions.append(ClassroomPlannerShareArtifactModel.roster_id == roster_id)
        if template_id is not None:
            conditions.append(ClassroomPlannerShareArtifactModel.template_id == template_id)

        result = await self._session.execute(
            select(ClassroomPlannerShareArtifactModel.id).where(*conditions)
        )
        return list(result.scalars().all())
