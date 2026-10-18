"""Export file names follow the exam title (TASK-SKRIPT-40-04-05, D1)."""

import pytest

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceExportTarget,
    SaveExamWorkspaceDocumentRequest,
)
from skriptoteket.application.curated_apps.exam_workspace_exports import export_file_base_name
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    NativeExportBlocker,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import _Env
from tests.unit.application.curated_apps.handlers.test_exam_workspace_exports_handler import (
    _export_handler,
    _imported_and_reviewed,
)
from tests.unit.application.curated_apps.test_exam_workspace_exports import (
    _source_fallback_document,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_document_test_support import (
    with_next_revision,
)

_EXTENSIONS = {
    ExamWorkspaceExportTarget.QTI: "zip",
    ExamWorkspaceExportTarget.PDF: "pdf",
    ExamWorkspaceExportTarget.DOCX: "docx",
}


@pytest.fixture()
def env() -> _Env:
    return _Env()


def _base(title: str) -> str:
    document = _source_fallback_document().model_copy(update={"title": title})
    return export_file_base_name(document)


def test_punctuation_goes_and_swedish_letters_digits_and_single_spaces_stay() -> None:
    assert _base("  Prov: Svenska 2 – åk. 9 (Ö/Ä)!  ") == "Prov Svenska 2 åk 9 ÖÄ"
    assert _base("Läs-  och\tskrivprov, Åsa & Örjan") == "Läs och skrivprov Åsa Örjan"
    assert _base('a_b/c\\d:e*f?g"h<i>j|k.l') == "abcdefghijkl"


def test_decomposed_letters_keep_their_marks() -> None:
    assert _base("Bårk") == "Bårk"


@pytest.mark.parametrize("title", ["...", "?!", " - / ", "\t", " "])
def test_title_without_letters_or_digits_has_no_base_name(title: str) -> None:
    with pytest.raises(DomainError) as exc_info:
        _base(title)
    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


async def _retitled(env: _Env, title: str):
    actor, lineage_id = await _imported_and_reviewed(env, b"")
    head = await env.vault_files.get_document_head(user_id=actor.id, document_lineage_id=lineage_id)
    assert head is not None
    container = env.codec.parse(content=await env.store.load(actor=actor, vault_file=head))
    document = with_next_revision(container.document.model_copy(update={"title": title}))
    await env.save_handler.handle(
        actor=actor,
        lineage_id=lineage_id,
        request=SaveExamWorkspaceDocumentRequest(
            expected_revision=2, document=document, position_step_id=lineage_id
        ),
    )
    return actor, lineage_id, document.revision


@pytest.mark.asyncio
async def test_three_formats_share_one_title_base_and_save_to_mina_filer_under_it(
    env: _Env,
) -> None:
    actor, lineage_id, revision = await _retitled(env, "Prov: Rörelse & kraft (åk. 8)!")
    handler = _export_handler(env)

    downloads = [
        await handler.handle(
            actor=actor, lineage_id=lineage_id, target=target, expected_revision=revision
        )
        for target in ExamWorkspaceExportTarget
    ]
    saved = [
        await handler.save(
            actor=actor, lineage_id=lineage_id, target=target, expected_revision=revision
        )
        for target in ExamWorkspaceExportTarget
    ]

    expected = [
        f"Prov Rörelse kraft åk 8.{_EXTENSIONS[target]}" for target in ExamWorkspaceExportTarget
    ]
    assert [download.filename for download in downloads] == expected
    assert [file.name for file in saved] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("title", ["?!...", "", "   "])
async def test_title_of_only_punctuation_or_blank_refuses_every_export_and_names_no_file(
    env: _Env,
    title: str,
) -> None:
    actor, lineage_id, revision = await _retitled(env, title)
    handler = _export_handler(env)

    for target in ExamWorkspaceExportTarget:
        with pytest.raises(DomainError) as download_error:
            await handler.handle(
                actor=actor, lineage_id=lineage_id, target=target, expected_revision=revision
            )
        with pytest.raises(DomainError) as save_error:
            await handler.save(
                actor=actor, lineage_id=lineage_id, target=target, expected_revision=revision
            )
        for error in (download_error.value, save_error.value):
            assert error.code is ErrorCode.VALIDATION_ERROR
            assert error.details == {
                "blockers": [{"item_id": None, "reason": "title_without_text"}]
            }
            assert "titel" in error.message
            assert "frågor" not in error.message


@pytest.mark.asyncio
async def test_checklist_refuses_a_title_without_letters_or_digits_and_clears_after_a_valid_one(
    env: _Env,
) -> None:
    actor, lineage_id, revision = await _retitled(env, "?!...")
    handler = _export_handler(env)

    with pytest.raises(DomainError) as refused:
        await handler.checklist(actor=actor, lineage_id=lineage_id, expected_revision=revision)
    assert refused.value.details == {
        "blockers": [{"item_id": None, "reason": "title_without_text"}]
    }

    head = await env.vault_files.get_document_head(user_id=actor.id, document_lineage_id=lineage_id)
    assert head is not None
    container = env.codec.parse(content=await env.store.load(actor=actor, vault_file=head))
    fixed = with_next_revision(container.document.model_copy(update={"title": "Prov 1"}))
    await env.save_handler.handle(
        actor=actor,
        lineage_id=lineage_id,
        request=SaveExamWorkspaceDocumentRequest(
            expected_revision=revision, document=fixed, position_step_id=lineage_id
        ),
    )
    await handler.checklist(actor=actor, lineage_id=lineage_id, expected_revision=fixed.revision)


@pytest.mark.parametrize(
    ("title", "names_title", "names_questions"),
    [("?!...", True, False), ("Prov 1", False, True), ("?!...", True, True)],
    ids=["title-only", "questions-only", "title-and-questions"],
)
def test_refusal_names_only_the_objects_that_block(
    env: _Env, title: str, names_title: bool, names_questions: bool
) -> None:
    document = _source_fallback_document().model_copy(update={"title": title})
    if not names_questions:
        document = document.model_copy(update={"items": ()})

    with pytest.raises(DomainError) as refusal:
        _export_handler(env)._raise_for_blockers(document)

    assert ("titel" in refusal.value.message) is names_title
    assert ("frågor" in refusal.value.message) is names_questions


@pytest.mark.asyncio
async def test_saved_document_response_carries_the_gates_title_verdict(env: _Env) -> None:
    actor, lineage_id = await _imported_and_reviewed(env, b"")
    head = await env.vault_files.get_document_head(user_id=actor.id, document_lineage_id=lineage_id)
    assert head is not None
    container = env.codec.parse(content=await env.store.load(actor=actor, vault_file=head))

    responses = []
    for revision, title in ((2, "?!..."), (3, "Prov 1")):
        document = with_next_revision(container.document.model_copy(update={"title": title}))
        responses.append(
            await env.save_handler.handle(
                actor=actor,
                lineage_id=lineage_id,
                request=SaveExamWorkspaceDocumentRequest(
                    expected_revision=revision, document=document, position_step_id=lineage_id
                ),
            )
        )
        container = container.model_copy(update={"document": document})

    assert responses[0].export_blockers == (
        NativeExportBlocker(item_id=None, reason="title_without_text"),
    )
    assert responses[1].export_blockers == ()
