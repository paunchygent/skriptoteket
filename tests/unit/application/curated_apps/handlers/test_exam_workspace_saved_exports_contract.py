"""Saved exports share the download gate and remain children of one exam file."""

from io import BytesIO
from zipfile import ZipFile

import pytest

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceExportTarget,
)
from skriptoteket.application.scripting.handlers.delete_vault_file import DeleteVaultFileHandler
from skriptoteket.application.scripting.handlers.list_vault_files import ListVaultFilesHandler
from skriptoteket.application.scripting.handlers.restore_vault_file import RestoreVaultFileHandler
from skriptoteket.application.scripting.vault import (
    DeleteVaultFileCommand,
    ListVaultFilesQuery,
    RestoreVaultFileCommand,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.vault import VaultListState
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _NOW,
    FakeUow,
    _actor,
    _Env,
    _settings,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_exports_handler import (
    _export_handler,
    _store_step,
)
from tests.unit.application.curated_apps.test_exam_workspace_exports import (
    _reviewed,
    _source_fallback_document,
)
from tests.unit.application.scripting.handlers.test_list_vault_files_missing_on_disk import (
    FakeCuratedApps,
    FakeRuns,
    FakeTools,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("target", list(ExamWorkspaceExportTarget))
async def test_saving_source_fallback_export_is_blocked_without_a_vault_side_effect(
    target: ExamWorkspaceExportTarget,
) -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor, document=_source_fallback_document())
    usage = env.vault_usage.usage.bytes_total
    with pytest.raises(DomainError) as error:
        await _export_handler(env).save(
            actor=actor,
            lineage_id=imported.summary.lineage_id,
            target=target,
            expected_revision=1,
        )
    assert error.value.code is ErrorCode.VALIDATION_ERROR
    assert (error.value.details or {}).get("blockers")
    assert len(await env.vault_files.list_active_for_user(user_id=actor.id)) == 1
    assert env.vault_usage.usage.bytes_total == usage


@pytest.mark.asyncio
async def test_saving_trashed_format_reuses_its_identity_and_charges_all_replacement_bytes() -> (
    None
):
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    await _store_step(
        env,
        actor,
        lineage,
        _reviewed(imported.document).model_copy(update={"revision": 2}),
    )
    exports = _export_handler(env)
    original = await exports.save(
        actor=actor, lineage_id=lineage, target=ExamWorkspaceExportTarget.QTI, expected_revision=2
    )
    await DeleteVaultFileHandler(
        uow=FakeUow(),
        vault_files=env.vault_files,
        vault_usage=env.vault_usage,
        clock=FixedClock(_NOW),
    ).handle(actor=actor, command=DeleteVaultFileCommand(file_id=original.id))
    assert env.vault_files.files[original.id].deleted_at is not None
    resaved = await exports.save(
        actor=actor, lineage_id=lineage, target=ExamWorkspaceExportTarget.QTI, expected_revision=2
    )
    assert resaved.id == original.id
    assert resaved.deleted_at is None
    assert len(env.vault_files.files) == 2  # One exam plus one format, including the trash.
    active = await env.vault_files.list_active_for_user(user_id=actor.id)
    expected_total = sum(file.bytes for file in active)
    assert env.vault_usage.usage.bytes_total == expected_total
    restored = await RestoreVaultFileHandler(
        uow=FakeUow(),
        vault_files=env.vault_files,
        vault_usage=env.vault_usage,
        settings=_settings(),
        clock=FixedClock(_NOW),
    ).handle(actor=actor, command=RestoreVaultFileCommand(file_id=original.id))
    assert restored.file.id == resaved.id
    assert env.vault_usage.usage.bytes_total == expected_total
    assert (
        len(await env.vault_files.list_saved_exports(user_id=actor.id, document_lineage_id=lineage))
        == 1
    )


@pytest.mark.asyncio
async def test_resaved_qti_replaces_bytes_and_lists_once_under_its_exam() -> None:
    env = _Env()
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    reviewed = _reviewed(imported.document).model_copy(update={"revision": 2})
    await _store_step(env, actor, lineage, reviewed)
    exports = _export_handler(env)
    first = await exports.save(
        actor=actor, lineage_id=lineage, target=ExamWorkspaceExportTarget.QTI, expected_revision=2
    )
    first_item = reviewed.items[0]
    paragraph = first_item.body[0]
    marker = "Lärarens omarbetade fråga"
    changed = reviewed.model_copy(
        update={
            "revision": 3,
            "items": (
                first_item.model_copy(
                    update={
                        "body": (
                            paragraph.model_copy(
                                update={
                                    "segments": (
                                        paragraph.segments[0].model_copy(update={"text": marker}),
                                        *paragraph.segments[1:],
                                    )
                                }
                            ),
                            *first_item.body[1:],
                        )
                    }
                ),
                *reviewed.items[1:],
            ),
        }
    )
    await _store_step(env, actor, lineage, changed)
    second = await exports.save(
        actor=actor, lineage_id=lineage, target=ExamWorkspaceExportTarget.QTI, expected_revision=3
    )
    assert second.id == first.id
    assert second.document_lineage_id == lineage
    assert second.document_version == 3
    stored = await env.store.load(actor=actor, vault_file=second)
    with ZipFile(BytesIO(stored)) as archive:
        xml = "\n".join(
            archive.read(name).decode("utf-8")
            for name in archive.namelist()
            if name.endswith(".xml")
        )
    assert marker in xml
    active = await env.vault_files.list_active_for_user(user_id=actor.id)
    assert {file.id for file in active} == {imported.summary.vault_file_id, first.id}
    assert env.vault_usage.usage.bytes_total == sum(file.bytes for file in active)
    listed = await ListVaultFilesHandler(
        uow=FakeUow(),
        runs=FakeRuns(),
        tools=FakeTools(),
        curated_apps=FakeCuratedApps(),
        vault_files=env.vault_files,
        vault_usage=env.vault_usage,
        vault_storage=env.vault_storage,
        settings=_settings(),
    ).handle(actor=actor, query=ListVaultFilesQuery(state=VaultListState.ACTIVE, limit=1))
    assert [file.id for file in listed.files] == [imported.summary.vault_file_id]
    assert [file.id for file in listed.files[0].exports] == [first.id]
    assert listed.next_cursor is None
    # Exports must never become the workspace document head.
    assert (await env.get_handler.handle(actor=actor, lineage_id=lineage)).document == changed
