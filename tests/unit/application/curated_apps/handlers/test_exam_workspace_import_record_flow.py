"""TASK-39-04-06: original import evidence survives retry, edits and persistence."""

from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.application.curated_apps.exam_workspace import (
    RetryExamWorkspaceItemRequest,
    SaveExamWorkspaceDocumentRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxBuildRoundFailure,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_retry import (
    RetryExamWorkspaceItemHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_import_record import (
    NativeExamAnswerKeyStep,
    NativeExamChosenTypeStep,
    NativeExamRetryStep,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeParseOrigin,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    PROFILE,
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


@pytest.mark.parametrize("review_attempts", [1, 2], ids=["two-retries", "three-retries"])
@pytest.mark.parametrize("forge_wording", [False, True], ids=["original", "forged-wording"])
async def test_unsaved_retries_keep_all_attempts_through_reload_save_and_reopen(
    review_attempts: int, forge_wording: bool
) -> None:
    env = _Env()
    retry_env = Env()
    actor = retry_env.actor
    handler = RetryExamWorkspaceItemHandler(
        vault_files=env.vault_files,
        codec=env.codec,
        store=env.store,
        exchange=retry_env.exchange,
        profile=PROFILE,
        enabled=True,
    )
    original = imported_document()
    head = await env.store.save(
        actor=actor,
        file_id=uuid4(),
        name="import.provdokument.zip",
        content=env.codec.build(
            content=ExamWorkspaceContainerContent(document=original, assets_by_id={})
        ),
        lineage_id=original.document_id,
        version=original.revision,
    )
    saved_bytes = await env.store.load(actor=actor, vault_file=head)
    expected_record = import_record()
    draft = original
    review_kinds = (NativeExamItemKind.SINGLE_CHOICE, NativeExamItemKind.GAP_FILL)
    kinds = (*review_kinds[:review_attempts], NativeExamItemKind.FREE_TEXT)
    for attempt, kind in enumerate(kinds):
        converted = attempt == review_attempts
        retry_env.exchange.failure = (
            DocxBuildRoundFailure("Otillgänglig", code="provider_unavailable")
            if attempt == 0
            else None
        )
        retry_env.exchange.reply = retry_reply(text="Slutlig frågetext.") if converted else {}
        if forge_wording:
            current = draft.items[0]
            record = current.import_record
            assert record is not None
            forged = record.model_copy(
                update={
                    "original_wording": record.original_wording.model_copy(
                        update={
                            "question_text": f"FORGED QUESTION {attempt}",
                            "answer_key_text": f"FORGED ANSWER {attempt}",
                        }
                    )
                }
            )
            draft = draft.model_copy(
                update={"items": (current.model_copy(update={"import_record": forged}),)}
            )
        # Reload the working draft, not a newly saved vault revision, before each request.
        draft = NativeExamDocument.model_validate_json(draft.model_dump_json())
        assert draft.revision == original.revision
        retry_response = await handler.handle(
            actor=actor,
            lineage_id=original.document_id,
            request=RetryExamWorkspaceItemRequest(document=draft, item_id="item_001", kind=kind),
        )
        expected_record = expected_record.model_copy(
            update={
                "steps": (
                    *expected_record.steps,
                    NativeExamRetryStep(
                        reason="teacher_request",
                        from_kind=draft.items[0].kind,
                        chosen_kind=kind,
                        outcome="converted" if converted else "review_required",
                    ),
                )
            }
        )
        assert retry_response.item.import_record == expected_record
        assert retry_response.item.review.parse_origin is (
            NativeParseOrigin.LLM_PARSED if converted else NativeParseOrigin.DETERMINISTIC
        )
        draft = draft.model_copy(update={"items": (retry_response.item,)})
        assert (
            await env.vault_files.get_document_head(
                user_id=actor.id, document_lineage_id=original.document_id
            )
            == head
        )
        assert await env.store.load(actor=actor, vault_file=head) == saved_bytes
    assert len(retry_env.exchange.requests) == len(kinds)
    assert len(env.vault_files.files) == 1
    final_draft = NativeExamDocument.model_validate_json(draft.model_dump_json()).model_copy(
        update={"revision": original.revision + 1}
    )
    saved = await env.save_handler.handle(
        actor=actor,
        lineage_id=original.document_id,
        request=SaveExamWorkspaceDocumentRequest(
            expected_revision=original.revision, document=final_draft
        ),
    )
    reopened = await env.get_handler.handle(actor=actor, lineage_id=original.document_id)
    for response in (saved, reopened):
        assert response.document.items[0].body == final_draft.items[0].body
        assert response.document.items[0].import_record == expected_record
        assert response.saved_document.items[0].import_record == expected_record
        assert response.model_dump(mode="json")["document"]["items"][0][
            "import_record"
        ] == expected_record.model_dump(mode="json")


@pytest.mark.parametrize("tamper", ["remove", "rewrite"])
async def test_retry_rejects_draft_history_that_does_not_extend_saved_steps(tamper: str) -> None:
    env = Env()
    original = imported_document()
    saved_step = NativeExamRetryStep(
        reason="teacher_request",
        from_kind=NativeExamItemKind.FREE_TEXT,
        chosen_kind=NativeExamItemKind.SINGLE_CHOICE,
        outcome="review_required",
    )
    saved_record = import_record().model_copy(
        update={"steps": (*import_record().steps, saved_step)}
    )
    original = original.model_copy(
        update={"items": (original.items[0].model_copy(update={"import_record": saved_record}),)}
    )
    await env.seed(original)
    draft_steps = saved_record.steps[:-1]
    if tamper == "rewrite":
        draft_steps = (*draft_steps, saved_step.model_copy(update={"outcome": "converted"}))
    draft = original.model_copy(
        update={
            "items": (
                original.items[0].model_copy(
                    update={"import_record": saved_record.model_copy(update={"steps": draft_steps})}
                ),
            )
        }
    )
    draft = NativeExamDocument.model_validate_json(draft.model_dump_json())
    env.exchange.reply = retry_reply()
    with pytest.raises(DomainError) as exc_info:
        await env.retry(draft)
    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert env.exchange.requests == []


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
