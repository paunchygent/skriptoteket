"""An exam-owned context that governs no question is exam-wide text (ruling 2026-10-18 b).

It is published once in the document's instructions and never joins a section parent's
heading run or instruction, whichever instruction a build reply lists it in. Exam metadata
stays excluded. The rule follows the grouping's owner and governs, never the line's wording.
"""

from collections.abc import Mapping
from types import MappingProxyType
from uuid import UUID

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_assembly import (
    exam_metadata_anchors,
    exam_wide_anchors,
    governed_anchors,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline_batches import (
    batch_state,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionJob,
    DocxConversionRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildResult
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import (
    ConversionBatch,
    question_families,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    ManifestQuestion,
    SharedContext,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeParagraph
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)

pytestmark = pytest.mark.unit

_OVERVIEW = "Översikt över provet:"
_NAME = "Namn: ______"
_DEL = "DEL A: ORDKLASSER"
_Q1 = "1. Förklara vad ett substantiv är. (5 p)"
_Q2 = "2. Förklara vad ett verb är. (5 p)"
_DEL_B = "DEL B: SATSDELAR"
_Q3 = "3. Förklara vad ett subjekt är. (5 p)"
_Q4 = "4. Förklara vad ett predikat är. (5 p)"
_TEXTS = {
    "body:0001": _NAME,
    "body:0002": _OVERVIEW,
    "body:0003": _DEL,
    "body:0004": _Q1,
    "body:0005": _Q2,
    "body:0006": _DEL_B,
    "body:0007": _Q3,
    "body:0008": _Q4,
}
_QUESTIONS = {"q1": "body:0004", "q2": "body:0005", "q3": "body:0007", "q4": "body:0008"}
_FREE_TEXT = frozenset({NativeExamItemKind.FREE_TEXT})


def _run(overview_kind: str) -> DocxConversionRun:
    chunks = tuple(
        DocxChunk(
            anchor,
            {"body:0002": overview_kind, "body:0003": "heading", "body:0006": "heading"}.get(
                anchor, "paragraph"
            ),
            text,
            text,
        )
        for anchor, text in _TEXTS.items()
    )
    job = DocxConversionJob(
        job_id=UUID(int=1),
        worker_id="worker",
        document_id=UUID(int=2),
        filename="prov.docx",
        source_sha256="0" * 64,
        source_docx=b"",
        chunks=chunks,
        course_key=None,
    )
    run = DocxConversionRun(job, 0.0)
    run.contexts = (
        SharedContext("body:0001", "exam_metadata", "exam", ()),
        SharedContext("body:0002", "other", "exam", ()),
        SharedContext("body:0003", "section_instruction", "exam", ("q1", "q2")),
        SharedContext("body:0006", "section_instruction", "exam", ("q3", "q4")),
    )
    manifest = ExamManifest(
        questions=tuple(ManifestQuestion(q, (a,), (), ()) for q, a in _QUESTIONS.items()),
        contexts=run.contexts,
        title_anchors=(),
        header=(),
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=(),
    )
    run.context_anchors = frozenset(context.anchor for context in run.contexts)
    run.families = question_families(manifest, chunks)
    run.kinds = dict.fromkeys(_QUESTIONS, NativeExamItemKind.FREE_TEXT)
    return run


def _item(anchor: str) -> dict[str, JsonValue]:
    return {
        "source_anchors": [anchor],
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "free_text",
        "key_source": None,
        "facit_text": None,
        "printed_label": anchor[-1],
        "body": [{"segments": [{"kind": "text", "text": _TEXTS[anchor], "accepted_values": []}]}],
        "points": 5,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }


def _build(
    overview_kind: str, instructions: tuple[tuple[str, ...], ...]
) -> tuple[DocxBuildResult, DocxConversionRun]:
    run = _run(overview_kind)
    claims = frozenset().union(*(f.claims for f in run.families))
    batch = ConversionBatch("w1-01", _FREE_TEXT, tuple(_QUESTIONS), claims, frozenset())
    state = batch_state(run, batch)
    owned = state.owned
    admit_batch(
        {
            "items": [_item(anchor) for anchor in _QUESTIONS.values()],
            "answer_key_anchors": [],
            "title": None,
            "instructions": [
                {
                    "text": "\n".join(_TEXTS[a] for a in anchors),
                    "source_anchors": [a for a in anchors if a in owned],
                }
                for anchors in instructions
            ],
        },
        state,
    )
    governed: Mapping[str, frozenset[str]] = MappingProxyType(
        governed_anchors(run.contexts, run.families)
    )
    result = state.result(
        governed=governed,
        questions=tuple(f.question_anchors for f in run.families),
        exam_wide=exam_wide_anchors(run.contexts, run.families),
        exam_metadata=exam_metadata_anchors(run.contexts),
    )
    return result, run


def _lines(paragraphs: tuple[NativeParagraph, ...]) -> list[str]:
    return [
        "".join(getattr(segment, "text", "") for segment in paragraph.segments)
        for paragraph in paragraphs
    ]


@pytest.mark.parametrize("overview_kind", ["paragraph", "heading"])
@pytest.mark.parametrize(
    "instructions",
    [
        (("body:0002", "body:0003"), ("body:0006",)),
        (("body:0002",), ("body:0003",), ("body:0006",)),
        (("body:0003",), ("body:0006",)),
    ],
    ids=["listed_with_section", "listed_alone", "not_listed"],
)
def test_ungoverned_exam_text_shows_once_in_document_instructions_and_in_no_parent(
    overview_kind, instructions
):
    result, run = _build(overview_kind, instructions)
    document = result.document
    shown = [
        *_lines(document.instructions),
        *(line for item in document.items for line in item.plain_text_lines()),
        *(line for parent in document.parents for line in _lines(parent.instruction)),
    ]

    assert _lines(document.instructions) == [_OVERVIEW]
    assert shown.count(_OVERVIEW) == 1
    assert [_lines(parent.instruction) for parent in document.parents] == [[_DEL], [_DEL_B]]
    assert [len(parent.item_ids) for parent in document.parents] == [2, 2]
    assert not [line for line in shown if line.startswith("Namn")]
    assert len(document.items) == 4
    assert "body:0002" in exam_wide_anchors(run.contexts, run.families)
