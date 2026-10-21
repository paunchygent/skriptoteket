"""Blank exam creation saves revision one under the untitled file name."""

from __future__ import annotations

from skriptoteket.application.curated_apps.handlers.exam_workspace_blank_document import (
    CreateBlankExamWorkspaceDocumentHandler,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
)


def _blank_handler(env: _Env) -> CreateBlankExamWorkspaceDocumentHandler:
    return CreateBlankExamWorkspaceDocumentHandler(
        store=env.store, codec=env.codec, id_generator=env.ids
    )


async def test_blank_saves_revision_one_with_the_untitled_name() -> None:
    env = _Env()
    actor = _actor()
    handler = _blank_handler(env)

    summary = await handler.handle(actor=actor)

    assert summary.version == 1
    assert summary.name == "Namnlöst prov.provdokument.zip"
    assert summary.title == ""
    assert summary.course_key is None
    files = list(env.vault_files.files.values())
    assert len(files) == 1
    vault_file = files[0]
    assert summary.vault_file_id == vault_file.id
    assert summary.lineage_id == vault_file.document_lineage_id


async def test_blank_saved_document_has_one_empty_question_and_matches_the_summary() -> None:
    env = _Env()
    actor = _actor()
    handler = _blank_handler(env)

    summary = await handler.handle(actor=actor)

    vault_file = next(iter(env.vault_files.files.values()))
    stored = env.vault_storage.stored[(actor.id, vault_file.id)]
    document = env.codec.parse(content=stored).document
    assert document.document_id == summary.lineage_id
    assert document.title == ""
    assert document.revision == 1
    assert len(document.items) == 1
