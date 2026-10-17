"""Imported wording and decisions are saved data, not editable-key provenance."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    ProducedItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_import_records import (
    with_docx_import_records,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_import_record import (
    NativeExamImportRecord,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    document,
    item,
    retry_reply,
    source,
)

pytestmark = pytest.mark.unit


def import_record() -> NativeExamImportRecord:
    return NativeExamImportRecord.model_validate(
        {
            "original_wording": {
                "question_text": "Originalfrågan.\nNästa stycke.",
                "answer_key_text": "Facit: ursprungligt svar.",
            },
            "steps": [
                {"kind": "chosen_type", "chosen_kind": "free_text"},
                {"kind": "answer_key", "origin": "not_applicable"},
            ],
        }
    )


def test_created_question_has_no_import_record() -> None:
    created = item("item_001", 1, anchor="body:0001")
    assert created.import_record is None
    assert created.model_dump(mode="json")["import_record"] is None


@pytest.mark.parametrize("origin", ["docx_import", "digiexam_import"])
def test_same_record_round_trips_for_both_sources_without_raw_events(origin: str) -> None:
    imported = item("item_001", 1, anchor="body:0001").model_copy(
        update={"import_record": import_record()}
    )
    saved = document(lineage_id=uuid4(), items=(imported,)).model_dump(mode="json")
    saved["origin"] = {
        "kind": origin,
        "source_filename": "source.docx" if origin == "docx_import" else "source.zip",
        "source_sha256": "a" * 64,
    }
    reopened = NativeExamDocument.model_validate_json(
        NativeExamDocument.model_validate(saved).model_dump_json()
    )
    assert reopened.items[0].import_record == import_record()
    assert reopened.schema_version != "native_exam_document_v4"
    assert set(reopened.items[0].import_record.model_dump()) == {"original_wording", "steps"}
    assert "events" not in reopened.model_dump()
    assert "diagnostics" not in reopened.items[0].model_dump()


@pytest.mark.parametrize("location", ["record", "step"])
def test_raw_build_events_cannot_be_smuggled_into_the_saved_record(location: str) -> None:
    payload = import_record().model_dump(mode="json")
    target = payload if location == "record" else payload["steps"][0]
    target["events"] = [{"stage": "admission", "code": "type_conflict", "batch": "batch_1"}]
    with pytest.raises(ValidationError):
        NativeExamImportRecord.model_validate(payload)


@pytest.mark.parametrize(
    "key_source,has_key,kind,expected_origin",
    [
        ("copied", True, "single_choice", "source_provided"),
        ("interpreted", True, "single_choice", "ai_interpreted"),
        ("invented", True, "single_choice", "machine_proposed"),
        (None, False, "single_choice", "absent"),
        (None, False, "free_text", "not_applicable"),
    ],
)
def test_docx_capture_keeps_plain_own_wording_and_import_time_key_origin(
    key_source, has_key, kind, expected_origin
) -> None:
    items = retry_reply(kind=kind)["items"]
    assert isinstance(items, list)
    payload = items[0]
    assert isinstance(payload, dict)
    facit = "Lärarens originalfacit." if key_source in {"copied", "interpreted"} else None
    payload.update({"key_source": key_source, "facit_text": facit})
    if kind == "single_choice":
        payload["choices"] = [
            {"text": "Rött", "correct": has_key},
            {"text": "Blått", "correct": False},
        ]
    built = native_item(ProducedItem.model_validate(payload), language="sv")
    own = source(text="Frågan i original.", key_anchors=("body:0008",))
    own = own.model_copy(
        update={
            "chunks": (
                own.chunks[0].model_copy(update={"marked_text": "<b>INTE MARKUP</b>"}),
                own.chunks[0].model_copy(
                    update={"anchor": "body:0002", "text": "Eget andra stycke."}
                ),
            ),
            "context_chunks": source(anchor="body:0099", text="INTE DELAD TEXT").chunks,
        }
    )
    built = built.model_copy(update={"retry_source": own})
    captured = (
        with_docx_import_records(document(lineage_id=uuid4(), items=(built,)), chunks=(), events=())
        .items[0]
        .import_record
    )
    assert captured is not None
    assert captured.original_wording.question_text == "Frågan i original.\nEget andra stycke."
    assert captured.original_wording.answer_key_text == facit
    assert [step.model_dump(mode="json") for step in captured.steps] == [
        {"kind": "chosen_type", "chosen_kind": kind},
        {"kind": "answer_key", "origin": expected_origin},
    ]


@pytest.mark.parametrize(
    "code,anchor,chosen,expected_count",
    [
        ("type_conflict", "body:0001", "gap_fill", 3),
        ("type_conflict_kept", "body:0001", "gap_fill", 2),
        ("type_conflict", "body:0099", "gap_fill", 2),
        ("type_conflict", "body:0001", "free_text", 2),
    ],
)
def test_conflict_steps_belong_only_to_the_question_that_changed_type(
    code, anchor, chosen, expected_count
) -> None:
    imported = item("item_001", 1, anchor="body:0001", source=source())
    event = DocxBuildEvent(stage="admission", code=code, anchors=(anchor,), detail=chosen)
    result = with_docx_import_records(
        document(lineage_id=uuid4(), items=(imported,)), chunks=(), events=(event,)
    )
    record = result.items[0].import_record
    assert record is not None
    assert len(record.steps) == expected_count
    if expected_count == 3:
        assert record.steps[-1].model_dump(mode="json") == {
            "kind": "retry",
            "reason": "type_conflict",
            "from_kind": "free_text",
            "chosen_kind": "gap_fill",
            "outcome": "review_required",
        }


def test_successful_resend_keeps_first_label_and_chosen_type_despite_review_reasons() -> None:
    items = retry_reply(kind="multiple_response")["items"]
    assert isinstance(items, list)
    payload = items[0]
    assert isinstance(payload, dict)
    payload.update(
        {
            "key_source": "interpreted",
            "facit_text": "Båda färgerna.",
            "choices": [{"text": "Röd", "correct": True}, {"text": "Blå", "correct": True}],
        }
    )
    built = native_item(ProducedItem.model_validate(payload), language="sv")
    built = built.model_copy(
        update={
            "retry_source": source(label_kind=NativeExamItemKind.SINGLE_CHOICE),
            "review": built.review.model_copy(update={"reasons": ("Kontrollera tolkningen.",)}),
        }
    )
    result = with_docx_import_records(
        document(lineage_id=uuid4(), items=(built,)),
        chunks=(),
        events=(
            DocxBuildEvent(stage="grouping", code="retry", detail="whole job"),
            DocxBuildEvent(
                stage="admission",
                code="type_conflict",
                anchors=("body:0001",),
                detail="multiple_response",
            ),
            DocxBuildEvent(
                stage="admission",
                code="type_conflict_kept",
                anchors=("body:0001",),
                detail="multiple_response",
            ),
        ),
    )
    record = result.items[0].import_record
    assert record is not None
    assert [step.model_dump(mode="json") for step in record.steps] == [
        {"kind": "chosen_type", "chosen_kind": "multiple_response"},
        {"kind": "answer_key", "origin": "ai_interpreted"},
        {
            "kind": "retry",
            "reason": "type_conflict",
            "from_kind": "single_choice",
            "chosen_kind": "multiple_response",
            "outcome": "converted",
        },
    ]


def test_ungrouped_review_fallback_keeps_its_exact_source_chunk_only() -> None:
    imported = item("item_001", 1, anchor="body:0001")
    result = with_docx_import_records(
        document(lineage_id=uuid4(), items=(imported,)),
        chunks=(
            DocxChunk("body:0001", "paragraph", "Originalet.", "<i>Originalet.</i>"),
            DocxChunk("body:0002", "paragraph", "Annan fråga.", "Annan fråga."),
        ),
        events=(),
    )
    record = result.items[0].import_record
    assert record is not None
    assert record.original_wording.question_text == "Originalet."


@pytest.mark.parametrize("order", [(), (0,), (1, 0), (0, 1, 0)])
def test_record_requires_initial_type_then_key_then_only_retries(order: tuple[int, ...]) -> None:
    payload = import_record().model_dump(mode="json")
    steps = payload["steps"]
    payload["steps"] = [steps[index] for index in order]
    with pytest.raises(ValidationError):
        NativeExamImportRecord.model_validate(payload)


def test_saved_v4_is_rejected_without_backfill() -> None:
    saved = document(
        lineage_id=uuid4(), items=(item("item_001", 1, anchor="body:0001"),)
    ).model_dump(mode="json")
    saved["schema_version"] = "native_exam_document_v4"
    with pytest.raises(ValidationError):
        NativeExamDocument.model_validate(saved)
