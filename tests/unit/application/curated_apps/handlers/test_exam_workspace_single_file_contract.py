"""Adversarial persistence contracts for one durable exam file per lineage."""

from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace_history import (
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_undo_steps import (
    StoreExamWorkspaceUndoStepHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    SequenceIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _NOW,
    FakeUow,
    _actor,
    _Env,
    _settings,
)


def _payload(env: _Env, lineage: UUID, revision: int, title: str) -> bytes:
    document = NativeExamDocument.model_validate_json(
        Path("tests/fixtures/exam_conversion/native_workspace_grammatik.json").read_bytes()
    ).model_copy(update={"document_id": lineage, "revision": revision, "title": title})
    return env.codec.build(
        content=ExamWorkspaceContainerContent(
            document=document,
            assets_by_id={},
            notes=(),
        )
    )


def _store(
    env: _Env, *, total_limit: int, uow: FakeUow | None = None
) -> ExamWorkspaceDocumentStore:
    return ExamWorkspaceDocumentStore(
        vault_files=env.vault_files,
        vault_usage=env.vault_usage,
        vault_storage=env.vault_storage,
        index=env.index,
        codec=env.codec,
        uow=uow or FakeUow(),
        clock=FixedClock(_NOW),
        settings=Settings.model_construct(
            VAULT_MAX_FILE_BYTES=5_000_000, VAULT_MAX_TOTAL_BYTES=total_limit
        ),
    )


@pytest.mark.asyncio
async def test_overwrite_reports_new_save_time_without_changing_row_creation_time() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    original = env.vault_files.files[imported.summary.vault_file_id]
    later = _NOW + timedelta(days=3)
    later_store = ExamWorkspaceDocumentStore(
        vault_files=env.vault_files,
        vault_usage=env.vault_usage,
        vault_storage=env.vault_storage,
        index=env.index,
        codec=env.codec,
        uow=FakeUow(),
        clock=FixedClock(later),
        settings=_settings(),
    )
    await StoreExamWorkspaceUndoStepHandler(
        vault_files=env.vault_files,
        codec=env.codec,
        store=later_store,
        id_generator=SequenceIdGenerator([uuid4()]),
        jobs=env.enrichment_jobs,
    ).handle(
        actor=actor,
        lineage_id=imported.summary.lineage_id,
        request=StoreExamWorkspaceUndoStepRequest(
            expected_cursor=(
                await env.save_handler.history(actor=actor, lineage_id=imported.summary.lineage_id)
            ).cursor,
            document=imported.document.model_copy(update={"title": "Later title"}),
        ),
    )
    reopened = await env.get_handler.handle(actor=actor, lineage_id=imported.summary.lineage_id)
    assert reopened.summary.saved_at == later
    assert reopened.summary.vault_file_id == original.id
    assert env.vault_files.files[original.id].created_at == original.created_at == _NOW


@pytest.mark.asyncio
async def test_overwrites_charge_only_size_delta_and_keep_one_file_at_quota() -> None:
    env, actor, lineage = _Env(), _actor(), uuid4()
    contents = [
        _payload(env, lineage, revision, title)
        for revision, title in enumerate(
            ("a", "A much longer changed title for this exam", "b"), start=1
        )
    ]
    store = _store(env, total_limit=max(map(len, contents)))
    original_id = uuid4()
    for revision, content in enumerate(contents, start=1):
        saved = await store.save(
            actor=actor,
            file_id=original_id if revision == 1 else uuid4(),
            name="Prov.provdokument.zip",
            content=content,
            lineage_id=lineage,
            version=revision,
            expected_revision=None if revision == 1 else revision - 1,
            editor_step_id=None if revision == 1 else lineage,
        )
        assert saved.id == original_id
        assert saved.bytes == len(content)
        assert saved.document_version == revision
        assert env.vault_usage.usage.bytes_total == len(content)
        assert await store.load(actor=actor, vault_file=saved) == content
        assert len(await env.vault_files.list_active_for_user(user_id=actor.id)) == 1
        assert set(env.vault_storage.stored) == {(actor.id, original_id)}


@pytest.mark.asyncio
async def test_stale_save_does_not_replace_payload_or_accounting() -> None:
    env, actor, lineage = _Env(), _actor(), uuid4()
    store = _store(env, total_limit=50_000)
    current = _payload(env, lineage, 3, "Current")
    saved = await store.save(
        actor=actor,
        file_id=uuid4(),
        name="Prov.provdokument.zip",
        content=current,
        lineage_id=lineage,
        version=3,
    )
    with pytest.raises(DomainError) as error:
        await store.save(
            actor=actor,
            file_id=uuid4(),
            name=saved.name,
            content=_payload(env, lineage, 2, "Stale"),
            lineage_id=lineage,
            version=2,
            expected_revision=1,
            editor_step_id=lineage,
        )
    assert error.value.code is ErrorCode.CONFLICT
    assert await store.load(actor=actor, vault_file=saved) == current
    assert env.vault_usage.usage.bytes_total == len(current)
    assert env.vault_files.files[saved.id].document_version == 3


@pytest.mark.asyncio
async def test_failed_accounting_does_not_destroy_previous_file_bytes() -> None:
    env, actor, lineage = _Env(), _actor(), uuid4()
    store = _store(env, total_limit=50_000)
    current = _payload(env, lineage, 1, "Last successful save")
    saved = await store.save(
        actor=actor,
        file_id=uuid4(),
        name="Prov.provdokument.zip",
        content=current,
        lineage_id=lineage,
        version=1,
    )
    env.vault_usage.fail_upsert = True
    with pytest.raises(RuntimeError, match="usage failed"):
        await store.save(
            actor=actor,
            file_id=uuid4(),
            name=saved.name,
            content=_payload(env, lineage, 2, "Uncommitted replacement"),
            lineage_id=lineage,
            version=2,
            expected_revision=1,
            editor_step_id=lineage,
        )
    assert await store.load(actor=actor, vault_file=saved) == current
    assert (actor.id, saved.id) not in env.vault_storage.deleted


@pytest.mark.asyncio
async def test_outer_transaction_failure_restores_the_last_successful_file() -> None:
    class NestedFailingUow(FakeUow):
        depth = 0
        fail_commit = False

        async def __aenter__(self) -> "NestedFailingUow":
            self.depth += 1
            return self

        async def __aexit__(self, *args: object) -> None:
            self.depth -= 1
            if self.depth == 0 and self.fail_commit:
                raise RuntimeError("outer commit failed")

    env, actor, lineage = _Env(), _actor(), uuid4()
    uow = NestedFailingUow()
    store = _store(env, total_limit=50_000, uow=uow)
    current = _payload(env, lineage, 1, "Last successful save")
    saved = await store.save(
        actor=actor,
        file_id=uuid4(),
        name="Prov.provdokument.zip",
        content=current,
        lineage_id=lineage,
        version=1,
    )
    uow.fail_commit = True
    with pytest.raises(RuntimeError, match="outer commit failed"):
        async with store.transaction(user_id=actor.id, lineage_id=lineage):
            await store.save(
                actor=actor,
                file_id=uuid4(),
                name=saved.name,
                content=_payload(env, lineage, 2, "Uncommitted replacement"),
                lineage_id=lineage,
                version=2,
                expected_revision=1,
                editor_step_id=lineage,
            )
    assert await store.load(actor=actor, vault_file=saved) == current


@pytest.mark.asyncio
async def test_growth_past_quota_keeps_the_previous_durable_file() -> None:
    env, actor, lineage = _Env(), _actor(), uuid4()
    current = _payload(env, lineage, 1, "a")
    larger = _payload(env, lineage, 2, "A substantially longer changed title to grow the file")
    assert len(larger) > len(current)
    store = _store(env, total_limit=len(current))
    saved = await store.save(
        actor=actor,
        file_id=uuid4(),
        name="Prov.provdokument.zip",
        content=current,
        lineage_id=lineage,
        version=1,
    )
    with pytest.raises(DomainError) as error:
        await store.save(
            actor=actor,
            file_id=uuid4(),
            name=saved.name,
            content=larger,
            lineage_id=lineage,
            version=2,
            expected_revision=1,
            editor_step_id=lineage,
        )
    assert error.value.code is ErrorCode.VALIDATION_ERROR
    assert await store.load(actor=actor, vault_file=saved) == current
    assert env.vault_usage.usage.bytes_total == len(current)
    assert env.vault_files.files[saved.id].document_version == 1
