"""Public guest Klassrumskartan share creation handlers.

Purpose:
    Implement the ADR-0084 public helper path for guest `Dela länk` without
    creating account-owned rows, accepting browser-auth cookies, or storing
    browser-supplied HTML/CSS.

Relationships:
    - Reuses public snapshot materialization from public Smart/export helpers.
    - Reuses the authenticated share renderer and artifact persistence model.
    - Consumed by dedicated public helper routes under `/api/v1/public/apps/...`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportKind,
    GroupingExportPaperSize,
    SeatingExportKind,
    SeatingExportLayoutId,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers import (
    public_smart_run_support,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.grouping_exports import (
    PrepareGroupingExportHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.seating_exports import (
    PrepareSeatingExportHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.share_artifacts import (
    CreateClassroomPlannerShareArtifactCommand,
    CreateClassroomPlannerShareArtifactHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.public_share_contracts import (
    PublicGuestShareRequest,
    PublicGuestShareResult,
    PublicGuestShareRevokeRequest,
    PublicGuestShareRevokeResult,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactSource,
    JsonObject,
    build_share_presentation_hash,
    extract_share_public_token,
    hash_share_revoke_secret,
    hash_share_token,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.protocols.classroom_planner_shares import (
    ClassroomPlannerShareArtifactRepositoryProtocol,
    ClassroomPlannerShareRendererProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


@dataclass(frozen=True, slots=True)
class PublicGuestSharePolicy:
    """Configure public guest share TTL and abuse-control limits."""

    ttl_days: int
    max_rendered_bytes: int
    max_active_per_snapshot: int


class CreatePublicGuestGroupingShareHandler:
    """Create one immutable public guest grouping share artifact."""

    def __init__(
        self,
        *,
        prepare_grouping: PrepareGroupingExportHandler,
        create_artifact: CreateClassroomPlannerShareArtifactHandler,
        renderer: ClassroomPlannerShareRendererProtocol,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        policy: PublicGuestSharePolicy,
    ) -> None:
        self._prepare_grouping = prepare_grouping
        self._create_artifact = create_artifact
        self._renderer = renderer
        self._shares = shares
        self._uow = uow
        self._clock = clock
        self._policy = policy

    async def handle(self, *, request: PublicGuestShareRequest) -> PublicGuestShareResult:
        materialized = public_smart_run_support.materialize_public_smart_workspace(
            snapshot=request.snapshot,
            draft_kind=PlanDraftKind.GROUPING,
            now=self._clock.now(),
        )
        _validate_expected_revision(
            actual_revision=materialized.draft_payload.revision,
            expected_revision=request.expected_revision,
        )
        workspace = public_smart_run_support.build_public_classroom_planner_workspace(
            materialized=materialized
        )
        prepared_export = self._prepare_grouping.build_prepared_contract(
            workspace=workspace,
            export_kind=GroupingExportKind.PDF,
            paper_size=GroupingExportPaperSize.A4_PORTRAIT,
        )
        rendered = self._renderer.render_grouping(prepared_export=prepared_export)
        return await _create_public_guest_share(
            shares=self._shares,
            uow=self._uow,
            clock=self._clock,
            policy=self._policy,
            create_artifact=self._create_artifact,
            request=request,
            draft_kind=PlanDraftKind.GROUPING,
            source_revision=materialized.draft_payload.revision,
            title=rendered.title,
            preview_description=rendered.preview_description,
            renderer_version=rendered.renderer_version,
            presentation_schema_version=rendered.presentation_schema_version,
            presentation_payload=rendered.presentation_payload,
            rendered_html=rendered.rendered_html,
            rendered_css=rendered.rendered_css,
        )


class CreatePublicGuestSeatingShareHandler:
    """Create one immutable public guest seating share artifact."""

    def __init__(
        self,
        *,
        prepare_seating: PrepareSeatingExportHandler,
        create_artifact: CreateClassroomPlannerShareArtifactHandler,
        renderer: ClassroomPlannerShareRendererProtocol,
        shares: ClassroomPlannerShareArtifactRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        policy: PublicGuestSharePolicy,
    ) -> None:
        self._prepare_seating = prepare_seating
        self._create_artifact = create_artifact
        self._renderer = renderer
        self._shares = shares
        self._uow = uow
        self._clock = clock
        self._policy = policy

    async def handle(self, *, request: PublicGuestShareRequest) -> PublicGuestShareResult:
        materialized = public_smart_run_support.materialize_public_smart_workspace(
            snapshot=request.snapshot,
            draft_kind=PlanDraftKind.SEATING,
            now=self._clock.now(),
        )
        _validate_expected_revision(
            actual_revision=materialized.draft_payload.revision,
            expected_revision=request.expected_revision,
        )
        workspace = public_smart_run_support.build_public_classroom_planner_workspace(
            materialized=materialized
        )
        prepared_export = self._prepare_seating.build_prepared_contract(
            workspace=workspace,
            export_kind=SeatingExportKind.PDF,
            layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        )
        rendered = self._renderer.render_seating(prepared_export=prepared_export)
        return await _create_public_guest_share(
            shares=self._shares,
            uow=self._uow,
            clock=self._clock,
            policy=self._policy,
            create_artifact=self._create_artifact,
            request=request,
            draft_kind=PlanDraftKind.SEATING,
            source_revision=materialized.draft_payload.revision,
            title=rendered.title,
            preview_description=rendered.preview_description,
            renderer_version=rendered.renderer_version,
            presentation_schema_version=rendered.presentation_schema_version,
            presentation_payload=rendered.presentation_payload,
            rendered_html=rendered.rendered_html,
            rendered_css=rendered.rendered_css,
        )


class PurgeExpiredPublicGuestShareArtifactsHandler:
    """Purge expired public guest rendered payloads for operator cleanup."""

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

    async def handle(self) -> int:
        async with self._uow:
            return await self._shares.purge_expired_public_guest_shares(now=self._clock.now())


class RevokePublicGuestShareHandler:
    """Revoke the current browser-owned public guest share link."""

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
        request: PublicGuestShareRevokeRequest,
    ) -> PublicGuestShareRevokeResult:
        token = extract_share_public_token(request.public_path)
        if token is None:
            raise validation_error(
                "Invalid public share path.",
                details={"reason_code": "public_helper_invalid_share_path"},
            )

        token_hash = hash_share_token(token)
        revoke_secret_hash = hash_share_revoke_secret(request.revoke_secret)
        now = self._clock.now()
        async with self._uow:
            active = await self._shares.find_active_public_guest_by_token_and_secret(
                token_hash=token_hash,
                revoke_secret_hash=revoke_secret_hash,
                now=now,
            )
            if active is None:
                raise not_found("PublicGuestShare", request.public_path)
            revoked = await self._shares.revoke_public_guest_by_token_and_secret(
                token_hash=token_hash,
                revoke_secret_hash=revoke_secret_hash,
                revoked_at=now,
            )
        if revoked is None:
            raise not_found("PublicGuestShare", request.public_path)
        return PublicGuestShareRevokeResult(
            artifact=revoked,
            public_path=revoked.public_path or request.public_path,
        )


async def _create_public_guest_share(
    *,
    shares: ClassroomPlannerShareArtifactRepositoryProtocol,
    uow: UnitOfWorkProtocol,
    clock: ClockProtocol,
    policy: PublicGuestSharePolicy,
    create_artifact: CreateClassroomPlannerShareArtifactHandler,
    request: PublicGuestShareRequest,
    draft_kind: PlanDraftKind,
    source_revision: int,
    title: str,
    preview_description: str,
    renderer_version: str,
    presentation_schema_version: str,
    presentation_payload: JsonObject,
    rendered_html: str,
    rendered_css: str,
) -> PublicGuestShareResult:
    _enforce_rendered_size(
        rendered_html=rendered_html,
        rendered_css=rendered_css,
        max_bytes=policy.max_rendered_bytes,
    )
    fingerprint = _build_guest_snapshot_fingerprint(
        request=request,
        draft_kind=draft_kind,
    )
    now = clock.now()
    previous_token_hash, previous_revoke_secret_hash = _previous_share_hashes(request=request)
    prepared = create_artifact.build_unsaved(
        command=CreateClassroomPlannerShareArtifactCommand(
            source=ClassroomPlannerShareArtifactSource.PUBLIC_GUEST,
            draft_kind=draft_kind,
            source_revision=source_revision,
            guest_snapshot_fingerprint=fingerprint,
            client_operation_id=request.client_operation_id,
            public_revoke_secret=request.revoke_secret,
            title=title,
            preview_description=preview_description,
            renderer_version=renderer_version,
            presentation_schema_version=presentation_schema_version,
            presentation_payload=presentation_payload,
            rendered_html=rendered_html,
            rendered_css=rendered_css,
            expires_at=now + timedelta(days=policy.ttl_days),
        )
    )
    preview_asset = await create_artifact.build_preview_asset(artifact=prepared.artifact)
    async with uow:
        persisted = await shares.create_or_reuse_public_guest_share(
            artifact=prepared.artifact,
            preview_asset=preview_asset,
            previous_token_hash=previous_token_hash,
            previous_revoke_secret_hash=previous_revoke_secret_hash,
            now=now,
            max_active_per_snapshot=policy.max_active_per_snapshot,
        )

    if persisted.artifact is not None and persisted.reused_client_operation:
        return _public_guest_result(
            artifact=persisted.artifact,
            public_revoke_secret=request.revoke_secret,
            superseded_previous=False,
            reused_client_operation=True,
        )
    if persisted.active_limit_exceeded:
        raise DomainError(
            code=ErrorCode.TOO_MANY_REQUESTS,
            message="Too many active public guest share links for this browser snapshot.",
            details={
                "reason_code": "public_helper_active_share_limit",
                "max_active_per_snapshot": policy.max_active_per_snapshot,
            },
        )
    if persisted.previous_already_superseded:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="The previous public guest share link was already superseded.",
            details={
                "reason_code": "public_helper_previous_share_already_superseded",
            },
        )
    if persisted.artifact is None:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Public guest share persistence did not create a share.",
            details={"reason_code": "public_helper_share_persistence_conflict"},
        )
    return PublicGuestShareResult(
        artifact=persisted.artifact,
        public_path=persisted.artifact.public_path or prepared.public_path,
        public_revoke_secret=request.revoke_secret,
        superseded_previous=persisted.superseded_previous,
    )


def _previous_share_hashes(
    *,
    request: PublicGuestShareRequest,
) -> tuple[str | None, str | None]:
    if not request.previous_public_path or not request.previous_revoke_secret:
        return None, None
    previous_token = extract_share_public_token(request.previous_public_path)
    if previous_token is None:
        return None, None
    return (
        hash_share_token(previous_token),
        hash_share_revoke_secret(request.previous_revoke_secret),
    )


def _validate_expected_revision(*, actual_revision: int, expected_revision: int) -> None:
    if actual_revision == expected_revision:
        return
    raise DomainError(
        code=ErrorCode.CONFLICT,
        message=f"Draft revision mismatch. Expected {expected_revision}, got {actual_revision}.",
        details={
            "expected_revision": expected_revision,
            "actual_revision": actual_revision,
        },
    )


def _enforce_rendered_size(*, rendered_html: str, rendered_css: str, max_bytes: int) -> None:
    rendered_bytes = len(rendered_html.encode("utf-8")) + len(rendered_css.encode("utf-8"))
    if rendered_bytes <= max_bytes:
        return
    raise DomainError(
        code=ErrorCode.PAYLOAD_TOO_LARGE,
        message="Rendered public guest share exceeds the allowed size.",
        details={
            "reason_code": "public_helper_rendered_share_too_large",
            "max_bytes": max_bytes,
        },
    )


def _build_guest_snapshot_fingerprint(
    *,
    request: PublicGuestShareRequest,
    draft_kind: PlanDraftKind,
) -> str:
    payload = request.snapshot.model_dump(mode="json")
    return build_share_presentation_hash(
        {
            "draft_kind": draft_kind.value,
            "snapshot": json.loads(json.dumps(payload, sort_keys=True)),
        }
    )


def _public_guest_result(
    *,
    artifact: ClassroomPlannerShareArtifact,
    public_revoke_secret: str,
    superseded_previous: bool,
    reused_client_operation: bool,
) -> PublicGuestShareResult:
    return PublicGuestShareResult(
        artifact=artifact,
        public_path=artifact.public_path or "",
        public_revoke_secret=public_revoke_secret,
        superseded_previous=superseded_previous,
        reused_client_operation=reused_client_operation,
    )
