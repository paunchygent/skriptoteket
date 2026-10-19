"""Guest-draft handoff numbers duplicate exam titles against the real database.

Purpose:
    Prove that a signed-in teacher's guest-draft handoff keeps an untaken
    title, numbers a taken one (``Titel (2)``, ``Titel (3)``, ...), and never
    hands two concurrent handoffs the same numbered title. The title lock is
    held inside the handoff transaction, so the second handoff sees the first
    handoff's committed title before choosing its number.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_guest_draft_handoff import (
    ImportGuestExamDraftHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_blank import (
    blank_native_exam_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.identity.models import User
from skriptoteket.infrastructure.repositories.exam_guest_draft_handoffs import (
    PostgreSQLExamGuestDraftHandoffRepository,
)
from skriptoteket.infrastructure.repositories.exam_index_repository import (
    PostgreSQLExamIndexRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.exam_workspace_conversion_support import ConversionWorld, Ids
from tests.integration.infrastructure.repositories.exam_workspace_test_support import create_owner

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]


class LockCountingExamIndexRepository(PostgreSQLExamIndexRepository):
    """Prove the handoff takes the title lock; removing the call fails the test."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.lock_calls: list[UUID] = []

    async def lock_owner_titles(self, *, owner_user_id: UUID) -> None:
        self.lock_calls.append(owner_user_id)
        await super().lock_owner_titles(owner_user_id=owner_user_id)


async def _seed_titled_exam(
    session_factory: async_sessionmaker[AsyncSession],
    storage: LocalVaultStorage,
    clock: FixedClock,
    actor: User,
    title: str,
) -> None:
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        document = blank_native_exam_document().model_copy(
            update={"document_id": uuid4(), "revision": 1, "title": title}
        )
        await world.store.save(
            actor=actor,
            file_id=uuid4(),
            name=f"{title}.provdokument.zip",
            content=world.codec.build(
                content=ExamWorkspaceContainerContent(document=document, assets_by_id={})
            ),
            lineage_id=document.document_id,
            version=1,
        )


def _handoff_handler(
    world: ConversionWorld,
    clock: FixedClock,
    session: AsyncSession,
    index: PostgreSQLExamIndexRepository | None = None,
) -> ImportGuestExamDraftHandler:
    return ImportGuestExamDraftHandler(
        handoffs=PostgreSQLExamGuestDraftHandoffRepository(session),
        reader=GetExamWorkspaceDocumentHandler(
            vault_files=world.vault_files,
            codec=world.codec,
            store=world.store,
            jobs=world.jobs,
            uow=world.uow,
        ),
        codec=world.codec,
        store=world.store,
        clock=clock,
        id_generator=Ids(),
        index=index if index is not None else world.index,
    )


async def _handoff(
    session_factory: async_sessionmaker[AsyncSession],
    storage: LocalVaultStorage,
    clock: FixedClock,
    actor: User,
    draft_id: UUID,
    title: str,
) -> NativeExamDocument:
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        created = await _handoff_handler(world, clock, session).handle(
            actor=actor,
            draft_id=draft_id,
            document=blank_native_exam_document().model_copy(update={"title": title}),
            assets_by_id={},
            notes=(),
        )
        return created.document


async def test_concurrent_handoffs_with_the_same_taken_title_get_two_and_three(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    storage = LocalVaultStorage(vault_root=tmp_path)
    await _seed_titled_exam(session_factory, storage, clock, actor, "Prov")

    first, second = await asyncio.gather(
        _handoff(session_factory, storage, clock, actor, uuid4(), "Prov"),
        _handoff(session_factory, storage, clock, actor, uuid4(), "Prov"),
    )

    assert {first.title, second.title} == {"Prov (2)", "Prov (3)"}
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        names = {
            (await world.opened(actor, document.document_id)).summary.name
            for document in (first, second)
        }
        assert names == {"Prov (2).provdokument.zip", "Prov (3).provdokument.zip"}


async def test_handoff_takes_the_title_lock_inside_its_transaction(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    storage = LocalVaultStorage(vault_root=tmp_path)
    await _seed_titled_exam(session_factory, storage, clock, actor, "Prov")

    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        counting = LockCountingExamIndexRepository(session)
        created = await _handoff_handler(world, clock, session, index=counting).handle(
            actor=actor,
            draft_id=uuid4(),
            document=blank_native_exam_document().model_copy(update={"title": "Prov"}),
            assets_by_id={},
            notes=(),
        )

    assert created.document.title == "Prov (2)"
    assert counting.lock_calls == [actor.id]


async def test_handoff_numbers_existing_suffix_and_suffixed_draft_through_the_repository(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    storage = LocalVaultStorage(vault_root=tmp_path)
    await _seed_titled_exam(session_factory, storage, clock, actor, "Prov")
    await _seed_titled_exam(session_factory, storage, clock, actor, "Prov (2)")

    taken_number = await _handoff(session_factory, storage, clock, actor, uuid4(), "Prov")
    assert taken_number.title == "Prov (3)"

    suffixed_draft = await _handoff(session_factory, storage, clock, actor, uuid4(), "Prov (2)")
    assert suffixed_draft.title == "Prov (4)"


async def test_titles_like_matches_exactly_and_escapes_like_wildcards(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    storage = LocalVaultStorage(vault_root=tmp_path)
    await _seed_titled_exam(session_factory, storage, clock, actor, "Prov")
    await _seed_titled_exam(session_factory, storage, clock, actor, "Provs")
    await _seed_titled_exam(session_factory, storage, clock, actor, "100%_x")
    await _seed_titled_exam(session_factory, storage, clock, actor, "1000_x (2)")

    async with session_factory() as session:
        index = PostgreSQLExamIndexRepository(session)
        assert await index.titles_like(owner_user_id=actor.id, base="Prov") == {"Prov"}
        assert await index.titles_like(owner_user_id=actor.id, base="100%_x") == {"100%_x"}

    numbered = await _handoff(session_factory, storage, clock, actor, uuid4(), "100%_x")
    assert numbered.title == "100%_x (2)"


async def test_handoff_keeps_an_untaken_title_unchanged(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    storage = LocalVaultStorage(vault_root=tmp_path)

    created = await _handoff(session_factory, storage, clock, actor, uuid4(), "Eget prov")

    assert created.title == "Eget prov"
    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        assert (await world.opened(actor, created.document_id)).summary.name == (
            "Eget prov.provdokument.zip"
        )


async def test_handoff_store_still_writes_the_index_entry_with_the_numbered_title(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    clock = FixedClock(datetime.now(UTC))
    storage = LocalVaultStorage(vault_root=tmp_path)
    await _seed_titled_exam(session_factory, storage, clock, actor, "Prov")

    created = await _handoff(session_factory, storage, clock, actor, uuid4(), "Prov")

    async with session_factory() as session:
        saved = await PostgreSQLExamIndexRepository(session).get(
            owner_user_id=actor.id, lineage_id=created.document_id
        )
        assert saved is not None
        assert saved.title == "Prov (2)"
