"""The exam's Mina filer file follows its title on every stored step (D13)."""

from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentSummary
from skriptoteket.application.curated_apps.handlers.exam_workspace_blank_document import (
    CreateBlankExamWorkspaceDocumentHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.identity.models import User
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
    _store_step,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_document_test_support import (
    with_next_revision,
)


@pytest.fixture()
def env() -> _Env:
    return _Env()


async def _blank_saved(env: _Env) -> tuple[User, ExamWorkspaceDocumentSummary]:
    actor = _actor()
    handler = CreateBlankExamWorkspaceDocumentHandler(
        store=env.store, codec=env.codec, id_generator=env.ids
    )
    summary = await handler.handle(actor=actor)
    return actor, summary


async def _head_name(env: _Env, actor: User, lineage: UUID) -> str:
    head = await env.vault_files.get_document_head(user_id=actor.id, document_lineage_id=lineage)
    assert head is not None
    return head.name


@pytest.mark.asyncio
async def test_blank_exam_saved_as_untitled_and_step_with_title_renames(env: _Env) -> None:
    actor, summary = await _blank_saved(env)
    assert summary.name == "Namnlöst prov.provdokument.zip"

    stored = env.vault_storage.stored[(actor.id, summary.vault_file_id)]
    document = env.codec.parse(content=stored).document
    titled = document.model_copy(update={"title": "Prov: Vecka 5!"})
    await _store_step(env, actor, summary.lineage_id, with_next_revision(titled))

    assert await _head_name(env, actor, summary.lineage_id) == "Prov Vecka 5.provdokument.zip"


@pytest.mark.asyncio
async def test_imported_exam_renamed_when_stored_step_changes_title(env: _Env) -> None:
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    assert imported.summary.name == "grammatik.provdokument.zip"

    retitled = imported.document.model_copy(update={"title": "Nytt namn: Vecka 2!"})
    await _store_step(env, actor, imported.summary.lineage_id, with_next_revision(retitled))

    assert (
        await _head_name(env, actor, imported.summary.lineage_id)
        == "Nytt namn Vecka 2.provdokument.zip"
    )


@pytest.mark.asyncio
async def test_second_title_change_renames_again(env: _Env) -> None:
    actor = _actor()
    imported = await env.seed_document(actor=actor)

    first = imported.document.model_copy(update={"title": "Första namnet 1"})
    await _store_step(env, actor, imported.summary.lineage_id, with_next_revision(first))
    second = first.model_copy(update={"title": "Andra namnet 2!"})
    await _store_step(env, actor, imported.summary.lineage_id, with_next_revision(second))

    assert (
        await _head_name(env, actor, imported.summary.lineage_id)
        == "Andra namnet 2.provdokument.zip"
    )


@pytest.mark.asyncio
async def test_step_with_unchanged_title_keeps_current_file_name(env: _Env) -> None:
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    head = await env.vault_files.get_document_head(user_id=actor.id, document_lineage_id=lineage)
    assert head is not None
    env.vault_files.files[head.id] = head.model_copy(
        update={"name": "Spara som-namn.provdokument.zip"}
    )

    await _store_step(env, actor, lineage, with_next_revision(imported.document))

    assert await _head_name(env, actor, lineage) == "Spara som-namn.provdokument.zip"


@pytest.mark.asyncio
async def test_save_overwrite_with_changed_title_renames(env: _Env) -> None:
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    head = await env.vault_files.get_document_head(user_id=actor.id, document_lineage_id=lineage)
    assert head is not None
    env.vault_files.files[head.id] = head.model_copy(
        update={"name": "Spara som-namn.provdokument.zip"}
    )

    retitled = imported.document.model_copy(update={"title": "Sparat namn 7", "revision": 2})
    saved = await env.store.save(
        actor=actor,
        file_id=uuid4(),
        name="stale-writer-copy.provdokument.zip",
        content=env.codec.build(
            content=ExamWorkspaceContainerContent(document=retitled, assets_by_id={}, notes=())
        ),
        lineage_id=lineage,
        version=2,
        expected_revision=1,
        preserve_editor_position=True,
    )
    assert saved.name == "Sparat namn 7.provdokument.zip"


@pytest.mark.asyncio
async def test_save_overwrite_with_unchanged_title_keeps_current_file_name(env: _Env) -> None:
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    lineage = imported.summary.lineage_id
    head = await env.vault_files.get_document_head(user_id=actor.id, document_lineage_id=lineage)
    assert head is not None
    env.vault_files.files[head.id] = head.model_copy(
        update={"name": "Spara som-namn.provdokument.zip"}
    )

    same_title = imported.document.model_copy(update={"revision": 2})
    saved = await env.store.save(
        actor=actor,
        file_id=uuid4(),
        name="stale-writer-copy.provdokument.zip",
        content=env.codec.build(
            content=ExamWorkspaceContainerContent(document=same_title, assets_by_id={}, notes=())
        ),
        lineage_id=lineage,
        version=2,
        expected_revision=1,
        preserve_editor_position=True,
    )
    assert saved.name == "Spara som-namn.provdokument.zip"
