"""Synthetic producer boundaries: one heading split preserves words and score meaning.

These are real admission/assembly paths, not model recordings or browser proof.
"""

from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_header import apply_header
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    HeaderAnchor,
    ManifestQuestion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class HeadingCase:
    heading: str
    questions: int
    words: tuple[str, ...]
    label: str | None = None
    item_points: int | float | tuple[int, ...] | None = None
    parent_total: int | None = None
    header_total: int | None = None
    rubric: bool = False
    matching: bool = False
    metadata_only: bool = False
    instruction: bool = False


def _chunk(number: int, kind: str, text: str) -> DocxChunk:
    return DocxChunk(f"body:{number:04d}", kind, text, text)


def _produced(anchor: str, prompt: str) -> dict[str, JsonValue]:
    return {
        "source_anchors": [anchor],
        "outcome": "converted",
        "review_reason": None,
        "kind": "free_text",
        "printed_label": None,
        "body": [{"segments": [{"kind": "text", "text": prompt, "accepted_values": []}]}],
        "key_source": None,
        "facit_text": None,
        "points": None,
        "choices": [],
    }


@pytest.mark.parametrize(
    "case",
    [
        HeadingCase(
            "Del 1: litteraturhistoria, 15 poäng",
            2,
            ("Del 1: litteraturhistoria",),
            parent_total=15,
        ),
        HeadingCase("Poäng: 15 poäng", 1, (), item_points=15, header_total=15, metadata_only=True),
        HeadingCase("2. Tempus (3 p)", 1, ("Tempus",), label="2", item_points=3),
        HeadingCase("2. (3 p)", 1, (), label="2", item_points=3),
        HeadingCase("Fråga 2 (3 p)", 1, (), label="Fråga 2", item_points=3),
        HeadingCase("2. (3 p)", 2, (), item_points=(2, 1)),
        HeadingCase("Tempus", 1, ("Tempus",), instruction=True),
        HeadingCase("2. Tempus (3 p)", 1, ("Tempus",), label="2", item_points=3, rubric=True),
        HeadingCase("2. Begrepp (3 p)", 1, ("Begrepp",), label="2", item_points=3, matching=True),
        HeadingCase(
            "Del 2: grammatik och språkstrukturer, 16 poäng",
            2,
            ("Del 2: grammatik och språkstrukturer",),
            parent_total=16,
            header_total=15,
        ),
        HeadingCase(
            "Del 3: kortsvar, 5 poäng", 2, ("Del 3: kortsvar",), parent_total=5, header_total=5
        ),
    ],
    ids=[
        "pointed-section",
        "bare-total-header",
        "pointed-question",
        "number-points-only",
        "word-number-points-only",
        "bare-part-total-no-parent",
        "plain-heading",
        "estimated-rubric",
        "explicit-matching-conflict",
        "heading-wins-total-conflict",
        "same-heading-header-total",
    ],
)
def test_heading_family_keeps_structure_metadata_and_native_scores_coherent(
    case: HeadingCase,
) -> None:
    heading = _chunk(2, "paragraph" if case.metadata_only else "heading", case.heading)
    prompts = tuple(
        _chunk(number, "paragraph", f"Beskriv begrepp {number}.")
        for number in range(3, 3 + case.questions)
    )
    chunks = (_chunk(1, "heading", "Språkprov"), heading, *prompts)
    header_anchor = heading.anchor
    if case.header_total is not None and not case.metadata_only:
        header_anchor = "body:0099"
        chunks += (_chunk(99, "paragraph", f"Poäng: {case.header_total} poäng"),)
    # Only the explicit matching conflict owns the heading before admission. All
    # pointed headings are omitted by the producer and must survive T1/T2.
    questions = tuple(
        ((heading.anchor, prompt.anchor) if case.matching else (prompt.anchor,))
        for prompt in prompts
    )
    state = DocxBuildState(
        origin_kind="docx_import",
        job_id=uuid4(),
        document_id=uuid4(),
        filename="sprakprov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=questions,
        header_anchors=(
            frozenset({header_anchor}) if case.header_total is not None else frozenset()
        ),
    )
    produced = [_produced(prompt.anchor, prompt.text) for prompt in prompts]
    if case.rubric:
        produced[0]["facit_text"] = "Visar förståelse för tempus."
        produced[0]["criteria"] = [{"text": "Visar förståelse för tempus.", "points": None}]
    if case.matching:
        produced[0].update(
            {
                "source_anchors": [heading.anchor, prompts[0].anchor],
                "kind": "matching",
                "points": 5,
                "key_source": "invented",
                "match_left": ["presens", "preteritum", "perfekt"],
                "match_right": ["nutid", "dåtid", "har gjort"],
                "match_pairs": [
                    {"left": "presens", "right": "nutid"},
                    {"left": "preteritum", "right": "dåtid"},
                    {"left": "perfekt", "right": "har gjort"},
                ],
            }
        )
    admit_batch(
        {
            "title": {"text": "Språkprov", "source_anchors": ["body:0001"]},
            "items": [item for item in produced],
            "instructions": (
                [{"text": heading.text, "source_anchors": [heading.anchor]}]
                if case.instruction
                else []
            ),
        },
        state,
    )
    document = state.result(questions=questions).document
    manifest = ExamManifest(
        questions=tuple(
            ManifestQuestion(f"q{number}", anchors, (), ())
            for number, anchors in enumerate(questions, 1)
        ),
        contexts=(),
        title_anchors=("body:0001",),
        header=(
            (
                HeaderAnchor(
                    header_anchor,
                    "part_total",
                    tuple(f"q{n}" for n in range(1, case.questions + 1)),
                ),
            )
            if case.header_total is not None
            else ()
        ),
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=(),
    )
    document = apply_header(document, manifest, chunks, course_key=None, courses=()).document
    # model_copy does not validate: enforce the final persisted native contract.
    NativeExamDocument.model_validate(document.model_dump())

    assert len(document.items) == case.questions
    assert document.instructions == ()
    if case.parent_total is not None:
        assert len(document.parents) == 1
        parent = document.parents[0]
        assert parent.printed_total == case.parent_total
        assert body_text_lines(parent.instruction) == case.words
        assert parent.item_ids == tuple(item.item_id for item in document.items)
        assert all(item.printed_label is None for item in document.items)
        assert all(item.points != case.parent_total for item in document.items)
    else:
        assert document.parents == ()
        expected_points = (
            case.item_points
            if isinstance(case.item_points, tuple)
            else (case.item_points,) * case.questions
        )
        for item, prompt, points in zip(document.items, prompts, expected_points, strict=True):
            assert item.printed_label == case.label
            assert item.points == points
            assert item.plain_text_lines() == (*case.words, prompt.text)
    if case.rubric:
        assert [(c.text, c.points) for c in document.items[0].criteria] == [
            ("Visar förståelse för tempus.", 3)
        ]
    if case.matching:
        item = document.items[0]
        assert item.tick_points == Decimal("1")
        assert not item.points_estimated
        assert item.review.reasons == ()
