"""A question holding only a points-bearing heading converts instead of crashing.

TASK-SKRIPT-40-04-24 (recorded by the TASK-SKRIPT-39-10-01 lead): the grouping gives a
question only its points-bearing section heading, such as "Vocabulary Matching (9 points)".
``assign_points_lines`` moved that heading to the next question's part, leaving the
question anchorless, and ``question_families`` raised ``IndexError``. The heading stays
with its question, so the import converts with the question kept at its heading.
"""

from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import question_families
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    claim_inner_chunks,
    manifest_from_output,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import (
    assign_points_lines,
    manifest_questions,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_instructions import (
    assign_question_headings,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines

pytestmark = pytest.mark.unit

_HEADING_ONE = "Vocabulary Matching (9 points)"
_BODY_ONE = "Match each word with its definition."
_HEADING_TWO = "Language Choice (6 points)"
_BODY_TWO = "Choose the correct alternative."


def _chunks() -> tuple[DocxChunk, ...]:
    return (
        DocxChunk("body:0001", "heading", _HEADING_ONE, _HEADING_ONE),
        DocxChunk("body:0002", "paragraph", _BODY_ONE, _BODY_ONE),
        DocxChunk("body:0003", "heading", _HEADING_TWO, _HEADING_TWO),
        DocxChunk("body:0004", "paragraph", _BODY_TWO, _BODY_TWO),
    )


def _grouped(chunks: tuple[DocxChunk, ...]) -> ExamManifest:
    """The recorded shape: q1 and q3 hold only their points-bearing heading."""
    raw: dict[str, JsonValue] = {
        "title_anchors": [],
        "header_anchors": [],
        "questions": [
            {
                "id": "q1",
                "anchors": ["body:0001"],
                "subpart_anchors": [],
                "answer_key_anchors": [],
            },
            {
                "id": "q2",
                "anchors": ["body:0002"],
                "subpart_anchors": [],
                "answer_key_anchors": [],
            },
            {
                "id": "q3",
                "anchors": ["body:0003"],
                "subpart_anchors": [],
                "answer_key_anchors": [],
            },
            {
                "id": "q4",
                "anchors": ["body:0004"],
                "subpart_anchors": [],
                "answer_key_anchors": [],
            },
        ],
        "shared_contexts": [],
    }
    return manifest_from_output(raw, chunks)


def _normalised(manifest: ExamManifest, chunks: tuple[DocxChunk, ...]) -> ExamManifest:
    """The manifest as the pipeline builds it before batching (pipeline :215)."""
    return claim_inner_chunks(
        assign_points_lines(assign_question_headings(manifest, chunks), chunks), chunks
    )


def test_a_question_holding_only_its_points_heading_is_kept_at_that_heading() -> None:
    chunks = _chunks()
    normalised = _normalised(_grouped(chunks), chunks)

    families = question_families(normalised, chunks)
    by_id = {family.question_id: family for family in families}
    assert [family.question_id for family in families] == ["q1", "q2", "q3", "q4"]
    assert by_id["q1"].question_anchors == ("body:0001",)
    assert by_id["q1"].position == 0
    assert "body:0001" in by_id["q1"].claims
    assert by_id["q3"].question_anchors == ("body:0003",)
    assert normalised.question("q1").anchors == ("body:0001",)
    assert normalised.question("q3").anchors == ("body:0003",)


def _item(anchors: list[str], text: str, points: int) -> dict[str, JsonValue]:
    return {
        "source_anchors": list(anchors),
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "free_text",
        "key_source": None,
        "facit_text": None,
        "printed_label": None,
        "body": [
            {"segments": [{"kind": "text", "text": line, "accepted_values": []}]}
            for line in text.split("\n")
        ],
        "points": points,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }


def test_a_question_holding_only_its_points_heading_keeps_its_points() -> None:
    chunks = _chunks()
    normalised = _normalised(_grouped(chunks), chunks)
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=manifest_questions(normalised),
    )

    admit_batch(
        {
            "items": [
                _item(["body:0001"], f"{_HEADING_ONE}\n{_BODY_ONE}", 9),
                _item(["body:0002"], _BODY_ONE, 9),
                _item(["body:0003"], f"{_HEADING_TWO}\n{_BODY_TWO}", 6),
                _item(["body:0004"], _BODY_TWO, 6),
            ]
        },
        state,
    )
    document = state.result().document
    assert all(i.review.parse_origin is NativeParseOrigin.LLM_PARSED for i in document.items)
    assert not [
        e
        for e in state.events
        if e.code in {"question_split", "questions_merged", "anchor_conflict"}
    ]
    assert [item.points for item in document.items] == [9, 9, 6, 6]
    assert body_text_lines(document.items[0].body)[0].startswith("Vocabulary Matching")
    NativeExamDocument.model_validate(document.model_dump())
