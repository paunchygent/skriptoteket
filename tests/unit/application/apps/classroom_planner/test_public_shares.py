"""Application tests for Klassrumskartan public guest share handlers.

Purpose:
    Lock the PR-0273 public guest share helper semantics: anonymous artifacts
    stay ownerless, expire within policy, reuse browser idempotency keys, and
    supersede previous links only through browser-held revoke secrets.

Relationships:
    - Exercises the public guest share creation helper with an in-memory
      repository fake.
    - Complements route tests that prove the public helper boundary remains
      cookie-agnostic.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import (
    CreateClassroomPlannerShareArtifactHandler,
    PublicGuestSharePolicy,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.public_shares import (
    RevokePublicGuestShareHandler,
    _create_public_guest_share,
)
from skriptoteket.application.curated_apps.classroom_planner.public_share_contracts import (
    PublicGuestShareRequest,
    PublicGuestShareResult,
    PublicGuestShareRevokeRequest,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    SHARE_CREATED_DATE_CHROME_SLOT,
    SHARE_PDF_DOWNLOAD_HREF_CHROME_SLOT,
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactSource,
    ClassroomPlannerSharePreviewAsset,
    PublicGuestSharePersistenceResult,
    build_share_content_hash,
    build_share_presentation_hash,
    hash_share_revoke_secret,
    hash_share_token,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.application.apps.classroom_planner.test_public_export_handlers import _snapshot


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
    def __init__(self, values: list[UUID]) -> None:
        self._values = values

    def new_uuid(self) -> UUID:
        return self._values.pop(0)


class _FixedTokenGenerator:
    def __init__(self, values: list[str]) -> None:
        self._values = values

    def new_token(self) -> str:
        return self._values.pop(0)


class _FakePreviewRenderer:
    async def render_png(self, *, artifact: ClassroomPlannerShareArtifact) -> bytes:
        del artifact
        return b"\x89PNG\r\npreview"


class _FakeShareRepository:
    def __init__(self) -> None:
        self.artifacts_by_id: dict[UUID, ClassroomPlannerShareArtifact] = {}
        self.preview_assets_by_share_id: dict[UUID, ClassroomPlannerSharePreviewAsset] = {}
        self._lock = asyncio.Lock()

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

    async def get_by_token_hash(self, *, token_hash: str) -> ClassroomPlannerShareArtifact | None:
        return next(
            (
                artifact
                for artifact in self.artifacts_by_id.values()
                if artifact.token_hash == token_hash
            ),
            None,
        )

    async def list_for_owner_draft(self, **_kwargs: object) -> list[ClassroomPlannerShareArtifact]:
        return []

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

    async def list_active_shares_missing_or_stale_preview(
        self,
        *,
        now: datetime,
        limit: int | None,
    ) -> list[ClassroomPlannerShareArtifact]:
        del now, limit
        return []

    async def revoke_owned(self, **_kwargs: object) -> ClassroomPlannerShareArtifact | None:
        return None

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
                if artifact.token_hash == token_hash
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
        async with self._lock:
            existing = await self.get_public_guest_by_client_operation_id(
                client_operation_id=artifact.client_operation_id or ""
            )
            if existing is not None:
                return PublicGuestSharePersistenceResult(
                    artifact=existing,
                    preview_asset=self.preview_assets_by_share_id.get(existing.id),
                    reused_client_operation=True,
                )

            previous = None
            if previous_token_hash and previous_revoke_secret_hash:
                previous_any = next(
                    (
                        item
                        for item in self.artifacts_by_id.values()
                        if item.token_hash == previous_token_hash
                        and item.revoke_secret_hash == previous_revoke_secret_hash
                    ),
                    None,
                )
                if previous_any is not None and previous_any.revoked_at is not None:
                    return PublicGuestSharePersistenceResult(
                        artifact=None,
                        previous_already_superseded=True,
                    )
                if previous_any is not None and (
                    previous_any.expires_at is None or previous_any.expires_at > now
                ):
                    previous = previous_any

            active_count = await self.count_active_public_guest_shares(
                guest_snapshot_fingerprint=artifact.guest_snapshot_fingerprint or "",
                now=now,
            )
            if active_count >= max_active_per_snapshot and previous is None:
                return PublicGuestSharePersistenceResult(
                    artifact=None,
                    active_limit_exceeded=True,
                )

            created = await self.create_with_preview(
                artifact=artifact,
                preview_asset=preview_asset,
            )
            superseded_previous = False
            if previous is not None:
                revoked = previous.model_copy(update={"revoked_at": now, "updated_at": now})
                self.artifacts_by_id[previous.id] = revoked
                superseded_previous = True
            return PublicGuestSharePersistenceResult(
                artifact=created,
                preview_asset=preview_asset,
                superseded_previous=superseded_previous,
            )

    async def purge_expired_public_guest_shares(self, *, now: datetime) -> int:
        return self._revoke_matching(
            predicate=lambda artifact: (
                artifact.source is ClassroomPlannerShareArtifactSource.PUBLIC_GUEST
                and artifact.expires_at is not None
                and artifact.expires_at <= now
            ),
            revoked_at=now,
        )

    async def revoke_for_draft_lifecycle(self, **_kwargs: object) -> int:
        return 0

    async def revoke_for_roster_lifecycle(self, **_kwargs: object) -> int:
        return 0

    async def revoke_for_template_lifecycle(self, **_kwargs: object) -> int:
        return 0

    async def revoke_for_owner_lifecycle(self, **_kwargs: object) -> int:
        return 0

    def _revoke_matching(
        self,
        *,
        predicate: Callable[[ClassroomPlannerShareArtifact], bool],
        revoked_at: datetime,
    ) -> int:
        count = 0
        for share_id, artifact in list(self.artifacts_by_id.items()):
            if not predicate(artifact):
                continue
            self.artifacts_by_id[share_id] = artifact.model_copy(
                update={"revoked_at": revoked_at, "updated_at": revoked_at}
            )
            count += 1
        return count


def _artifact(
    *,
    token: str,
    revoke_secret: str,
    client_operation_id: str,
    fingerprint: str,
    created_at: datetime,
) -> ClassroomPlannerShareArtifact:
    return ClassroomPlannerShareArtifact(
        id=uuid4(),
        token_hash=hash_share_token(token),
        source=ClassroomPlannerShareArtifactSource.PUBLIC_GUEST,
        draft_kind=PlanDraftKind.GROUPING,
        source_revision=4,
        guest_snapshot_fingerprint=fingerprint,
        client_operation_id=client_operation_id,
        revoke_secret_hash=hash_share_revoke_secret(revoke_secret),
        title="Klass 7A",
        slug="klass-7a",
        public_path=f"/share/classroom/{token}/klass-7a",
        renderer_version="klassrumskartan-share-renderer-v1",
        presentation_schema_version="grouping-share-v1",
        presentation_hash=build_share_presentation_hash({"title": "Klass 7A"}),
        content_hash=build_share_content_hash(rendered_html="<main />", rendered_css="main {}"),
        presentation_payload={"title": "Klass 7A"},
        rendered_html="<main />",
        rendered_css="main {}",
        created_at=created_at,
        updated_at=created_at,
        expires_at=created_at.replace(month=6),
    )


def _request(
    *,
    client_operation_id: str = "operation-123456789",
    revoke_secret: str = "r" * 32,
    previous_public_path: str | None = None,
    previous_revoke_secret: str | None = None,
) -> PublicGuestShareRequest:
    return PublicGuestShareRequest(
        snapshot=_snapshot(),
        expected_revision=4,
        client_operation_id=client_operation_id,
        revoke_secret=revoke_secret,
        previous_public_path=previous_public_path,
        previous_revoke_secret=previous_revoke_secret,
    )


async def _create_share(
    *,
    shares: _FakeShareRepository,
    request: PublicGuestShareRequest,
    policy: PublicGuestSharePolicy | None = None,
    rendered_html: str | None = None,
    token: str = "public-token",
) -> PublicGuestShareResult:
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    create_artifact = CreateClassroomPlannerShareArtifactHandler(
        shares=shares,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator([uuid4()]),
        token_generator=_FixedTokenGenerator([token]),
        preview_renderer=_FakePreviewRenderer(),
    )
    return await _create_public_guest_share(
        shares=shares,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        policy=policy
        or PublicGuestSharePolicy(
            ttl_days=60,
            max_rendered_bytes=750_000,
            max_active_per_snapshot=3,
        ),
        create_artifact=create_artifact,
        request=request,
        draft_kind=PlanDraftKind.GROUPING,
        source_revision=4,
        title="Klass 7A",
        preview_description="Frozen grouping plan",
        renderer_version="klassrumskartan-share-renderer-v1",
        presentation_schema_version="grouping-share-v1",
        presentation_payload={"title": "Klass 7A"},
        rendered_html=rendered_html or _share_html_with_owned_chrome("Klass 7A"),
        rendered_css="main { color: black; }",
    )


def _share_html_with_owned_chrome(content: str) -> str:
    return "\n".join(
        [
            "<main>",
            f'<p class="share-created">Skapad: {SHARE_CREATED_DATE_CHROME_SLOT}</p>',
            f"<a {SHARE_PDF_DOWNLOAD_HREF_CHROME_SLOT}>Ladda ner PDF</a>",
            f"<section>{content}</section>",
            "</main>",
        ]
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_guest_share_creates_ownerless_expiring_artifact() -> None:
    shares = _FakeShareRepository()

    result = await _create_share(shares=shares, request=_request())

    artifact = result.artifact
    assert artifact.source is ClassroomPlannerShareArtifactSource.PUBLIC_GUEST
    assert artifact.owner_user_id is None
    assert artifact.draft_id is None
    assert artifact.roster_id is None
    assert artifact.expires_at == datetime(2026, 6, 29, tzinfo=timezone.utc)
    assert artifact.revoke_secret_hash == hash_share_revoke_secret("r" * 32)
    assert result.public_revoke_secret == "r" * 32
    assert result.public_path == "/share/classroom/public-token/klass-7a"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_guest_share_reuses_client_operation_id() -> None:
    shares = _FakeShareRepository()
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    existing = _artifact(
        token="old-token",
        revoke_secret="r" * 32,
        client_operation_id="operation-123456789",
        fingerprint="sha256:fingerprint",
        created_at=now,
    )
    await shares.create(artifact=existing)

    result = await _create_share(shares=shares, request=_request())

    assert result.artifact == existing
    assert result.reused_client_operation is True
    assert len(shares.artifacts_by_id) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_guest_share_supersedes_previous_when_secret_matches() -> None:
    shares = _FakeShareRepository()
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    existing = _artifact(
        token="old-token",
        revoke_secret="previous-secret-value-1234567890",
        client_operation_id="previous-operation-1234",
        fingerprint="sha256:fingerprint",
        created_at=now,
    )
    await shares.create(artifact=existing)

    result = await _create_share(
        shares=shares,
        request=_request(
            previous_public_path="/share/classroom/old-token/klass-7a",
            previous_revoke_secret="previous-secret-value-1234567890",
        ),
    )

    assert result.superseded_previous is True
    assert shares.artifacts_by_id[existing.id].revoked_at == now


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_guest_revoke_removes_current_browser_owned_link() -> None:
    shares = _FakeShareRepository()
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    existing = _artifact(
        token="old-token",
        revoke_secret="browser-secret-value-1234567890x",
        client_operation_id="previous-operation-1234",
        fingerprint="sha256:fingerprint",
        created_at=now,
    )
    await shares.create(artifact=existing)
    handler = RevokePublicGuestShareHandler(
        shares=shares,
        uow=_DummyUow(),
        clock=_FixedClock(now),
    )

    result = await handler.handle(
        request=PublicGuestShareRevokeRequest(
            public_path="/share/classroom/old-token/klass-7a",
            revoke_secret="browser-secret-value-1234567890x",
        )
    )

    assert result.artifact.id == existing.id
    assert result.artifact.revoked_at == now
    assert shares.artifacts_by_id[existing.id].revoked_at == now


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_guest_revoke_rejects_invalid_secret_without_revoking() -> None:
    shares = _FakeShareRepository()
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    existing = _artifact(
        token="old-token",
        revoke_secret="browser-secret-value-1234567890x",
        client_operation_id="previous-operation-1234",
        fingerprint="sha256:fingerprint",
        created_at=now,
    )
    await shares.create(artifact=existing)
    handler = RevokePublicGuestShareHandler(
        shares=shares,
        uow=_DummyUow(),
        clock=_FixedClock(now),
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            request=PublicGuestShareRevokeRequest(
                public_path="/share/classroom/old-token/klass-7a",
                revoke_secret="w" * 32,
            )
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert shares.artifacts_by_id[existing.id].revoked_at is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_guest_revoke_rejects_non_share_path() -> None:
    handler = RevokePublicGuestShareHandler(
        shares=_FakeShareRepository(),
        uow=_DummyUow(),
        clock=_FixedClock(datetime(2026, 4, 30, tzinfo=timezone.utc)),
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            request=PublicGuestShareRevokeRequest(
                public_path="/not/a/share",
                revoke_secret="browser-secret-value-1234567890x",
            )
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_guest_share_enforces_rendered_size_cap() -> None:
    shares = _FakeShareRepository()

    with pytest.raises(DomainError) as exc_info:
        await _create_share(
            shares=shares,
            request=_request(),
            policy=PublicGuestSharePolicy(
                ttl_days=60,
                max_rendered_bytes=4,
                max_active_per_snapshot=3,
            ),
        )

    assert exc_info.value.code is ErrorCode.PAYLOAD_TOO_LARGE


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_guest_share_concurrent_same_client_operation_reuses_existing() -> None:
    shares = _FakeShareRepository()
    request = _request()

    first, second = await asyncio.gather(
        _create_share(shares=shares, request=request, token="public-token-1"),
        _create_share(shares=shares, request=request, token="public-token-2"),
    )

    assert first.artifact.id == second.artifact.id
    assert {first.reused_client_operation, second.reused_client_operation} == {False, True}
    assert len(shares.artifacts_by_id) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_guest_share_concurrent_supersede_allows_only_one_newest_link() -> None:
    shares = _FakeShareRepository()
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    existing = _artifact(
        token="old-token",
        revoke_secret="previous-secret-value-1234567890",
        client_operation_id="previous-operation-1234",
        fingerprint="sha256:fingerprint",
        created_at=now,
    )
    await shares.create(artifact=existing)

    results = await asyncio.gather(
        _create_share(
            shares=shares,
            request=_request(
                client_operation_id="operation-123456789",
                previous_public_path="/share/classroom/old-token/klass-7a",
                previous_revoke_secret="previous-secret-value-1234567890",
            ),
            token="public-token-1",
        ),
        _create_share(
            shares=shares,
            request=_request(
                client_operation_id="operation-abcdefghi",
                previous_public_path="/share/classroom/old-token/klass-7a",
                previous_revoke_secret="previous-secret-value-1234567890",
            ),
            token="public-token-2",
        ),
        return_exceptions=True,
    )

    created = [result for result in results if isinstance(result, PublicGuestShareResult)]
    conflicts = [result for result in results if isinstance(result, DomainError)]
    assert len(created) == 1
    assert created[0].superseded_previous is True
    assert len(conflicts) == 1
    assert conflicts[0].code is ErrorCode.CONFLICT
    assert shares.artifacts_by_id[existing.id].revoked_at == now
    active_new_links = [
        artifact
        for artifact in shares.artifacts_by_id.values()
        if artifact.id != existing.id and artifact.revoked_at is None
    ]
    assert len(active_new_links) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_guest_share_concurrent_active_limit_allows_one_create() -> None:
    shares = _FakeShareRepository()
    policy = PublicGuestSharePolicy(
        ttl_days=60,
        max_rendered_bytes=750_000,
        max_active_per_snapshot=1,
    )

    results = await asyncio.gather(
        _create_share(
            shares=shares,
            request=_request(client_operation_id="operation-123456789"),
            policy=policy,
            token="public-token-1",
        ),
        _create_share(
            shares=shares,
            request=_request(client_operation_id="operation-abcdefghi"),
            policy=policy,
            token="public-token-2",
        ),
        return_exceptions=True,
    )

    created = [result for result in results if isinstance(result, PublicGuestShareResult)]
    limited = [result for result in results if isinstance(result, DomainError)]
    assert len(created) == 1
    assert len(limited) == 1
    assert limited[0].code is ErrorCode.TOO_MANY_REQUESTS
    assert len(shares.artifacts_by_id) == 1
