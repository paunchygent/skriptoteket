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

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.classroom_planner.shares import (
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactSource,
    ClassroomPlannerSharePreviewAsset,
    PublicGuestSharePersistenceResult,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.infrastructure.db.models.classroom_planner_share_artifact import (
    ClassroomPlannerShareArtifactModel,
    ClassroomPlannerSharePreviewAssetModel,
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
            guest_snapshot_fingerprint=artifact.guest_snapshot_fingerprint,
            client_operation_id=artifact.client_operation_id,
            revoke_secret_hash=artifact.revoke_secret_hash,
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
            guest_snapshot_fingerprint=model.guest_snapshot_fingerprint,
            client_operation_id=model.client_operation_id,
            revoke_secret_hash=model.revoke_secret_hash,
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

    def _to_preview_model(
        self,
        preview_asset: ClassroomPlannerSharePreviewAsset,
    ) -> ClassroomPlannerSharePreviewAssetModel:
        return ClassroomPlannerSharePreviewAssetModel(
            share_id=preview_asset.share_id,
            content_type=preview_asset.content_type,
            width=preview_asset.width,
            height=preview_asset.height,
            image_bytes=preview_asset.image_bytes,
            preview_content_hash=preview_asset.preview_content_hash,
            source_content_hash=preview_asset.source_content_hash,
            presentation_hash=preview_asset.presentation_hash,
            renderer_version=preview_asset.renderer_version,
            generated_at=preview_asset.generated_at,
            updated_at=preview_asset.updated_at,
        )

    def _to_preview_asset(
        self,
        model: ClassroomPlannerSharePreviewAssetModel,
    ) -> ClassroomPlannerSharePreviewAsset:
        return ClassroomPlannerSharePreviewAsset(
            share_id=model.share_id,
            content_type=model.content_type,
            width=model.width,
            height=model.height,
            image_bytes=model.image_bytes,
            preview_content_hash=model.preview_content_hash,
            source_content_hash=model.source_content_hash,
            presentation_hash=model.presentation_hash,
            renderer_version=model.renderer_version,
            generated_at=model.generated_at,
            updated_at=model.updated_at,
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

    async def create_with_preview(
        self,
        *,
        artifact: ClassroomPlannerShareArtifact,
        preview_asset: ClassroomPlannerSharePreviewAsset,
    ) -> ClassroomPlannerShareArtifact:
        model = self._to_model(artifact)
        preview_model = self._to_preview_model(preview_asset)
        self._session.add(model)
        self._session.add(preview_model)
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

    async def get_preview_by_share_id(
        self,
        *,
        share_id: UUID,
    ) -> ClassroomPlannerSharePreviewAsset | None:
        model = await self._session.get(ClassroomPlannerSharePreviewAssetModel, share_id)
        return self._to_preview_asset(model) if model else None

    async def upsert_preview_asset(
        self,
        *,
        preview_asset: ClassroomPlannerSharePreviewAsset,
    ) -> ClassroomPlannerSharePreviewAsset:
        model = await self._session.get(
            ClassroomPlannerSharePreviewAssetModel,
            preview_asset.share_id,
        )
        if model is None:
            model = self._to_preview_model(preview_asset)
            self._session.add(model)
        else:
            model.content_type = preview_asset.content_type
            model.width = preview_asset.width
            model.height = preview_asset.height
            model.image_bytes = preview_asset.image_bytes
            model.preview_content_hash = preview_asset.preview_content_hash
            model.source_content_hash = preview_asset.source_content_hash
            model.presentation_hash = preview_asset.presentation_hash
            model.renderer_version = preview_asset.renderer_version
            model.generated_at = preview_asset.generated_at
            model.updated_at = preview_asset.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_preview_asset(model)

    async def update_rendered_artifact(
        self,
        *,
        artifact: ClassroomPlannerShareArtifact,
    ) -> ClassroomPlannerShareArtifact:
        model = await self._session.get(ClassroomPlannerShareArtifactModel, artifact.id)
        if model is None:
            raise ValueError(f"Classroom planner share artifact not found: {artifact.id}")
        model.title = artifact.title
        model.preview_description = artifact.preview_description
        model.renderer_version = artifact.renderer_version
        model.presentation_schema_version = artifact.presentation_schema_version
        model.presentation_hash = artifact.presentation_hash
        model.content_hash = artifact.content_hash
        model.presentation_payload = artifact.presentation_payload
        model.rendered_html = artifact.rendered_html
        model.rendered_css = artifact.rendered_css
        model.updated_at = artifact.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_artifact(model)

    async def list_active_shares_missing_or_stale_preview(
        self,
        *,
        now: datetime,
        limit: int | None,
        current_seating_renderer_version: str,
    ) -> list[ClassroomPlannerShareArtifact]:
        statement = (
            select(ClassroomPlannerShareArtifactModel)
            .outerjoin(
                ClassroomPlannerSharePreviewAssetModel,
                ClassroomPlannerSharePreviewAssetModel.share_id
                == ClassroomPlannerShareArtifactModel.id,
            )
            .where(
                ClassroomPlannerShareArtifactModel.revoked_at.is_(None),
                (
                    (ClassroomPlannerShareArtifactModel.expires_at.is_(None))
                    | (ClassroomPlannerShareArtifactModel.expires_at > now)
                ),
                (
                    (ClassroomPlannerSharePreviewAssetModel.share_id.is_(None))
                    | (
                        ClassroomPlannerSharePreviewAssetModel.source_content_hash
                        != ClassroomPlannerShareArtifactModel.content_hash
                    )
                    | (
                        ClassroomPlannerSharePreviewAssetModel.presentation_hash
                        != ClassroomPlannerShareArtifactModel.presentation_hash
                    )
                    | (
                        ClassroomPlannerSharePreviewAssetModel.renderer_version
                        != ClassroomPlannerShareArtifactModel.renderer_version
                    )
                    | (
                        (
                            ClassroomPlannerShareArtifactModel.draft_kind
                            == PlanDraftKind.SEATING.value
                        )
                        & (
                            ClassroomPlannerShareArtifactModel.renderer_version
                            != current_seating_renderer_version
                        )
                    )
                ),
            )
            .order_by(ClassroomPlannerShareArtifactModel.created_at.asc())
        )
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.execute(statement)
        return [self._to_artifact(model) for model in result.scalars().all()]

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

    async def get_public_guest_by_client_operation_id(
        self,
        *,
        client_operation_id: str,
    ) -> ClassroomPlannerShareArtifact | None:
        result = await self._session.execute(
            select(ClassroomPlannerShareArtifactModel).where(
                ClassroomPlannerShareArtifactModel.source
                == ClassroomPlannerShareArtifactSource.PUBLIC_GUEST.value,
                ClassroomPlannerShareArtifactModel.client_operation_id == client_operation_id,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_artifact(model) if model else None

    async def count_active_public_guest_shares(
        self,
        *,
        guest_snapshot_fingerprint: str,
        now: datetime,
    ) -> int:
        result = await self._session.execute(
            select(ClassroomPlannerShareArtifactModel.id).where(
                ClassroomPlannerShareArtifactModel.source
                == ClassroomPlannerShareArtifactSource.PUBLIC_GUEST.value,
                ClassroomPlannerShareArtifactModel.guest_snapshot_fingerprint
                == guest_snapshot_fingerprint,
                ClassroomPlannerShareArtifactModel.revoked_at.is_(None),
                (
                    (ClassroomPlannerShareArtifactModel.expires_at.is_(None))
                    | (ClassroomPlannerShareArtifactModel.expires_at > now)
                ),
            )
        )
        return len(result.scalars().all())

    async def find_active_public_guest_by_token_and_secret(
        self,
        *,
        token_hash: str,
        revoke_secret_hash: str,
        now: datetime,
    ) -> ClassroomPlannerShareArtifact | None:
        result = await self._session.execute(
            select(ClassroomPlannerShareArtifactModel).where(
                ClassroomPlannerShareArtifactModel.source
                == ClassroomPlannerShareArtifactSource.PUBLIC_GUEST.value,
                ClassroomPlannerShareArtifactModel.token_hash == token_hash,
                ClassroomPlannerShareArtifactModel.revoke_secret_hash == revoke_secret_hash,
                ClassroomPlannerShareArtifactModel.revoked_at.is_(None),
                (
                    (ClassroomPlannerShareArtifactModel.expires_at.is_(None))
                    | (ClassroomPlannerShareArtifactModel.expires_at > now)
                ),
            )
        )
        model = result.scalar_one_or_none()
        return self._to_artifact(model) if model else None

    async def revoke_public_guest_by_token_and_secret(
        self,
        *,
        token_hash: str,
        revoke_secret_hash: str,
        revoked_at: datetime,
    ) -> ClassroomPlannerShareArtifact | None:
        model = (
            await self._session.execute(
                select(ClassroomPlannerShareArtifactModel).where(
                    ClassroomPlannerShareArtifactModel.source
                    == ClassroomPlannerShareArtifactSource.PUBLIC_GUEST.value,
                    ClassroomPlannerShareArtifactModel.token_hash == token_hash,
                    ClassroomPlannerShareArtifactModel.revoke_secret_hash == revoke_secret_hash,
                    ClassroomPlannerShareArtifactModel.revoked_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if model is None:
            return None
        model.revoked_at = revoked_at
        model.updated_at = revoked_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_artifact(model)

    async def create_or_reuse_public_guest_share(
        self,
        *,
        artifact: ClassroomPlannerShareArtifact,
        preview_asset: ClassroomPlannerSharePreviewAsset,
        previous_token_hash: str | None,
        previous_revoke_secret_hash: str | None,
        now: datetime,
        max_active_per_snapshot: int,
    ) -> PublicGuestSharePersistenceResult:
        await self._lock_public_guest_share_keys(
            artifact=artifact,
            previous_token_hash=previous_token_hash,
        )
        existing = await self.get_public_guest_by_client_operation_id(
            client_operation_id=artifact.client_operation_id or ""
        )
        if existing is not None:
            existing_preview = await self.get_preview_by_share_id(share_id=existing.id)
            return PublicGuestSharePersistenceResult(
                artifact=existing,
                preview_asset=existing_preview,
                reused_client_operation=True,
            )

        previous = await self._locked_public_guest_by_token_and_secret(
            previous_token_hash=previous_token_hash,
            previous_revoke_secret_hash=previous_revoke_secret_hash,
            now=now,
        )
        if previous is _STALE_PREVIOUS_SHARE:
            return PublicGuestSharePersistenceResult(
                artifact=None,
                previous_already_superseded=True,
            )

        active_count = await self._active_public_guest_share_count_for_update(
            guest_snapshot_fingerprint=artifact.guest_snapshot_fingerprint or "",
            now=now,
        )
        if active_count >= max_active_per_snapshot and previous is None:
            return PublicGuestSharePersistenceResult(
                artifact=None,
                active_limit_exceeded=True,
            )

        model = self._to_model(artifact)
        preview_model = self._to_preview_model(preview_asset)
        self._session.add(model)
        self._session.add(preview_model)
        await self._session.flush()

        superseded_previous = False
        if isinstance(previous, ClassroomPlannerShareArtifactModel):
            previous.revoked_at = now
            previous.updated_at = now
            superseded_previous = True
            await self._session.flush()

        await self._session.refresh(model)
        return PublicGuestSharePersistenceResult(
            artifact=self._to_artifact(model),
            preview_asset=self._to_preview_asset(preview_model),
            superseded_previous=superseded_previous,
        )

    async def purge_expired_public_guest_shares(self, *, now: datetime) -> int:
        share_ids = list(
            (
                await self._session.execute(
                    select(ClassroomPlannerShareArtifactModel.id).where(
                        ClassroomPlannerShareArtifactModel.source
                        == ClassroomPlannerShareArtifactSource.PUBLIC_GUEST.value,
                        ClassroomPlannerShareArtifactModel.expires_at.is_not(None),
                        ClassroomPlannerShareArtifactModel.expires_at <= now,
                    )
                )
            )
            .scalars()
            .all()
        )
        if not share_ids:
            return 0
        await self._session.execute(
            delete(ClassroomPlannerSharePreviewAssetModel).where(
                ClassroomPlannerSharePreviewAssetModel.share_id.in_(share_ids)
            )
        )
        await self._session.execute(
            update(ClassroomPlannerShareArtifactModel)
            .where(ClassroomPlannerShareArtifactModel.id.in_(share_ids))
            .values(
                rendered_html="",
                rendered_css="",
                presentation_payload=None,
                revoked_at=now,
                updated_at=now,
            )
        )
        await self._session.flush()
        return len(share_ids)

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

    async def _lock_public_guest_share_keys(
        self,
        *,
        artifact: ClassroomPlannerShareArtifact,
        previous_token_hash: str | None,
    ) -> None:
        lock_keys = {
            f"public-guest-share:client:{artifact.client_operation_id or ''}",
            f"public-guest-share:snapshot:{artifact.guest_snapshot_fingerprint or ''}",
        }
        if previous_token_hash:
            lock_keys.add(f"public-guest-share:previous:{previous_token_hash}")
        for lock_key in sorted(lock_keys):
            await self._session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                {"lock_key": lock_key},
            )

    async def _locked_public_guest_by_token_and_secret(
        self,
        *,
        previous_token_hash: str | None,
        previous_revoke_secret_hash: str | None,
        now: datetime,
    ) -> ClassroomPlannerShareArtifactModel | object | None:
        if not previous_token_hash or not previous_revoke_secret_hash:
            return None
        model = (
            await self._session.execute(
                select(ClassroomPlannerShareArtifactModel)
                .where(
                    ClassroomPlannerShareArtifactModel.source
                    == ClassroomPlannerShareArtifactSource.PUBLIC_GUEST.value,
                    ClassroomPlannerShareArtifactModel.token_hash == previous_token_hash,
                    ClassroomPlannerShareArtifactModel.revoke_secret_hash
                    == previous_revoke_secret_hash,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if model is None:
            return None
        if model.revoked_at is not None:
            return _STALE_PREVIOUS_SHARE
        if model.expires_at is not None and model.expires_at <= now:
            return None
        return model

    async def _active_public_guest_share_count_for_update(
        self,
        *,
        guest_snapshot_fingerprint: str,
        now: datetime,
    ) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(ClassroomPlannerShareArtifactModel)
            .where(
                ClassroomPlannerShareArtifactModel.source
                == ClassroomPlannerShareArtifactSource.PUBLIC_GUEST.value,
                ClassroomPlannerShareArtifactModel.guest_snapshot_fingerprint
                == guest_snapshot_fingerprint,
                ClassroomPlannerShareArtifactModel.revoked_at.is_(None),
                (
                    (ClassroomPlannerShareArtifactModel.expires_at.is_(None))
                    | (ClassroomPlannerShareArtifactModel.expires_at > now)
                ),
            )
        )
        return int(result.scalar_one())


_STALE_PREVIOUS_SHARE = object()
