"""Kept-answer links are refused in document and parent instructions (TASK-SKRIPT-40-04-13 H1b).

A kept gap link is valid only on a text run of a gap_fill or inline_choice
question body. Shared instructions carry no gaps, so a text run with
``kept_gap_id`` there fails at the model boundary, the same way a placed gap
segment does. The same word without the link stays accepted.
"""

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
)


def kept_body() -> tuple[NativeParagraph, ...]:
    return (
        NativeParagraph(
            heading_level=None,
            segments=(NativeTextSegment(text="Läs texten.", marks=(), kept_gap_id="gap_002"),),
        ),
    )


def plain_body() -> tuple[NativeParagraph, ...]:
    return (
        NativeParagraph(
            heading_level=None,
            segments=(NativeTextSegment(text="Läs texten.", marks=()),),
        ),
    )


def document_with_instructions(instructions: tuple[NativeParagraph, ...]) -> NativeExamDocument:
    payload = make_document(make_free_text_item()).model_dump(mode="json")
    payload["instructions"] = [
        {
            "heading_level": None,
            "segments": [
                {"kind": "text", "text": segment.text, "marks": list(segment.marks)}
                | ({"kept_gap_id": segment.kept_gap_id} if segment.kept_gap_id else {})
                for paragraph in instructions
                for segment in paragraph.segments
                if isinstance(segment, NativeTextSegment)
            ],
        }
    ]
    return NativeExamDocument.model_validate(payload)


class TestDocumentInstructionsRefuseKeptLinks:
    def test_kept_run_in_document_instructions_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="kept"):
            document_with_instructions(kept_body())

    def test_same_word_without_the_link_is_accepted(self) -> None:
        document = document_with_instructions(plain_body())

        assert document.instructions == plain_body()


class TestParentInstructionsRefuseKeptLinks:
    def test_kept_run_in_parent_instruction_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="kept"):
            NativeExamParent(parent_id="parent_001", place=0, instruction=kept_body())

    def test_same_word_without_the_link_is_accepted(self) -> None:
        parent = NativeExamParent(parent_id="parent_001", place=0, instruction=plain_body())

        assert parent.instruction == plain_body()

    def test_kept_run_in_a_document_parent_is_refused(self) -> None:
        document = make_document(make_free_text_item())
        payload = document.model_dump(mode="json")
        payload["parents"] = [
            {
                "parent_id": "parent_001",
                "place": 0,
                "instruction": [
                    {
                        "heading_level": None,
                        "segments": [
                            {
                                "kind": "text",
                                "text": "Läs texten.",
                                "marks": [],
                                "kept_gap_id": "gap_002",
                            },
                        ],
                    }
                ],
                "item_ids": [],
            }
        ]
        with pytest.raises(ValidationError, match="kept"):
            NativeExamDocument.model_validate(payload)
