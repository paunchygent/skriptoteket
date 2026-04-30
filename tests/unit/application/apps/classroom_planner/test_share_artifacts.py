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
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactSource,
    ClassroomPlannerShareLifecycleService,
    CreateClassroomPlannerShareArtifactCommand,
    CreateClassroomPlannerShareArtifactHandler,
    GetClassroomPlannerShareArtifactByTokenHandler,
    ListClassroomPlannerShareArtifactsHandler,
    RevokeClassroomPlannerShareArtifactHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    build_share_content_hash,
    build_share_presentation_hash,
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


class _FakeShareRepository:
    def __init__(self) -> None:
        self.artifacts_by_id: dict[UUID, ClassroomPlannerShareArtifact] = {}
        self.token_hashes_seen: list[str] = []

    async def create(
        self,
        *,
        artifact: ClassroomPlannerShareArtifact,
    ) -> ClassroomPlannerShareArtifact:
        self.artifacts_by_id[artifact.id] = artifact
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
        rendered_html="<main>Klass 7A</main>",
        rendered_css="main { color: black; }",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_share_artifact_hashes_public_token_and_content() -> None:
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    share_id = uuid4()
    owner_user_id = uuid4()
    draft_id = uuid4()
    roster_id = uuid4()
    shares = _FakeShareRepository()
    handler = CreateClassroomPlannerShareArtifactHandler(
        shares=shares,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator(share_id),
        token_generator=_FixedTokenGenerator("public-token"),
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
    assert artifact.expires_at is None
    assert shares.artifacts_by_id[share_id] == artifact


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_share_artifact_normalizes_custom_slug() -> None:
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    handler = CreateClassroomPlannerShareArtifactHandler(
        shares=_FakeShareRepository(),
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator(uuid4()),
        token_generator=_FixedTokenGenerator("public-token"),
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
    handler = CreateClassroomPlannerShareArtifactHandler(
        shares=_FakeShareRepository(),
        uow=_DummyUow(),
        clock=_FixedClock(datetime(2026, 4, 30, tzinfo=timezone.utc)),
        id_generator=_FixedIdGenerator(uuid4()),
        token_generator=_FixedTokenGenerator("public-token"),
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
async def test_public_guest_share_creation_waits_for_dedicated_helper_path() -> None:
    handler = CreateClassroomPlannerShareArtifactHandler(
        shares=_FakeShareRepository(),
        uow=_DummyUow(),
        clock=_FixedClock(datetime(2026, 4, 30, tzinfo=timezone.utc)),
        id_generator=_FixedIdGenerator(uuid4()),
        token_generator=_FixedTokenGenerator("public-token"),
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
    assert "PR-0273" in exc_info.value.message


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
async def test_list_and_revoke_are_owner_scoped() -> None:
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    owner_user_id = uuid4()
    draft_id = uuid4()
    shares = _FakeShareRepository()
    create_handler = CreateClassroomPlannerShareArtifactHandler(
        shares=shares,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator(uuid4()),
        token_generator=_FixedTokenGenerator("public-token"),
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
    created = await CreateClassroomPlannerShareArtifactHandler(
        shares=shares,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator(uuid4()),
        token_generator=_FixedTokenGenerator("public-token"),
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
    created = await CreateClassroomPlannerShareArtifactHandler(
        shares=shares,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator(uuid4()),
        token_generator=_FixedTokenGenerator("public-token"),
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
