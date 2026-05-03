"""Behavior tests for Klassrumskartan share artifact handlers.

Purpose:
    Lock the first PR-0274 backend foundation slice: share artifacts are
    persisted through protocols, public tokens are hashed before storage, and
    owner-scoped list/revoke behavior stays separate from export jobs.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import (
    BackfillClassroomPlannerSharePreviewsHandler,
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactSource,
    ClassroomPlannerShareLifecycleService,
    ClassroomPlannerSharePreviewAsset,
    CreateClassroomPlannerShareArtifactCommand,
    CreateClassroomPlannerShareArtifactHandler,
    GetClassroomPlannerShareArtifactByTokenHandler,
    GetClassroomPlannerSharePreviewAssetHandler,
    ListClassroomPlannerShareArtifactsHandler,
    RenderedClassroomPlannerShare,
    RevokeClassroomPlannerShareArtifactHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.exports import (
    PosterSceneRoom,
    PreparedGroupingExportContract,
    PreparedSeatingExportContract,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingPosterScene,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    SHARE_CREATED_DATE_CHROME_SLOT,
    SHARE_CREATED_DATE_PLACEHOLDER,
    SHARE_PDF_DOWNLOAD_HREF_CHROME_SLOT,
    SHARE_PDF_DOWNLOAD_PATH_PLACEHOLDER,
    JsonObject,
    PublicGuestSharePersistenceResult,
    build_share_content_hash,
    build_share_presentation_hash,
    build_share_preview_content_hash,
    hash_share_token,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.domain.errors import DomainError, ErrorCode


class _DummyUow:
    async def __aenter__(self) -> _DummyUow:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class _FixedIdGenerator:
    def __init__(self, value: UUID) -> None:
        self._value = value

    def new_uuid(self) -> UUID:
        return self._value


class _FixedTokenGenerator:
    def __init__(self, value: str) -> None:
        self._value = value

    def new_token(self) -> str:
        return self._value


class _FakePreviewRenderer:
    def __init__(self, *, image_bytes: bytes = b"\x89PNG\r\npreview") -> None:
        self._image_bytes = image_bytes
        self.rendered_artifacts: list[ClassroomPlannerShareArtifact] = []

    async def render_png(self, *, artifact: ClassroomPlannerShareArtifact) -> bytes:
        self.rendered_artifacts.append(artifact)
        return self._image_bytes


class _FakeShareRenderer:
    def render_grouping(
        self,
        *,
        prepared_export: PreparedGroupingExportContract,
    ) -> RenderedClassroomPlannerShare:
        raise AssertionError("Grouping shares are outside this test fake.")

    def render_seating(
        self,
        *,
        prepared_export: PreparedSeatingExportContract,
    ) -> RenderedClassroomPlannerShare:
        payload = prepared_export.model_dump(mode="json")
        assert isinstance(payload, dict)
        return RenderedClassroomPlannerShare(
            title=f"{prepared_export.roster_name} - Sittschema",
            preview_description=f"Sittschema för {prepared_export.roster_name}.",
            renderer_version="klassrumskartan-seating-share-renderer-v2",
            presentation_schema_version="seating-share-v1",
            presentation_payload=payload,
            rendered_html=(
                f"<main><p>Skapad: {SHARE_CREATED_DATE_CHROME_SLOT}</p>"
                f"<a {SHARE_PDF_DOWNLOAD_HREF_CHROME_SLOT}>PDF</a>"
                f"{prepared_export.roster_name} refreshed</main>"
            ),
            rendered_css="main { color: navy; }",
        )


class _FakeShareRepository:
    def __init__(self) -> None:
        self.artifacts_by_id: dict[UUID, ClassroomPlannerShareArtifact] = {}
        self.preview_assets_by_share_id: dict[UUID, ClassroomPlannerSharePreviewAsset] = {}
        self.token_hashes_seen: list[str] = []

    async def create(
        self,
        *,
        artifact: ClassroomPlannerShareArtifact,
    ) -> ClassroomPlannerShareArtifact:
        self.artifacts_by_id[artifact.id] = artifact
        return artifact

    async def create_with_preview(
        self,
        *,
        artifact: ClassroomPlannerShareArtifact,
        preview_asset: ClassroomPlannerSharePreviewAsset,
    ) -> ClassroomPlannerShareArtifact:
        self.artifacts_by_id[artifact.id] = artifact
        self.preview_assets_by_share_id[artifact.id] = preview_asset
        return artifact

    async def get_by_id(self, *, share_id: UUID) -> ClassroomPlannerShareArtifact | None:
        return self.artifacts_by_id.get(share_id)

    async def get_by_token_hash(
        self,
        *,
        token_hash: str,
    ) -> ClassroomPlannerShareArtifact | None:
        self.token_hashes_seen.append(token_hash)
        return next(
            (
                artifact
                for artifact in self.artifacts_by_id.values()
                if artifact.token_hash == token_hash
            ),
            None,
        )

    async def get_preview_by_share_id(
        self,
        *,
        share_id: UUID,
    ) -> ClassroomPlannerSharePreviewAsset | None:
        return self.preview_assets_by_share_id.get(share_id)

    async def upsert_preview_asset(
        self,
        *,
        preview_asset: ClassroomPlannerSharePreviewAsset,
    ) -> ClassroomPlannerSharePreviewAsset:
        self.preview_assets_by_share_id[preview_asset.share_id] = preview_asset
        return preview_asset

    async def update_rendered_artifact(
        self,
        *,
        artifact: ClassroomPlannerShareArtifact,
    ) -> ClassroomPlannerShareArtifact:
        self.artifacts_by_id[artifact.id] = artifact
        return artifact

    async def list_active_shares_missing_or_stale_preview(
        self,
        *,
        now: datetime,
        limit: int | None,
        current_seating_renderer_version: str,
    ) -> list[ClassroomPlannerShareArtifact]:
        matches = [
            artifact
            for artifact in self.artifacts_by_id.values()
            if artifact.revoked_at is None
            and (artifact.expires_at is None or artifact.expires_at > now)
            and (
                _is_missing_or_stale_preview(
                    artifact=artifact,
                    preview_asset=self.preview_assets_by_share_id.get(artifact.id),
                )
                or (
                    artifact.draft_kind is PlanDraftKind.SEATING
                    and artifact.renderer_version != current_seating_renderer_version
                )
            )
        ]
        return matches[:limit] if limit is not None else matches

    async def list_for_owner_draft(
        self,
        *,
        owner_user_id: UUID,
        draft_id: UUID,
        draft_kind: PlanDraftKind,
    ) -> list[ClassroomPlannerShareArtifact]:
        return [
            artifact
            for artifact in self.artifacts_by_id.values()
            if artifact.owner_user_id == owner_user_id
            and artifact.draft_id == draft_id
            and artifact.draft_kind is draft_kind
        ]

    async def revoke_owned(
        self,
        *,
        share_id: UUID,
        owner_user_id: UUID,
        revoked_at: datetime,
    ) -> ClassroomPlannerShareArtifact | None:
        artifact = self.artifacts_by_id.get(share_id)
        if artifact is None or artifact.owner_user_id != owner_user_id:
            return None
        revoked = artifact.model_copy(update={"revoked_at": revoked_at, "updated_at": revoked_at})
        self.artifacts_by_id[share_id] = revoked
        return revoked

    async def get_public_guest_by_client_operation_id(
        self,
        *,
        client_operation_id: str,
    ) -> ClassroomPlannerShareArtifact | None:
        return next(
            (
                artifact
                for artifact in self.artifacts_by_id.values()
                if artifact.source is ClassroomPlannerShareArtifactSource.PUBLIC_GUEST
                and artifact.client_operation_id == client_operation_id
            ),
            None,
        )

    async def count_active_public_guest_shares(
        self,
        *,
        guest_snapshot_fingerprint: str,
        now: datetime,
    ) -> int:
        return len(
            [
                artifact
                for artifact in self.artifacts_by_id.values()
                if artifact.source is ClassroomPlannerShareArtifactSource.PUBLIC_GUEST
                and artifact.guest_snapshot_fingerprint == guest_snapshot_fingerprint
                and artifact.revoked_at is None
                and (artifact.expires_at is None or artifact.expires_at > now)
            ]
        )

    async def find_active_public_guest_by_token_and_secret(
        self,
        *,
        token_hash: str,
        revoke_secret_hash: str,
        now: datetime,
    ) -> ClassroomPlannerShareArtifact | None:
        return next(
            (
                artifact
                for artifact in self.artifacts_by_id.values()
                if artifact.source is ClassroomPlannerShareArtifactSource.PUBLIC_GUEST
                and artifact.token_hash == token_hash
                and artifact.revoke_secret_hash == revoke_secret_hash
                and artifact.revoked_at is None
                and (artifact.expires_at is None or artifact.expires_at > now)
            ),
            None,
        )

    async def revoke_public_guest_by_token_and_secret(
        self,
        *,
        token_hash: str,
        revoke_secret_hash: str,
        revoked_at: datetime,
    ) -> ClassroomPlannerShareArtifact | None:
        artifact = await self.find_active_public_guest_by_token_and_secret(
            token_hash=token_hash,
            revoke_secret_hash=revoke_secret_hash,
            now=revoked_at,
        )
        if artifact is None:
            return None
        revoked = artifact.model_copy(update={"revoked_at": revoked_at, "updated_at": revoked_at})
        self.artifacts_by_id[artifact.id] = revoked
        return revoked

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
        del previous_token_hash, previous_revoke_secret_hash, now, max_active_per_snapshot
        existing = await self.get_public_guest_by_client_operation_id(
            client_operation_id=artifact.client_operation_id or ""
        )
        if existing is not None:
            return PublicGuestSharePersistenceResult(
                artifact=existing,
                preview_asset=self.preview_assets_by_share_id.get(existing.id),
                reused_client_operation=True,
            )
        created = await self.create_with_preview(artifact=artifact, preview_asset=preview_asset)
        return PublicGuestSharePersistenceResult(
            artifact=created,
            preview_asset=preview_asset,
        )

    async def purge_expired_public_guest_shares(self, *, now: datetime) -> int:
        return self._revoke_matching(
            revoked_at=now,
            predicate=lambda artifact: (
                artifact.source is ClassroomPlannerShareArtifactSource.PUBLIC_GUEST
                and artifact.expires_at is not None
                and artifact.expires_at <= now
            ),
            updates={"rendered_html": "", "rendered_css": "", "presentation_payload": None},
        )

    async def revoke_for_draft_lifecycle(
        self,
        *,
        owner_user_id: UUID,
        draft_id: UUID,
        draft_kind: PlanDraftKind,
        revoked_at: datetime,
    ) -> int:
        return self._revoke_matching(
            revoked_at=revoked_at,
            predicate=lambda artifact: (
                artifact.owner_user_id == owner_user_id
                and artifact.draft_id == draft_id
                and artifact.draft_kind is draft_kind
            ),
            updates={"draft_id": None},
        )

    async def revoke_for_roster_lifecycle(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        revoked_at: datetime,
    ) -> int:
        return self._revoke_matching(
            revoked_at=revoked_at,
            predicate=lambda artifact: (
                artifact.owner_user_id == owner_user_id and artifact.roster_id == roster_id
            ),
            updates={"draft_id": None, "roster_id": None},
        )

    async def revoke_for_template_lifecycle(
        self,
        *,
        owner_user_id: UUID,
        template_id: UUID,
        revoked_at: datetime,
    ) -> int:
        return self._revoke_matching(
            revoked_at=revoked_at,
            predicate=lambda artifact: (
                artifact.owner_user_id == owner_user_id and artifact.template_id == template_id
            ),
            updates={"draft_id": None, "template_id": None},
        )

    async def revoke_for_owner_lifecycle(
        self,
        *,
        owner_user_id: UUID,
        revoked_at: datetime,
        detach_owner: bool,
    ) -> int:
        updates = (
            {"owner_user_id": None, "draft_id": None, "roster_id": None, "template_id": None}
            if detach_owner
            else {}
        )
        return self._revoke_matching(
            revoked_at=revoked_at,
            predicate=lambda artifact: artifact.owner_user_id == owner_user_id,
            updates=updates,
        )

    def _revoke_matching(
        self,
        *,
        revoked_at: datetime,
        predicate: Callable[[ClassroomPlannerShareArtifact], bool],
        updates: Mapping[str, object],
    ) -> int:
        count = 0
        for share_id, artifact in list(self.artifacts_by_id.items()):
            if not predicate(artifact):
                continue
            self.artifacts_by_id[share_id] = artifact.model_copy(
                update={"revoked_at": revoked_at, "updated_at": revoked_at, **updates}
            )
            count += 1
        return count


def _is_missing_or_stale_preview(
    *,
    artifact: ClassroomPlannerShareArtifact,
    preview_asset: ClassroomPlannerSharePreviewAsset | None,
) -> bool:
    return (
        preview_asset is None
        or preview_asset.source_content_hash != artifact.content_hash
        or preview_asset.presentation_hash != artifact.presentation_hash
        or preview_asset.renderer_version != artifact.renderer_version
    )


def _create_handler(
    *,
    shares: _FakeShareRepository,
    now: datetime,
    share_id: UUID | None = None,
    public_token: str = "public-token",
    preview_renderer: _FakePreviewRenderer | None = None,
) -> CreateClassroomPlannerShareArtifactHandler:
    return CreateClassroomPlannerShareArtifactHandler(
        shares=shares,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator(share_id or uuid4()),
        token_generator=_FixedTokenGenerator(public_token),
        preview_renderer=preview_renderer or _FakePreviewRenderer(),
    )


def _command(
    *,
    owner_user_id: UUID,
    draft_id: UUID,
    roster_id: UUID,
) -> CreateClassroomPlannerShareArtifactCommand:
    return CreateClassroomPlannerShareArtifactCommand(
        source=ClassroomPlannerShareArtifactSource.AUTHENTICATED,
        draft_kind=PlanDraftKind.GROUPING,
        owner_user_id=owner_user_id,
        draft_id=draft_id,
        roster_id=roster_id,
        source_revision=7,
        title="Klass 7A Share!",
        preview_description="Frozen grouping plan",
        renderer_version="share-renderer-v1",
        presentation_schema_version="grouping-share-v1",
        presentation_payload={"title": "Klass 7A", "student_count": 2},
        rendered_html=(
            f"<main><p>Skapad: {SHARE_CREATED_DATE_CHROME_SLOT}</p>"
            f"<a {SHARE_PDF_DOWNLOAD_HREF_CHROME_SLOT}>PDF</a>Klass 7A</main>"
        ),
        rendered_css="main { color: black; }",
    )


def _seating_presentation_payload() -> JsonObject:
    prepared = PreparedSeatingExportContract(
        seating_draft_id=uuid4(),
        roster_id=uuid4(),
        roster_name="Klass 8B",
        template_id=uuid4(),
        template_name="Sal A",
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        poster_scene=SeatingPosterScene(
            room=PosterSceneRoom(grid_cols=12, grid_rows=8),
            seats=[],
            fixtures=[],
        ),
    )
    payload = prepared.model_dump(mode="json")
    assert isinstance(payload, dict)
    return payload


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_share_artifact_hashes_public_token_and_content() -> None:
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    share_id = uuid4()
    owner_user_id = uuid4()
    draft_id = uuid4()
    roster_id = uuid4()
    shares = _FakeShareRepository()
    preview_renderer = _FakePreviewRenderer()
    handler = _create_handler(
        shares=shares,
        now=now,
        share_id=share_id,
        public_token="public-token",
        preview_renderer=preview_renderer,
    )

    result = await handler.handle(
        command=_command(
            owner_user_id=owner_user_id,
            draft_id=draft_id,
            roster_id=roster_id,
        )
    )

    artifact = result.artifact
    assert result.public_token == "public-token"
    assert result.public_path == "/share/classroom/public-token/klass-7a-share"
    assert artifact.public_path == "/share/classroom/public-token/klass-7a-share"
    assert artifact.id == share_id
    assert artifact.owner_user_id == owner_user_id
    assert artifact.draft_id == draft_id
    assert artifact.roster_id == roster_id
    assert artifact.source_revision == 7
    assert artifact.token_hash == hash_share_token("public-token")
    assert "public-token" not in artifact.token_hash
    assert artifact.presentation_hash == build_share_presentation_hash(
        artifact.presentation_payload
    )
    assert artifact.content_hash == build_share_content_hash(
        rendered_html=artifact.rendered_html,
        rendered_css=artifact.rendered_css,
    )
    assert 'data-skriptoteket-share-created-date="owned">2026-04-30</span>' in (
        artifact.rendered_html
    )
    assert 'href="/share/classroom/public-token/download.pdf"' in artifact.rendered_html
    assert SHARE_CREATED_DATE_PLACEHOLDER not in artifact.rendered_html
    assert SHARE_PDF_DOWNLOAD_PATH_PLACEHOLDER not in artifact.rendered_html
    assert artifact.expires_at is None
    assert shares.artifacts_by_id[share_id] == artifact
    assert preview_renderer.rendered_artifacts == [artifact]
    assert shares.preview_assets_by_share_id[share_id].source_content_hash == artifact.content_hash
    assert shares.preview_assets_by_share_id[share_id].preview_content_hash == (
        build_share_preview_content_hash(b"\x89PNG\r\npreview")
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_share_artifact_normalizes_custom_slug() -> None:
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    handler = _create_handler(
        shares=_FakeShareRepository(),
        now=now,
    )
    command = _command(
        owner_user_id=uuid4(),
        draft_id=uuid4(),
        roster_id=uuid4(),
    ).model_copy(update={"slug": " ../Klass 7A?share#frag/ "})

    result = await handler.handle(command=command)

    assert result.artifact.slug == "klass-7a-share-frag"
    assert result.public_path == "/share/classroom/public-token/klass-7a-share-frag"
    assert result.artifact.public_path == "/share/classroom/public-token/klass-7a-share-frag"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authenticated_share_requires_owner_and_revision() -> None:
    handler = _create_handler(
        shares=_FakeShareRepository(),
        now=datetime(2026, 4, 30, tzinfo=timezone.utc),
    )
    command = CreateClassroomPlannerShareArtifactCommand(
        source=ClassroomPlannerShareArtifactSource.AUTHENTICATED,
        draft_kind=PlanDraftKind.SEATING,
        title="Klass 7A",
        renderer_version="share-renderer-v1",
        presentation_schema_version="seating-share-v1",
        rendered_html="<main>Klass 7A</main>",
        rendered_css="main { color: black; }",
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(command=command)

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_guest_share_creation_requires_guest_controls() -> None:
    handler = _create_handler(
        shares=_FakeShareRepository(),
        now=datetime(2026, 4, 30, tzinfo=timezone.utc),
    )
    command = CreateClassroomPlannerShareArtifactCommand(
        source=ClassroomPlannerShareArtifactSource.PUBLIC_GUEST,
        draft_kind=PlanDraftKind.SEATING,
        title="Klass 7A",
        renderer_version="share-renderer-v1",
        presentation_schema_version="seating-share-v1",
        rendered_html="<main>Klass 7A</main>",
        rendered_css="main { color: black; }",
        expires_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(command=command)

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_guest_share_creation_rejects_source_provenance_ids() -> None:
    handler = _create_handler(
        shares=_FakeShareRepository(),
        now=datetime(2026, 4, 30, tzinfo=timezone.utc),
    )
    command = CreateClassroomPlannerShareArtifactCommand(
        source=ClassroomPlannerShareArtifactSource.PUBLIC_GUEST,
        draft_kind=PlanDraftKind.SEATING,
        roster_id=uuid4(),
        template_id=uuid4(),
        source_revision=1,
        guest_snapshot_fingerprint="sha256:fingerprint",
        client_operation_id="operation-123456789",
        public_revoke_secret="r" * 32,
        title="Klass 7A",
        renderer_version="share-renderer-v1",
        presentation_schema_version="seating-share-v1",
        rendered_html="<main>Klass 7A</main>",
        rendered_css="main { color: black; }",
        expires_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(command=command)

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_by_public_token_hashes_lookup_value() -> None:
    shares = _FakeShareRepository()
    artifact = ClassroomPlannerShareArtifact(
        id=uuid4(),
        token_hash=hash_share_token("public-token"),
        source=ClassroomPlannerShareArtifactSource.AUTHENTICATED,
        draft_kind=PlanDraftKind.GROUPING,
        owner_user_id=uuid4(),
        draft_id=uuid4(),
        roster_id=uuid4(),
        source_revision=1,
        title="Klass 7A",
        slug="klass-7a",
        renderer_version="share-renderer-v1",
        presentation_schema_version="grouping-share-v1",
        presentation_hash=build_share_presentation_hash(None),
        content_hash=build_share_content_hash(rendered_html="<main />", rendered_css="main {}"),
        rendered_html="<main />",
        rendered_css="main {}",
        created_at=datetime(2026, 4, 30, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 30, tzinfo=timezone.utc),
    )
    await shares.create(artifact=artifact)
    handler = GetClassroomPlannerShareArtifactByTokenHandler(shares=shares, uow=_DummyUow())

    result = await handler.handle(public_token="public-token")

    assert result == artifact
    assert shares.token_hashes_seen == [hash_share_token("public-token")]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_preview_asset_by_share_id_returns_generated_thumbnail() -> None:
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    shares = _FakeShareRepository()
    created = await _create_handler(shares=shares, now=now).handle(
        command=_command(
            owner_user_id=uuid4(),
            draft_id=uuid4(),
            roster_id=uuid4(),
        )
    )
    handler = GetClassroomPlannerSharePreviewAssetHandler(shares=shares, uow=_DummyUow())

    result = await handler.handle(share_id=created.artifact.id)

    assert result == shares.preview_assets_by_share_id[created.artifact.id]
    assert result.source_content_hash == created.artifact.content_hash


@pytest.mark.unit
@pytest.mark.asyncio
async def test_backfill_generates_missing_and_stale_preview_rows_only_for_active_shares() -> None:
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    shares = _FakeShareRepository()
    active_missing = _create_handler(shares=shares, now=now).build_unsaved(
        command=_command(owner_user_id=uuid4(), draft_id=uuid4(), roster_id=uuid4())
    )
    active_stale = _create_handler(shares=shares, now=now).build_unsaved(
        command=_command(owner_user_id=uuid4(), draft_id=uuid4(), roster_id=uuid4())
    )
    revoked = _create_handler(shares=shares, now=now).build_unsaved(
        command=_command(owner_user_id=uuid4(), draft_id=uuid4(), roster_id=uuid4())
    )
    shares.artifacts_by_id[active_missing.artifact.id] = active_missing.artifact
    shares.artifacts_by_id[active_stale.artifact.id] = active_stale.artifact
    shares.artifacts_by_id[revoked.artifact.id] = revoked.artifact.model_copy(
        update={"revoked_at": now}
    )
    shares.preview_assets_by_share_id[active_stale.artifact.id] = ClassroomPlannerSharePreviewAsset(
        share_id=active_stale.artifact.id,
        image_bytes=b"old",
        preview_content_hash=build_share_preview_content_hash(b"old"),
        source_content_hash="sha256:stale",
        presentation_hash=active_stale.artifact.presentation_hash,
        renderer_version=active_stale.artifact.renderer_version,
        generated_at=now,
        updated_at=now,
    )
    create_handler = _create_handler(shares=shares, now=now)
    backfill = BackfillClassroomPlannerSharePreviewsHandler(
        shares=shares,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        create_artifact=create_handler,
        renderer=_FakeShareRenderer(),
        current_seating_renderer_version="klassrumskartan-seating-share-renderer-v2",
    )

    result = await backfill.handle()

    assert result.scanned == 2
    assert result.generated == 2
    assert result.refreshed == 0
    assert result.failed_share_ids == ()
    assert (
        shares.preview_assets_by_share_id[active_missing.artifact.id].source_content_hash
        == active_missing.artifact.content_hash
    )
    assert (
        shares.preview_assets_by_share_id[active_stale.artifact.id].source_content_hash
        == active_stale.artifact.content_hash
    )
    assert revoked.artifact.id not in shares.preview_assets_by_share_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_backfill_refreshes_old_active_seating_artifact_before_preview() -> None:
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    shares = _FakeShareRepository()
    old_payload = _seating_presentation_payload()
    old_artifact = ClassroomPlannerShareArtifact(
        id=uuid4(),
        token_hash=hash_share_token("old-public-token"),
        source=ClassroomPlannerShareArtifactSource.AUTHENTICATED,
        draft_kind=PlanDraftKind.SEATING,
        owner_user_id=uuid4(),
        draft_id=uuid4(),
        roster_id=uuid4(),
        template_id=uuid4(),
        source_revision=4,
        title="Klass 8B - Sittschema",
        slug="klass-8b-sittschema",
        public_path="/share/classroom/old-public-token/klass-8b-sittschema",
        preview_description="Old preview",
        renderer_version="klassrumskartan-share-renderer-v1",
        presentation_schema_version="seating-share-v1",
        presentation_hash=build_share_presentation_hash(old_payload),
        content_hash=build_share_content_hash(
            rendered_html="<main>old seating</main>",
            rendered_css="main { color: black; }",
        ),
        presentation_payload=old_payload,
        rendered_html="<main>old seating</main>",
        rendered_css="main { color: black; }",
        created_at=now,
        updated_at=now,
    )
    shares.artifacts_by_id[old_artifact.id] = old_artifact
    shares.preview_assets_by_share_id[old_artifact.id] = ClassroomPlannerSharePreviewAsset(
        share_id=old_artifact.id,
        image_bytes=b"old",
        preview_content_hash=build_share_preview_content_hash(b"old"),
        source_content_hash=old_artifact.content_hash,
        presentation_hash=old_artifact.presentation_hash,
        renderer_version=old_artifact.renderer_version,
        generated_at=now,
        updated_at=now,
    )
    preview_renderer = _FakePreviewRenderer()
    backfill = BackfillClassroomPlannerSharePreviewsHandler(
        shares=shares,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        create_artifact=_create_handler(
            shares=shares,
            now=now,
            preview_renderer=preview_renderer,
        ),
        renderer=_FakeShareRenderer(),
        current_seating_renderer_version="klassrumskartan-seating-share-renderer-v2",
    )

    result = await backfill.handle()

    refreshed = shares.artifacts_by_id[old_artifact.id]
    preview = shares.preview_assets_by_share_id[old_artifact.id]
    assert result.scanned == 1
    assert result.generated == 1
    assert result.refreshed == 1
    assert refreshed.renderer_version == "klassrumskartan-seating-share-renderer-v2"
    assert refreshed.rendered_html != old_artifact.rendered_html
    assert refreshed.content_hash != old_artifact.content_hash
    assert 'data-skriptoteket-share-created-date="owned">2026-04-30</span>' in (
        refreshed.rendered_html
    )
    assert 'href="/share/classroom/old-public-token/download.pdf"' in refreshed.rendered_html
    assert preview.source_content_hash == refreshed.content_hash
    assert preview.renderer_version == refreshed.renderer_version
    assert preview_renderer.rendered_artifacts == [refreshed]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_and_revoke_are_owner_scoped() -> None:
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    owner_user_id = uuid4()
    draft_id = uuid4()
    shares = _FakeShareRepository()
    create_handler = _create_handler(
        shares=shares,
        now=now,
    )
    created = await create_handler.handle(
        command=_command(
            owner_user_id=owner_user_id,
            draft_id=draft_id,
            roster_id=uuid4(),
        )
    )
    list_handler = ListClassroomPlannerShareArtifactsHandler(shares=shares, uow=_DummyUow())
    revoke_handler = RevokeClassroomPlannerShareArtifactHandler(
        shares=shares,
        uow=_DummyUow(),
        clock=_FixedClock(now),
    )

    listed = await list_handler.handle(
        owner_user_id=owner_user_id,
        draft_id=draft_id,
        draft_kind=PlanDraftKind.GROUPING,
    )
    revoked = await revoke_handler.handle(
        share_id=created.artifact.id,
        owner_user_id=owner_user_id,
    )

    assert listed == [created.artifact]
    assert revoked.revoked_at == now
    with pytest.raises(DomainError) as exc_info:
        await revoke_handler.handle(share_id=created.artifact.id, owner_user_id=uuid4())
    assert exc_info.value.code is ErrorCode.NOT_FOUND


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lifecycle_service_revokes_and_detaches_deleted_source_ids() -> None:
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    owner_user_id = uuid4()
    draft_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    shares = _FakeShareRepository()
    created = await _create_handler(
        shares=shares,
        now=now,
    ).handle(
        command=_command(
            owner_user_id=owner_user_id,
            draft_id=draft_id,
            roster_id=roster_id,
        ).model_copy(update={"template_id": template_id})
    )
    lifecycle = ClassroomPlannerShareLifecycleService(shares=shares, clock=_FixedClock(now))

    count = await lifecycle.revoke_for_draft_delete(
        owner_user_id=owner_user_id,
        draft_id=draft_id,
        draft_kind=PlanDraftKind.GROUPING,
    )

    artifact = shares.artifacts_by_id[created.artifact.id]
    assert count == 1
    assert artifact.revoked_at == now
    assert artifact.draft_id is None
    assert artifact.roster_id == roster_id
    assert artifact.template_id == template_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_owner_lifecycle_revokes_and_detaches_owner_provenance() -> None:
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    owner_user_id = uuid4()
    shares = _FakeShareRepository()
    created = await _create_handler(
        shares=shares,
        now=now,
    ).handle(
        command=_command(
            owner_user_id=owner_user_id,
            draft_id=uuid4(),
            roster_id=uuid4(),
        )
    )
    lifecycle = ClassroomPlannerShareLifecycleService(shares=shares, clock=_FixedClock(now))

    count = await lifecycle.revoke_for_owner_delete(owner_user_id=owner_user_id)

    artifact = shares.artifacts_by_id[created.artifact.id]
    assert count == 1
    assert artifact.revoked_at == now
    assert artifact.owner_user_id is None
    assert artifact.draft_id is None
    assert artifact.roster_id is None
    assert artifact.template_id is None
