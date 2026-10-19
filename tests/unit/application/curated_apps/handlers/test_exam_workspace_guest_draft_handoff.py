"""Sign-in guest-draft handoff: the compensated store owns the outermost commit.

Failure contract (F7):
    When the outermost COMMIT fails, the already-written exam payload must be
    deleted (compensation requested) and the error must propagate. A successful
    handoff writes exactly once; a repeated claim for the same
    ``(owner, draft_id)`` returns the first lineage without creating anything.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_guest_draft_handoff import (
    ImportGuestExamDraftHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_blank import (
    blank_native_exam_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _NOW,
    FakeUow,
    _actor,
    _Env,
    _settings,
)


class FailOutermostCommit:
    """Fail the outermost ``async with`` exit without an active exception.

    The handler and the store share one instance, like the request-scoped UoW:
    a raw outer UoW around ``store.save`` releases the store's guard before the
    outer COMMIT, while the compensated envelope keeps it through that commit.
    """

    def __init__(self) -> None:
        self.depth = 0

    async def __aenter__(self) -> FailOutermostCommit:
        self.depth += 1
        return self

    async def __aexit__(self, *args: object) -> None:
        self.depth -= 1
        if self.depth == 0 and args[0] is None:
            raise RuntimeError("simulated outermost COMMIT failure")
        return None


class InMemoryGuestDraftHandoffs:
    """Ledger double with the real claim semantics minus database blocking."""

    def __init__(self) -> None:
        self.rows: dict[tuple[UUID, UUID], UUID] = {}

    async def claim(
        self, *, owner_user_id: UUID, draft_id: UUID, lineage_id: UUID, now: datetime
    ) -> bool:
        key = (owner_user_id, draft_id)
        if key in self.rows:
            return False
        self.rows[key] = lineage_id
        return True

    async def get_lineage(self, *, owner_user_id: UUID, draft_id: UUID) -> UUID | None:
        return self.rows.get((owner_user_id, draft_id))


def _handler(env: _Env, uow: UnitOfWorkProtocol) -> ImportGuestExamDraftHandler:
    store = ExamWorkspaceDocumentStore(
        vault_files=env.vault_files,
        vault_usage=env.vault_usage,
        vault_storage=env.vault_storage,
        uow=uow,
        clock=FixedClock(_NOW),
        settings=_settings(),
        index=env.index,
        codec=env.codec,
    )
    reader = GetExamWorkspaceDocumentHandler(
        vault_files=env.vault_files,
        codec=env.codec,
        store=store,
        jobs=env.enrichment_jobs,
        uow=uow,
    )
    return ImportGuestExamDraftHandler(
        handoffs=InMemoryGuestDraftHandoffs(),
        reader=reader,
        codec=env.codec,
        store=store,
        clock=FixedClock(_NOW),
        id_generator=env.ids,
        index=env.index,
    )


def _guest_document(title: str) -> NativeExamDocument:
    return blank_native_exam_document().model_copy(update={"title": title})


async def test_handoff_outer_commit_failure_compensates_the_written_payload() -> None:
    env = _Env()
    actor = _actor()
    handler = _handler(env, FailOutermostCommit())
    document = _guest_document("Omprov: grammatik")

    try:
        await handler.handle(
            actor=actor, draft_id=uuid4(), document=document, assets_by_id={}, notes=()
        )
    except RuntimeError as exc:
        assert str(exc) == "simulated outermost COMMIT failure"
    else:
        raise AssertionError("the outermost COMMIT failure must propagate")

    assert len(env.vault_storage.stored) == 1
    (owner_id, file_id), _content = next(iter(env.vault_storage.stored.items()))
    assert owner_id == actor.id
    assert env.vault_storage.deleted == [(actor.id, file_id)]


async def test_handoff_writes_once_and_repeat_claim_returns_the_first_lineage() -> None:
    env = _Env()
    actor = _actor()
    handler = _handler(env, FakeUow())
    draft_id = uuid4()

    first = await handler.handle(
        actor=actor,
        draft_id=draft_id,
        document=_guest_document("Omprov: grammatik"),
        assets_by_id={},
        notes=(),
    )
    assert first.summary.version == 1
    assert first.document.title == "Omprov: grammatik"

    again = await handler.handle(
        actor=actor,
        draft_id=draft_id,
        document=_guest_document("Annat"),
        assets_by_id={},
        notes=(),
    )

    assert again.summary.lineage_id == first.summary.lineage_id
    assert again.document == first.document
    assert len(env.vault_files.files) == 1


async def _seed_titled_exam(env: _Env, *, actor: User, title: str) -> None:
    await env.seed_document(
        actor=actor,
        document=_guest_document(title).model_copy(update={"document_id": uuid4()}),
    )


async def test_handoff_numbers_a_taken_title_and_derives_the_vault_name() -> None:
    env = _Env()
    actor = _actor()
    await _seed_titled_exam(env, actor=actor, title="Prov")
    handler = _handler(env, FakeUow())

    created = await handler.handle(
        actor=actor, draft_id=uuid4(), document=_guest_document("Prov"), assets_by_id={}, notes=()
    )

    assert created.document.title == "Prov (2)"
    assert created.saved_document.title == "Prov (2)"
    assert created.summary.name == "Prov (2).provdokument.zip"
    assert env.index.locks == [actor.id]
    reopened = await env.get_handler.handle(actor=actor, lineage_id=created.summary.lineage_id)
    assert reopened.document.title == "Prov (2)"


async def test_handoff_numbers_from_a_draft_title_that_already_ends_in_a_suffix() -> None:
    env = _Env()
    actor = _actor()
    await _seed_titled_exam(env, actor=actor, title="Prov")
    await _seed_titled_exam(env, actor=actor, title="Prov (2)")
    handler = _handler(env, FakeUow())

    created = await handler.handle(
        actor=actor,
        draft_id=uuid4(),
        document=_guest_document("Prov (2)"),
        assets_by_id={},
        notes=(),
    )

    assert created.document.title == "Prov (3)"
    assert created.summary.name == "Prov (3).provdokument.zip"


async def test_handoff_replay_keeps_the_original_exam_despite_a_taken_title() -> None:
    env = _Env()
    actor = _actor()
    await _seed_titled_exam(env, actor=actor, title="Prov")
    handler = _handler(env, FakeUow())
    draft_id = uuid4()

    first = await handler.handle(
        actor=actor, draft_id=draft_id, document=_guest_document("Prov"), assets_by_id={}, notes=()
    )
    assert first.document.title == "Prov (2)"

    again = await handler.handle(
        actor=actor, draft_id=draft_id, document=_guest_document("Prov"), assets_by_id={}, notes=()
    )

    assert again.summary.lineage_id == first.summary.lineage_id
    assert again.document == first.document
    assert again.document.title == "Prov (2)"


async def test_handoff_stores_the_posted_notes_in_the_created_container() -> None:
    env = _Env()
    actor = _actor()
    handler = _handler(env, FakeUow())

    created = await handler.handle(
        actor=actor,
        draft_id=uuid4(),
        document=_guest_document("Prov"),
        assets_by_id={},
        notes=("Fråga 3 hoppades över.",),
    )

    assert created.notes == ("Fråga 3 hoppades över.",)
    vault_file = next(iter(env.vault_files.files.values()))
    container = env.codec.parse(content=await env.store.load(actor=actor, vault_file=vault_file))
    assert container.notes == ("Fråga 3 hoppades över.",)
