"""One editing tab: the server edit lease, the tab guard, and the lease routes."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.routing import APIRoute

from skriptoteket.application.curated_apps.exam_workspace_history import (
    MoveExamWorkspaceHistoryPositionRequest,
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.application.curated_apps.exam_workspace_parents import (
    CreateEmptyExamPartRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_change_type import (
    ChangeExamWorkspaceItemTypeHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_edit_lease import (
    EDIT_LEASE_HEARTBEAT_INTERVAL_SECONDS,
    EDIT_LEASE_TTL_SECONDS,
    ExamWorkspaceEditLeaseHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_parents import (
    ExamWorkspaceParentsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_undo_steps import (
    StoreExamWorkspaceUndoStepHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.exam_workspace_change_type import (
    ChangeExamWorkspaceItemTypeRequest,
)
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace as documents_api
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    SequenceIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
)

_NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


class MutableClock:
    """An advancing test clock, so expiry is deterministic without sleeping."""

    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, *, seconds: int) -> None:
        self._now += timedelta(seconds=seconds)


def _lease_handler(env: _Env, clock: MutableClock) -> ExamWorkspaceEditLeaseHandler:
    return ExamWorkspaceEditLeaseHandler(vault_files=env.vault_files, store=env.store, clock=clock)


def _undo_handler(env: _Env, clock: MutableClock) -> StoreExamWorkspaceUndoStepHandler:
    return StoreExamWorkspaceUndoStepHandler(
        vault_files=env.vault_files,
        codec=env.codec,
        store=env.store,
        jobs=env.enrichment_jobs,
        id_generator=SequenceIdGenerator([uuid4() for _ in range(100)]),
        clock=clock,
    )


async def _seeded(env: _Env, actor: User) -> tuple[UUID, NativeExamDocument]:
    imported = await env.seed_document(actor=actor)
    return imported.summary.lineage_id, imported.document


async def _cursor(env: _Env, actor: User, lineage: UUID) -> UUID:
    return (await env.save_handler.history(actor=actor, lineage_id=lineage)).cursor


async def _file_bytes(env: _Env, actor: User, lineage: UUID) -> bytes:
    head = next(
        file
        for file in env.vault_files.files.values()
        if file.document_lineage_id == lineage and file.export_format is None
    )
    return await env.store.load(actor=actor, vault_file=head)


@pytest.mark.asyncio
async def test_claim_with_no_lease_succeeds_and_names_the_tab() -> None:
    assert EDIT_LEASE_TTL_SECONDS == 15
    assert EDIT_LEASE_HEARTBEAT_INTERVAL_SECONDS == 5
    env, actor, clock = _Env(), _actor(), MutableClock(_NOW)
    lineage, _ = await _seeded(env, actor)
    tab = uuid4()

    claimed = await _lease_handler(env, clock).claim(actor=actor, lineage_id=lineage, tab_id=tab)

    assert claimed.holder_tab_id == tab
    assert claimed.renewed_at == _NOW
    assert claimed.takeover_requested is False


@pytest.mark.asyncio
async def test_second_tab_claim_fails_while_first_renews() -> None:
    env, actor, clock = _Env(), _actor(), MutableClock(_NOW)
    lineage, _ = await _seeded(env, actor)
    first, second = uuid4(), uuid4()
    leases = _lease_handler(env, clock)
    await leases.claim(actor=actor, lineage_id=lineage, tab_id=first)

    clock.advance(seconds=EDIT_LEASE_TTL_SECONDS - 1)
    await leases.renew(actor=actor, lineage_id=lineage, tab_id=first)
    with pytest.raises(DomainError) as error:
        await leases.claim(actor=actor, lineage_id=lineage, tab_id=second)

    assert error.value.code is ErrorCode.EDIT_LEASE_HELD


@pytest.mark.asyncio
async def test_second_tab_claim_succeeds_after_the_lease_dies() -> None:
    env, actor, clock = _Env(), _actor(), MutableClock(_NOW)
    lineage, _ = await _seeded(env, actor)
    first, second = uuid4(), uuid4()
    leases = _lease_handler(env, clock)
    await leases.claim(actor=actor, lineage_id=lineage, tab_id=first)

    clock.advance(seconds=EDIT_LEASE_TTL_SECONDS)
    claimed = await leases.claim(actor=actor, lineage_id=lineage, tab_id=second)

    assert claimed.holder_tab_id == second


@pytest.mark.asyncio
async def test_renew_reports_a_pending_takeover() -> None:
    env, actor, clock = _Env(), _actor(), MutableClock(_NOW)
    lineage, _ = await _seeded(env, actor)
    holder, waiter = uuid4(), uuid4()
    leases = _lease_handler(env, clock)
    await leases.claim(actor=actor, lineage_id=lineage, tab_id=holder)
    await leases.request_takeover(actor=actor, lineage_id=lineage, tab_id=waiter)

    renewed = await leases.renew(actor=actor, lineage_id=lineage, tab_id=holder)

    assert renewed.takeover_requested is True
    assert renewed.takeover_requested_by == waiter


@pytest.mark.asyncio
async def test_release_lets_the_requester_claim_at_once() -> None:
    env, actor, clock = _Env(), _actor(), MutableClock(_NOW)
    lineage, _ = await _seeded(env, actor)
    holder, waiter = uuid4(), uuid4()
    leases = _lease_handler(env, clock)
    await leases.claim(actor=actor, lineage_id=lineage, tab_id=holder)
    await leases.request_takeover(actor=actor, lineage_id=lineage, tab_id=waiter)
    await leases.release(actor=actor, lineage_id=lineage, tab_id=holder)

    claimed = await leases.claim(actor=actor, lineage_id=lineage, tab_id=waiter)

    assert claimed.holder_tab_id == waiter
    assert claimed.takeover_requested is False


@pytest.mark.asyncio
async def test_release_by_a_tab_without_the_lease_is_a_lease_conflict() -> None:
    env, actor, clock = _Env(), _actor(), MutableClock(_NOW)
    lineage, _ = await _seeded(env, actor)
    leases = _lease_handler(env, clock)
    await leases.claim(actor=actor, lineage_id=lineage, tab_id=uuid4())

    with pytest.raises(DomainError) as error:
        await leases.release(actor=actor, lineage_id=lineage, tab_id=uuid4())

    assert error.value.code is ErrorCode.EDIT_LEASE_HELD


@pytest.mark.asyncio
async def test_store_without_the_lease_is_refused_and_writes_nothing() -> None:
    env, actor, clock = _Env(), _actor(), MutableClock(_NOW)
    lineage, document = await _seeded(env, actor)
    before_bytes = await _file_bytes(env, actor, lineage)
    before = await env.save_handler.history(actor=actor, lineage_id=lineage)

    with pytest.raises(DomainError) as error:
        await _undo_handler(env, clock).handle(
            actor=actor,
            lineage_id=lineage,
            request=StoreExamWorkspaceUndoStepRequest(
                expected_cursor=before.cursor,
                document=document.model_copy(update={"title": "Tyst överskrivning"}),
                tab_id=uuid4(),
            ),
        )

    assert error.value.code is ErrorCode.EDIT_LEASE_HELD
    assert await _file_bytes(env, actor, lineage) == before_bytes
    assert await env.save_handler.history(actor=actor, lineage_id=lineage) == before


@pytest.mark.asyncio
async def test_move_without_the_lease_is_refused_and_writes_nothing() -> None:
    env, actor, clock = _Env(), _actor(), MutableClock(_NOW)
    lineage, document = await _seeded(env, actor)
    holder = uuid4()
    leases = _lease_handler(env, clock)
    await leases.claim(actor=actor, lineage_id=lineage, tab_id=holder)
    stored = await _undo_handler(env, clock).handle(
        actor=actor,
        lineage_id=lineage,
        request=StoreExamWorkspaceUndoStepRequest(
            expected_cursor=await _cursor(env, actor, lineage),
            document=document.model_copy(update={"title": "Hållarens text"}),
            tab_id=holder,
        ),
    )
    before_bytes = await _file_bytes(env, actor, lineage)

    with pytest.raises(DomainError) as error:
        await _undo_handler(env, clock).move_to_step(
            actor=actor,
            lineage_id=lineage,
            request=MoveExamWorkspaceHistoryPositionRequest(
                expected_cursor=stored.history.cursor,
                step_id=stored.history.step_ids[0],
                tab_id=uuid4(),
            ),
        )

    assert error.value.code is ErrorCode.EDIT_LEASE_HELD
    assert await _file_bytes(env, actor, lineage) == before_bytes
    assert (
        await env.save_handler.history(actor=actor, lineage_id=lineage)
    ).position_step_id == stored.history.position_step_id


@pytest.mark.asyncio
async def test_parent_command_without_the_lease_is_refused_and_writes_nothing() -> None:
    env, actor, clock = _Env(), _actor(), MutableClock(_NOW)
    lineage, _ = await _seeded(env, actor)
    parents = ExamWorkspaceParentsHandler(
        reader=env.get_handler, undo_steps=_undo_handler(env, clock)
    )
    before_bytes = await _file_bytes(env, actor, lineage)
    before = await env.save_handler.history(actor=actor, lineage_id=lineage)

    with pytest.raises(DomainError) as error:
        await parents.create_empty_part(
            actor=actor,
            lineage_id=lineage,
            request=CreateEmptyExamPartRequest(
                expected_cursor=before.cursor, position=0, tab_id=uuid4()
            ),
        )

    assert error.value.code is ErrorCode.EDIT_LEASE_HELD
    assert await _file_bytes(env, actor, lineage) == before_bytes
    assert await env.save_handler.history(actor=actor, lineage_id=lineage) == before


@pytest.mark.asyncio
async def test_change_type_without_the_lease_is_refused_and_writes_nothing() -> None:
    env, actor, clock = _Env(), _actor(), MutableClock(_NOW)
    lineage, _ = await _seeded(env, actor)
    changer = ChangeExamWorkspaceItemTypeHandler(
        reader=env.get_handler,
        undo_steps=_undo_handler(env, clock),
        rng=__import__("random").Random(0),
    )
    reopened = await env.get_handler.handle(actor=actor, lineage_id=lineage)
    before_bytes = await _file_bytes(env, actor, lineage)
    before = await env.save_handler.history(actor=actor, lineage_id=lineage)

    with pytest.raises(DomainError) as error:
        await changer.handle(
            actor=actor,
            lineage_id=lineage,
            request=ChangeExamWorkspaceItemTypeRequest(
                item_id=reopened.document.items[0].item_id,
                target_kind=NativeExamItemKind.FREE_TEXT,
                expected_revision=reopened.document.revision,
                expected_cursor=before.cursor,
                tab_id=uuid4(),
            ),
        )

    assert error.value.code is ErrorCode.EDIT_LEASE_HELD
    assert await _file_bytes(env, actor, lineage) == before_bytes
    assert await env.save_handler.history(actor=actor, lineage_id=lineage) == before


def test_the_edit_lease_routes_are_registered() -> None:
    routes = {
        (route.path, next(iter(route.methods or ())))
        for route in documents_api.router.routes
        if isinstance(route, APIRoute)
    }
    base = "/api/v1/apps/documents.conversion_hub/exam-workspace/documents/{lineage_id}"
    for action in ("claim", "renew", "takeover", "release"):
        assert (f"{base}/edit-lease/{action}", "POST") in routes


def test_the_lease_conflict_maps_to_409() -> None:
    from skriptoteket.web.error_mapping import error_to_status

    assert error_to_status(ErrorCode.EDIT_LEASE_HELD) == 409
