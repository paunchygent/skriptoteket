"""Native exam documents built from the recorded v7 corpus conversions."""

from pathlib import Path
from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildEnvelope
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeExamParent,
    NativeParagraph,
    NativeTextSegment,
)

_RECORDINGS = Path("tests/fixtures/exam_conversion/docx_build_v7")
ENGLISH_EXAM = "bf26_english_1_unit_test_kap_1_2_med_facit"


def recorded_items(exam: str = ENGLISH_EXAM) -> tuple[NativeExamItem, ...]:
    """Every converted item of the exam's first recorded round, numbered in source order."""
    envelope = DocxBuildEnvelope.model_validate_json(
        (_RECORDINGS / exam / "round1.json").read_text()
    )
    return tuple(
        native_item(produced).model_copy(
            update={"item_id": f"item_{number:03d}", "sequence": number}
        )
        for number, produced in enumerate(
            (p for p in envelope.items if p.outcome == "converted"), start=1
        )
    )


def recorded_document(
    parents: tuple[NativeExamParent, ...] = (),
    *,
    items: tuple[NativeExamItem, ...] | None = None,
) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Recorded exam",
        items=items if items is not None else recorded_items(),
        parents=parents,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def item_numbers(items: tuple[NativeExamItem, ...], kind: NativeExamItemKind) -> list[int]:
    """Sequence numbers of the items of one kind, in order."""
    return [item.sequence for item in items if item.kind is kind]


def parent_over(parent_id: str, instruction: str, *numbers: int) -> NativeExamParent:
    return NativeExamParent(
        parent_id=parent_id,
        instruction=(NativeParagraph(segments=(NativeTextSegment(text=instruction),)),),
        item_ids=tuple(f"item_{number:03d}" for number in numbers),
    )
