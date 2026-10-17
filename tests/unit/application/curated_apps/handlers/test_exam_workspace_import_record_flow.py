"""TASK-39-04-06: original import evidence survives retry, edits and persistence."""

from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.application.curated_apps.exam_workspace import SaveExamWorkspaceDocumentRequest
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxBuildRoundFailure,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_import_record import (
    NativeExamAnswerKeyStep,
    NativeExamChosenTypeStep,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    Env,
    document,
    item,
    retry_reply,
    source,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import _Env
from tests.unit.application.curated_apps.handlers.test_exam_workspace_docx_jobs import (
    claim,
    environment,
)
from tests.unit.domain.curated_apps.exam_workspace.test_exam_workspace_import_record import (
    import_record,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def imported_document():
    imported = item("item_001", 1, anchor="body:0001", source=source()).model_copy(
        update={"import_record": import_record(), "facit_text": "Facit: ursprungligt svar."}
    )
    return document(lineage_id=uuid4(), items=(imported,))


@pytest.mark.parametrize("reply", ["converted", "provider_failure", "disabled", "invalid"])
async def test_retry_preserves_saved_wording_and_adds_exactly_one_outcome_step(reply: str) -> None:
    env = Env(enabled=reply != "disabled")
    original = imported_document()
    await env.seed(original)
    env.exchange.reply = retry_reply(text="Ny formulering från modellen.")
    if reply == "provider_failure":
        env.exchange.failure = DocxBuildRoundFailure("Otillgänglig", code="provider_unavailable")
    elif reply == "invalid":
        env.exchange.reply = {}
    # Source evidence in the draft is untrusted. It cannot replace the saved import.
    forged = import_record().model_copy(
        update={
            "original_wording": import_record().original_wording.model_copy(
                update={"question_text": "FORGED DRAFT WORDING"}
            )
        }
    )
    draft = original.model_copy(
        update={"items": (original.items[0].model_copy(update={"import_record": forged}),)}
    )
    response = await env.retry(draft, kind=NativeExamItemKind.FREE_TEXT)
    record = response.item.import_record
    assert record is not None
    assert record.original_wording == import_record().original_wording
    assert record.steps[:-1] == import_record().steps
    assert record.steps[-1].model_dump(mode="json") == {
        "kind": "retry",
        "reason": "teacher_request",
        "from_kind": "free_text",
        "chosen_kind": "free_text",
        "outcome": "converted" if reply == "converted" else "review_required",
    }
    assert response.model_dump(mode="json")["item"]["import_record"] == record.model_dump(
        mode="json"
    )


async def test_two_retries_keep_original_wording_and_append_in_order_after_reopen() -> None:
    env = Env()
    original = imported_document()
    await env.seed(original)
    env.exchange.reply = retry_reply()
    first = await env.retry(original)
    after_first = original.model_copy(update={"revision": 2, "items": (first.item,)})
    await env.store.save(
        actor=env.actor,
        file_id=uuid4(),
        name="import.provdokument.zip",
        content=env.codec.build(
            content=ExamWorkspaceContainerContent(document=after_first, assets_by_id={})
        ),
        lineage_id=original.document_id,
        version=2,
        expected_revision=1,
    )
    second = await env.retry(after_first)
    assert second.item.import_record is not None
    assert second.item.import_record.original_wording == import_record().original_wording
    assert len(second.item.import_record.steps) == 4
    assert [step.kind for step in second.item.import_record.steps] == [
        "chosen_type",
        "answer_key",
        "retry",
        "retry",
    ]


@pytest.mark.parametrize("enabled", [True, False])
async def test_recorded_docx_import_publishes_each_record_and_get_reads_saved_evidence(
    enabled,
) -> None:
    # Observed DOCX fixture and recorded provider replies; this is replay, not live AI proof.
    env = environment(enabled=enabled)
    running = await claim(env)
    finished = await env.processor.handle(job=running)
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert running.workspace_lineage_id is not None
    opened = await env.get_handler.handle(actor=env.actor, lineage_id=running.workspace_lineage_id)
    for imported in opened.document.items:
        record = imported.import_record
        assert record is not None
        assert record.original_wording.question_text
        if imported.retry_source is not None:
            assert record.original_wording.question_text == "\n".join(
                chunk.text for chunk in imported.retry_source.chunks
            )
        assert record.original_wording.answer_key_text == imported.facit_text
        assert isinstance(record.steps[0], NativeExamChosenTypeStep)
        assert record.steps[0].chosen_kind == imported.kind
        assert isinstance(record.steps[1], NativeExamAnswerKeyStep)
        assert record.steps[1].origin == imported.answer_key.origin
    for update in (*env.replay.progress.updates, *env.replay.progress.finals):
        assert all(imported.import_record is not None for imported in update.document.items)
    payload = opened.model_dump_json()
    assert '"stage":' not in payload and '"diagnostics":' not in payload
    assert finished.diagnostics  # Raw events remain on the job rather than the document.


async def test_put_and_get_return_import_record_even_after_teacher_changes_facit() -> None:
    env = _Env()
    retry_env = Env()
    actor = retry_env.actor
    original = imported_document()
    expected_record = import_record().model_copy(
        update={
            "steps": (
                NativeExamChosenTypeStep(chosen_kind=NativeExamItemKind.SINGLE_CHOICE),
                NativeExamAnswerKeyStep(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
            )
        }
    )
    choice_item = original.items[0].model_copy(
        update={
            "kind": NativeExamItemKind.SINGLE_CHOICE,
            "choices": (
                NativeChoice(choice_id="choice_001", body=original.items[0].body),
                NativeChoice(choice_id="choice_002", body=original.items[0].body),
            ),
            "answer_key": NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED, correct_choice_ids=("choice_001",)
            ),
            "import_record": expected_record,
        }
    )
    original = original.model_copy(update={"items": (choice_item,)})
    await env.store.save(
        actor=actor,
        file_id=uuid4(),
        name="import.provdokument.zip",
        content=env.codec.build(
            content=ExamWorkspaceContainerContent(document=original, assets_by_id={})
        ),
        lineage_id=original.document_id,
        version=1,
    )
    edited_item = original.items[0].model_copy(
        update={
            "facit_text": "Lärarens nya facit.",
            "answer_key": NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED, correct_choice_ids=("choice_002",)
            ),
        }
    )
    edited = original.model_copy(update={"revision": 2, "items": (edited_item,)})
    saved = await env.save_handler.handle(
        actor=actor,
        lineage_id=original.document_id,
        request=SaveExamWorkspaceDocumentRequest(expected_revision=1, document=edited),
    )
    reopened = await env.get_handler.handle(actor=actor, lineage_id=original.document_id)
    for response in (saved, reopened):
        assert response.document.items[0].facit_text == "Lärarens nya facit."
        record = response.document.items[0].import_record
        assert (
            response.document.items[0].answer_key.origin is NativeAnswerKeyOrigin.TEACHER_AUTHORED
        )
        assert record == expected_record
        payload = response.model_dump(mode="json")["document"]["items"][0]
        assert payload["import_record"] == expected_record.model_dump(mode="json")
        assert "events" not in payload and "diagnostics" not in payload
