"""Application handlers for Klassrumskartan share artifacts.

Purpose:
    Own the persistence-facing share artifact commands for the first
    authenticated share-link implementation slice. The handlers generate
    unguessable public tokens, store only token hashes, and keep create/list/
    revoke behavior separate from export-job orchestration.

Relationships:
    - Uses `ClassroomPlannerShareArtifactRepositoryProtocol` for persistence.
    - Uses shared clock, UUID, token, and Unit of Work protocols from the
      composition root.
    - Produces application share contracts from
      `classroom_planner.shares`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.application.curated_apps.classroom_planner.share_artifact_refresh import (
    refresh_seating_share_artifact_if_needed,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactCreateResult,
    ClassroomPlannerShareArtifactSource,
    ClassroomPlannerSharePreviewAsset,
    JsonObject,
    build_share_content_hash,
    build_share_pdf_download_path,
    build_share_presentation_hash,
    build_share_preview_content_hash,
    build_share_public_path,
    build_share_slug,
    finalize_share_rendered_html,
    hash_share_revoke_secret,
    hash_share_token,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.protocols.classroom_planner_shares import (
    ClassroomPlannerShareArtifactRepositoryProtocol,
    ClassroomPlannerSharePreviewRendererProtocol,
    ClassroomPlannerShareRendererProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class CreateClassroomPlannerShareArtifactCommand(BaseModel):
    """Capture immutable rendered share artifact input from future renderers."""

    model_config = ConfigDict(frozen=True)

    source: ClassroomPlannerShareArtifactSource
    draft_kind: PlanDraftKind
    title: str = Field(min_length=1, max_length=255)
    renderer_version: str = Field(min_length=1, max_length=64)
    presentation_schema_version: str = Field(min_length=1, max_length=64)
    rendered_html: str = Field(min_length=1)
    rendered_css: str = Field(min_length=1)
    owner_user_id: UUID | None = None
    draft_id: UUID | None = None
    roster_id: UUID | None = None
    template_id: UUID | None = None
    source_revision: int | None = Field(default=None, ge=0)
    guest_snapshot_fingerprint: str | None = Field(default=None, max_length=96)
    client_operation_id: str | None = Field(default=None, max_length=128)
    public_revoke_secret: str | None = Field(default=None, min_length=32, max_length=256)
    slug: str | None = Field(default=None, max_length=255)
    preview_description: str | None = Field(default=None, max_length=500)
    presentation_payload: JsonObject | None = None
    expires_at: datetime | None = None


class CreateClassroomPlannerShareArtifactHandler:
    """Persist one immutable share artifact and return its one-time public token."""

    def __init__(
        self,
        *,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        token_generator: TokenGeneratorProtocol,
        preview_renderer: ClassroomPlannerSharePreviewRendererProtocol,
    ) -> None:
        self._shares = shares
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator
        self._token_generator = token_generator
        self._preview_renderer = preview_renderer

    async def handle(
        self,
        *,
        command: CreateClassroomPlannerShareArtifactCommand,
        after_persist: Callable[[ClassroomPlannerShareArtifact], Awaitable[None]] | None = None,
    ) -> ClassroomPlannerShareArtifactCreateResult:
        result = self.build_unsaved(command=command)
        preview_asset = await self.build_preview_asset(artifact=result.artifact)
        async with self._uow:
            persisted = await self._shares.create_with_preview(
                artifact=result.artifact,
                preview_asset=preview_asset,
            )
            if after_persist is not None:
                await after_persist(persisted)
        return result.model_copy(update={"artifact": persisted})

    async def build_preview_asset(
        self,
        *,
        artifact: ClassroomPlannerShareArtifact,
    ) -> ClassroomPlannerSharePreviewAsset:
        """Generate an unsaved preview asset for one unsaved or persisted share."""

        try:
            image_bytes = await self._preview_renderer.render_png(artifact=artifact)
        except DomainError:
            raise
        except Exception as exc:
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Could not generate Klassrumskartan share preview image.",
                details={"reason_code": "classroom_share_preview_generation_failed"},
            ) from exc

        now = self._clock.now()
        return ClassroomPlannerSharePreviewAsset(
            share_id=artifact.id,
            image_bytes=image_bytes,
            preview_content_hash=build_share_preview_content_hash(image_bytes),
            source_content_hash=artifact.content_hash,
            presentation_hash=artifact.presentation_hash,
            renderer_version=artifact.renderer_version,
            generated_at=now,
            updated_at=now,
        )

    def build_unsaved(
        self,
        *,
        command: CreateClassroomPlannerShareArtifactCommand,
    ) -> ClassroomPlannerShareArtifactCreateResult:
        """Build one validated share artifact without persisting it."""

        _validate_create_command(command)

        now = self._clock.now()
        public_token = self._token_generator.new_token()
        revoke_secret_hash = (
            hash_share_revoke_secret(command.public_revoke_secret)
            if command.public_revoke_secret
            else None
        )
        slug = build_share_slug(command.slug or command.title)
        rendered_html = finalize_share_rendered_html(
            rendered_html=command.rendered_html,
            created_at=now,
            pdf_download_path=build_share_pdf_download_path(public_token=public_token),
        )
        artifact = ClassroomPlannerShareArtifact(
            id=self._id_generator.new_uuid(),
            token_hash=hash_share_token(public_token),
            source=command.source,
            draft_kind=command.draft_kind,
            owner_user_id=command.owner_user_id,
            draft_id=command.draft_id,
            roster_id=command.roster_id,
            template_id=command.template_id,
            source_revision=command.source_revision,
            guest_snapshot_fingerprint=command.guest_snapshot_fingerprint,
            client_operation_id=command.client_operation_id,
            revoke_secret_hash=revoke_secret_hash,
            title=command.title.strip(),
            slug=slug,
            public_path=build_share_public_path(public_token=public_token, slug=slug),
            preview_description=command.preview_description,
            renderer_version=command.renderer_version,
            presentation_schema_version=command.presentation_schema_version,
            presentation_hash=build_share_presentation_hash(command.presentation_payload),
            content_hash=build_share_content_hash(
                rendered_html=rendered_html,
                rendered_css=command.rendered_css,
            ),
            presentation_payload=command.presentation_payload,
            rendered_html=rendered_html,
            rendered_css=command.rendered_css,
            created_at=now,
            updated_at=now,
            expires_at=command.expires_at,
        )
        return ClassroomPlannerShareArtifactCreateResult(
            artifact=artifact,
            public_token=public_token,
            public_revoke_secret=command.public_revoke_secret,
        )


class ListClassroomPlannerShareArtifactsHandler:
    """List owner-scoped share artifacts for one planner draft."""

    def __init__(
        self,
        *,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._shares = shares
        self._uow = uow

    async def handle(
        self,
        *,
        owner_user_id: UUID,
        draft_id: UUID,
        draft_kind: PlanDraftKind,
    ) -> list[ClassroomPlannerShareArtifact]:
        async with self._uow:
            return await self._shares.list_for_owner_draft(
                owner_user_id=owner_user_id,
                draft_id=draft_id,
                draft_kind=draft_kind,
            )


class GetClassroomPlannerShareArtifactByTokenHandler:
    """Resolve one share artifact from its public token."""

    def __init__(
        self,
        *,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._shares = shares
        self._uow = uow

    async def handle(self, *, public_token: str) -> ClassroomPlannerShareArtifact:
        async with self._uow:
            artifact = await self._shares.get_by_token_hash(
                token_hash=hash_share_token(public_token),
            )
        if artifact is None:
            raise not_found("ClassroomPlannerShareArtifact", "public-token")
        return artifact


class GetClassroomPlannerSharePreviewAssetHandler:
    """Resolve one generated preview image asset for a share artifact."""

    def __init__(
        self,
        *,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._shares = shares
        self._uow = uow

    async def handle(
        self,
        *,
        share_id: UUID,
    ) -> ClassroomPlannerSharePreviewAsset:
        async with self._uow:
            preview_asset = await self._shares.get_preview_by_share_id(share_id=share_id)
        if preview_asset is None:
            raise not_found("ClassroomPlannerSharePreviewAsset", str(share_id))
        return preview_asset


class BackfillClassroomPlannerSharePreviewsHandler:
    """Generate or refresh preview assets for active legacy share artifacts."""

    def __init__(
        self,
        *,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        create_artifact: CreateClassroomPlannerShareArtifactHandler,
        renderer: ClassroomPlannerShareRendererProtocol,
        current_seating_renderer_version: str,
    ) -> None:
        self._shares = shares
        self._uow = uow
        self._clock = clock
        self._create_artifact = create_artifact
        self._renderer = renderer
        self._current_seating_renderer_version = current_seating_renderer_version

    async def handle(
        self,
        *,
        limit: int | None = None,
        fail_fast: bool = False,
    ) -> "ClassroomPlannerSharePreviewBackfillResult":
        async with self._uow:
            shares = await self._shares.list_active_shares_missing_or_stale_preview(
                now=self._clock.now(),
                limit=limit,
                current_seating_renderer_version=self._current_seating_renderer_version,
            )

        generated = 0
        refreshed = 0
        failed: list[UUID] = []
        for artifact in shares:
            try:
                artifact_to_preview = refresh_seating_share_artifact_if_needed(
                    artifact=artifact,
                    renderer=self._renderer,
                    current_seating_renderer_version=self._current_seating_renderer_version,
                    refreshed_at=self._clock.now(),
                )
                preview_asset = await self._create_artifact.build_preview_asset(
                    artifact=artifact_to_preview,
                )
                async with self._uow:
                    if artifact_to_preview != artifact:
                        artifact_to_preview = await self._shares.update_rendered_artifact(
                            artifact=artifact_to_preview
                        )
                        refreshed += 1
                    await self._shares.upsert_preview_asset(preview_asset=preview_asset)
                generated += 1
            except Exception:
                failed.append(artifact.id)
                if fail_fast:
                    raise

        return ClassroomPlannerSharePreviewBackfillResult(
            scanned=len(shares),
            generated=generated,
            refreshed=refreshed,
            failed_share_ids=tuple(failed),
        )


class ClassroomPlannerSharePreviewBackfillResult(BaseModel):
    """Summarize one preview backfill run."""

    model_config = ConfigDict(frozen=True)

    scanned: int
    generated: int
    refreshed: int = 0
    failed_share_ids: tuple[UUID, ...]


class RevokeClassroomPlannerShareArtifactHandler:
    """Revoke one owner-scoped share artifact."""

    def __init__(
        self,
        *,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._shares = shares
        self._uow = uow
        self._clock = clock

    async def handle(
        self,
        *,
        share_id: UUID,
        owner_user_id: UUID,
    ) -> ClassroomPlannerShareArtifact:
        async with self._uow:
            artifact = await self._shares.revoke_owned(
                share_id=share_id,
                owner_user_id=owner_user_id,
                revoked_at=self._clock.now(),
            )
        if artifact is None:
            raise not_found("ClassroomPlannerShareArtifact", str(share_id))
        return artifact


class ClassroomPlannerShareLifecycleService:
    """Apply deterministic source/owner lifecycle semantics for share artifacts."""

    def __init__(
        self,
        *,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._shares = shares
        self._clock = clock

    async def revoke_for_draft_delete(
        self,
        *,
        owner_user_id: UUID,
        draft_id: UUID,
        draft_kind: PlanDraftKind,
    ) -> int:
        return await self._shares.revoke_for_draft_lifecycle(
            owner_user_id=owner_user_id,
            draft_id=draft_id,
            draft_kind=draft_kind,
            revoked_at=self._clock.now(),
        )

    async def revoke_for_roster_delete(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
    ) -> int:
        return await self._shares.revoke_for_roster_lifecycle(
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            revoked_at=self._clock.now(),
        )

    async def revoke_for_template_delete(
        self,
        *,
        owner_user_id: UUID,
        template_id: UUID,
    ) -> int:
        return await self._shares.revoke_for_template_lifecycle(
            owner_user_id=owner_user_id,
            template_id=template_id,
            revoked_at=self._clock.now(),
        )

    async def revoke_for_owner_delete(
        self,
        *,
        owner_user_id: UUID,
    ) -> int:
        return await self._shares.revoke_for_owner_lifecycle(
            owner_user_id=owner_user_id,
            revoked_at=self._clock.now(),
            detach_owner=True,
        )


def _validate_create_command(command: CreateClassroomPlannerShareArtifactCommand) -> None:
    if command.source is ClassroomPlannerShareArtifactSource.AUTHENTICATED:
        _validate_authenticated_command(command)
    if command.source is ClassroomPlannerShareArtifactSource.PUBLIC_GUEST:
        _validate_public_guest_command(command)


def _validate_authenticated_command(command: CreateClassroomPlannerShareArtifactCommand) -> None:
    if command.owner_user_id is None:
        raise validation_error("Authenticated share artifacts require an owner.")
    if command.draft_id is None or command.roster_id is None:
        raise validation_error("Authenticated share artifacts require draft and roster ids.")
    if command.source_revision is None:
        raise validation_error("Authenticated share artifacts require the source draft revision.")
    if command.expires_at is not None:
        raise validation_error("Authenticated share artifacts do not use default expiry.")


def _validate_public_guest_command(command: CreateClassroomPlannerShareArtifactCommand) -> None:
    if (
        command.owner_user_id is not None
        or command.draft_id is not None
        or command.roster_id is not None
        or command.template_id is not None
    ):
        raise validation_error("Public guest share artifacts must not store source ids.")
    if command.expires_at is None:
        raise validation_error("Public guest share artifacts require an expiry.")
    if command.guest_snapshot_fingerprint is None:
        raise validation_error("Public guest share artifacts require a snapshot fingerprint.")
    if command.client_operation_id is None:
        raise validation_error("Public guest share artifacts require a client operation id.")
    if command.public_revoke_secret is None:
        raise validation_error("Public guest share artifacts require a browser-held revoke secret.")
