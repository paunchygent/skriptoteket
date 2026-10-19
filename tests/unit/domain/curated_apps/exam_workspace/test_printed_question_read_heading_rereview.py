"""Rereview R7/R8 full assembly: a reader-consumed heading label leaves the text.

Both cases build the points plan with the real reader, never a hand-made
``PrintedPoints``, and run the real ``apply_printed_points`` and
``assemble_build_result``. Four one-point rubric criteria settle 4 points and
report that the printed 3 cannot be distributed.
"""

from dataclasses import replace
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import assemble_build_result
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_item import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import printed_points_plan
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem

pytestmark = pytest.mark.unit

_READ_LABEL_REASON = "Tryckta 3 poäng kan inte fördelas på frågans bedömning. Kontrollera poängen."


def _assembled_item(heading: str, prompt: str, body_text: str) -> NativeExamItem:
    chunks = (
        DocxChunk("body:0001", "heading", heading, heading),
        DocxChunk("body:0002", "paragraph", prompt, prompt),
    )
    questions = (("body:0001", "body:0002"),)
    plan = printed_points_plan(chunks, questions)
    produced = ProducedItem.model_validate(
        {
            "source_anchors": ["body:0001", "body:0002"],
            "outcome": "converted",
            "review_reason": None,
            "kind": "free_text",
            "key_source": None,
            "facit_text": "Visar förståelse för tempus.",
            "body": [{"segments": [{"kind": "text", "text": body_text, "accepted_values": []}]}],
            "points": 4,
            "choices": [],
            "criteria": [{"text": f"Kriterium {number}.", "points": 1} for number in range(4)],
        }
    )
    aligned = aligned_native_item(produced, language="sv", foreign_chunks=())
    # Explicit source-shaped provenance: the one body paragraph renders the heading
    # in the answer-line case, and the prompt otherwise. No wording-based alignment.
    aligned = replace(aligned, chunks=("body:0001" if prompt == "__________" else "body:0002",))
    result = assemble_build_result(
        document_id=uuid4(),
        filename="tempus.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        accepted=((aligned, questions[0]),),
        review_reasons={},
        questions=questions,
        printed=plan,
    )
    (item,) = result.document.items
    return item


def test_a_question_owned_points_only_heading_leaves_whole() -> None:
    # R8: the reader consumed "Poäng: (3 p)" as the question's points, so the
    # heading leaves whole while the printed 3 stays in the source record.
    item = _assembled_item("Poäng: (3 p)", "Förklara tempus.", "Förklara tempus.")

    assert item.plain_text_lines() == ("Förklara tempus.",)
    assert item.points == 4
    assert [criterion.points for criterion in item.criteria] == [1, 1, 1, 1]
    assert item.leftover_points_text is None
    assert item.source_points == 3
    assert _READ_LABEL_REASON in item.review.reasons


def test_a_read_heading_as_the_only_paragraph_loses_its_label() -> None:
    # R7: the reader consumed "(3 p)" from the heading, so the sole surviving
    # plain paragraph loses the label with no leftover candidate.
    item = _assembled_item("2. Förklara tempus (3 p)", "__________", "Förklara tempus (3 p)")

    assert item.plain_text_lines() == ("Förklara tempus",)
    assert item.points == 4
    assert [criterion.points for criterion in item.criteria] == [1, 1, 1, 1]
    assert item.leftover_points_text is None
