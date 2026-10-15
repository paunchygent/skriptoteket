"""Native exam documents built from the fresh live v14 recordings of the corpus exams.

Each exam's recordings are the raw replies of one live run: first-wave envelopes convene
the label batches, second-wave envelopes answer the questions the first pass escalated.
An anchor may appear in more than one envelope when the run rescanned a question, so the
final converted reply for an anchor is the one kept. This reads the raw model replies
directly and tests native-document invariants; pipeline admission is exercised elsewhere.
"""

import json
from pathlib import Path
from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.exam_document_language import Language
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)

_RECORDINGS = Path("tests/fixtures/exam_conversion/docx_key_provenance_v14")
ENGLISH_EXAM = "bf26_english_1_unit_test_kap_1_2_med_facit"


def recorded_exam_language(exam: str) -> Language:
    """The corpus exam's own language, which conversion infers from its document text."""
    if "english" in exam:
        return "en"
    return "sv"


def recorded_converted_items(exam: str) -> tuple[ProducedItem, ...]:
    """Every converted item the exam's envelopes returned, in source order.

    Scanning the envelopes in name order makes each later converted reply for one first
    source anchor replace the earlier one; a reply that is not converted replaces nothing.
    """
    latest: dict[str, ProducedItem] = {}
    for path in sorted((_RECORDINGS / exam).glob("docx_w*.json")):
        content = json.loads(path.read_text())
        for raw in content["items"]:
            # Only a converted reply is a native item; a conflict or review reply is not one.
            if not isinstance(raw, dict) or raw.get("outcome") != "converted":
                continue
            produced = ProducedItem.model_validate(raw)
            latest[produced.source_anchors[0]] = produced
    ordered = sorted(latest.values(), key=lambda produced: produced.source_anchors[0])
    return tuple(ordered)


def recorded_items(exam: str = ENGLISH_EXAM) -> tuple[NativeExamItem, ...]:
    """Every converted item of the exam, numbered in source order."""
    language = recorded_exam_language(exam)
    return tuple(
        native_item(produced, language=language).model_copy(
            update={"item_id": f"item_{number:03d}", "sequence": number}
        )
        for number, produced in enumerate(recorded_converted_items(exam), start=1)
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
        instruction=(
            NativeParagraph(
                heading_level=None, segments=(NativeTextSegment(text=instruction, marks=()),)
            ),
        ),
        item_ids=tuple(f"item_{number:03d}" for number in numbers),
    )
