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

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.application.curated_apps.classroom_planner.shares import (
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactCreateResult,
    ClassroomPlannerShareArtifactSource,
    JsonObject,
    build_share_content_hash,
    build_share_presentation_hash,
    build_share_public_path,
    build_share_slug,
    hash_share_token,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.protocols.classroom_planner_shares import (
    ClassroomPlannerShareArtifactRepositoryProtocol,
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
    ) -> None:
        self._shares = shares
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator
        self._token_generator = token_generator

    async def handle(
        self,
        *,
        command: CreateClassroomPlannerShareArtifactCommand,
    ) -> ClassroomPlannerShareArtifactCreateResult:
        _validate_create_command(command)

        now = self._clock.now()
        public_token = self._token_generator.new_token()
        slug = build_share_slug(command.slug or command.title)
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
            title=command.title.strip(),
            slug=slug,
            public_path=build_share_public_path(public_token=public_token, slug=slug),
            preview_description=command.preview_description,
            renderer_version=command.renderer_version,
            presentation_schema_version=command.presentation_schema_version,
            presentation_hash=build_share_presentation_hash(command.presentation_payload),
            content_hash=build_share_content_hash(
                rendered_html=command.rendered_html,
                rendered_css=command.rendered_css,
            ),
            presentation_payload=command.presentation_payload,
            rendered_html=command.rendered_html,
            rendered_css=command.rendered_css,
            created_at=now,
            updated_at=now,
            expires_at=command.expires_at,
        )
        async with self._uow:
            persisted = await self._shares.create(artifact=artifact)
        return ClassroomPlannerShareArtifactCreateResult(
            artifact=persisted,
            public_token=public_token,
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
    raise validation_error(
        "Public guest share artifacts must use the dedicated PR-0273 public helper path."
    )
