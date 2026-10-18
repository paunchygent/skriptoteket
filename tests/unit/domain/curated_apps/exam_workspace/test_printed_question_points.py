"""Synthetic grouping/build seams: printed question points own coherent native scores."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_assembly import (
    with_type_check_mark,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import question_families
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_header import apply_header
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    manifest_from_output,
    question_source,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class PrintedCase:
    source: str
    scores: tuple[int, ...] = (5,)
    expected: tuple[float, ...] = (3,)
    kind: str = "free_text"
    heading_owned: bool = False
    criteria: tuple[int, ...] = ()
    printed: float = 3
    type_conflict: bool = False
    separate_questions: bool = False


@pytest.mark.parametrize(
    "case",
    [
        PrintedCase("question_total"),
        PrintedCase("part_total"),
        PrintedCase("heading"),
        PrintedCase("heading", heading_owned=True),
        PrintedCase("question_total", kind="rubric"),
        PrintedCase("heading", kind="rubric", heading_owned=True),
        PrintedCase("question_total", kind="matching"),
        PrintedCase("heading", kind="matching", heading_owned=True),
        PrintedCase("absent", expected=(5,)),
        PrintedCase("heading", (4,), (4,), kind="rubric_overflow"),
        PrintedCase("heading", kind="rubric_missing_total", heading_owned=True),
        PrintedCase("question_total", (3,), kind="rubric", criteria=(1, 2)),
        PrintedCase("heading", heading_owned=True, type_conflict=True),
        # The heading prints 3 over both questions under it, wherever the grouping put it.
        PrintedCase("heading", (1, 5), (2, 1), heading_owned=True, separate_questions=True),
    ],
    ids=[
        "question-line-overrides-build",
        "single-question-part-overrides-build",
        "omitted-heading-overrides-build",
        "owned-heading-overrides-build",
        "question-line-rubric-rescaled",
        "owned-heading-rubric-rescaled",
        "question-line-matching-rescaled",
        "owned-heading-matching-rescaled",
        "no-print-retains-build",
        "impossible-rubric-goes-to-teacher",
        "owned-heading-rubric-without-build-total",
        "matching-total-preserves-uneven-rubric",
        "owned-heading-preserves-repeated-type-conflict-mark",
        "question-owned-heading-opens-a-part-over-the-questions-under-it",
    ],
)
def test_printed_question_points_own_scores_and_never_become_exam_text(case: PrintedCase) -> None:
    heading = case.source == "heading"
    header = case.source in {"question_total", "part_total"}
    metadata_anchor = "body:0002"
    metadata_text = (
        f"2. Tempus ({case.printed:g} p)" if heading else f"Poäng: {case.printed:g} poäng"
    )
    prompts = tuple(
        DocxChunk(
            f"body:{i + 3:04d}",
            "paragraph",
            f"Förklara tempus {i + 1}.",
            f"Förklara tempus {i + 1}.",
        )
        for i in range(len(case.scores))
    )
    chunks = (
        DocxChunk("body:0001", "heading", "Språkprov", "Språkprov"),
        *(
            (
                DocxChunk(
                    metadata_anchor,
                    "heading" if heading else "paragraph",
                    metadata_text,
                    metadata_text,
                ),
            )
            if heading
            else ()
        ),
        *prompts,
        *(
            (DocxChunk(metadata_anchor, "paragraph", metadata_text, metadata_text),)
            if header
            else ()
        ),
    )
    question_anchors = [p.anchor for p in prompts]
    if heading and case.heading_owned:
        question_anchors.insert(0, metadata_anchor)
    raw: dict[str, JsonValue] = {
        "title_anchors": ["body:0001"],
        "header_anchors": (
            [{"anchor": metadata_anchor, "kind": case.source, "governs": ["q1"]}] if header else []
        ),
        "questions": [
            {
                "id": f"q{index + 1}",
                "anchors": [anchor for anchor in own],
                "subpart_anchors": [],
                "answer_key_anchors": [],
            }
            for index, own in enumerate(
                [[metadata_anchor, prompts[0].anchor], [prompts[1].anchor]]
                if case.separate_questions
                else [question_anchors]
            )
        ],
        "shared_contexts": [],
    }
    manifest = manifest_from_output(raw, chunks)
    if header:
        assert [(h.kind, h.governs) for h in manifest.header] == [(case.source, ("q1",))]
        assert metadata_text not in question_source(manifest, chunks, "q1")
        assert all(
            metadata_anchor not in f.claims | f.reads for f in question_families(manifest, chunks)
        )
    questions = tuple(q.anchors for q in manifest.questions)
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="tempus.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=questions,
        header_anchors=frozenset(h.anchor for h in manifest.header),
    )
    produced: list[JsonValue] = []
    for index, (prompt, score) in enumerate(zip(prompts, case.scores, strict=True)):
        anchors = [prompt.anchor]
        if heading and case.heading_owned and index == 0 and not case.separate_questions:
            anchors.insert(0, metadata_anchor)
        item: dict[str, JsonValue] = {
            "source_anchors": [anchor for anchor in anchors],
            "outcome": "converted",
            "review_reason": None,
            "kind": "matching" if case.kind == "matching" else "free_text",
            "printed_label": None,
            "body": [{"segments": [{"kind": "text", "text": prompt.text, "accepted_values": []}]}],
            "key_source": None,
            "facit_text": None,
            "points": score,
            "choices": [],
        }
        if case.kind == "rubric_missing_total":
            item["points"] = None
        if case.kind.startswith("rubric"):
            item["facit_text"] = "Visar förståelse för tempus."
            item["criteria"] = (
                [{"text": f"Bedömning {n}.", "points": 1} for n in range(4)]
                if case.kind == "rubric_overflow"
                else [{"text": "Visar förståelse för tempus.", "points": score}]
            )
        if case.criteria:
            item["criteria"] = [
                {"text": f"Bedömning {n}.", "points": points}
                for n, points in enumerate(case.criteria)
            ]
        if case.kind == "matching":
            item.update(
                {
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
        produced.append(item)
    admit_batch(
        {
            "title": {"text": "Språkprov", "source_anchors": ["body:0001"]},
            "items": produced,
            "instructions": [],
        },
        state,
    )
    if case.type_conflict:
        state.kept_conflicts.update(question_anchors)
        with_type_check_mark(state)
        for accepted_item, _ in state.accepted:
            assert accepted_item.review.confidence is not None
            assert 0 < accepted_item.review.confidence < 0.95
    admitted = tuple(item for item, _ in state.accepted)
    document = apply_header(
        state.result(questions=questions).document, manifest, chunks, course_key=None, courses=()
    ).document
    NativeExamDocument.model_validate(document.model_dump())
    assert len(document.items) == len(prompts)
    assert tuple(item.points for item in document.items) == case.expected
    assert document.instructions == ()
    rendered = [line for item in document.items for line in item.plain_text_lines()]
    rendered.extend(
        line for parent in document.parents for line in body_text_lines(parent.instruction)
    )
    assert all("Poäng:" not in line and f"{case.printed:g} p" not in line for line in rendered)
    assert all(prompt.text in rendered for prompt in prompts)
    assert not any(
        "AI-tolkningen anger" in reason for item in document.items for reason in item.review.reasons
    )
    if case.kind.startswith("rubric"):
        assert sum(c.points for c in document.items[0].criteria) == case.expected[0]
    if case.kind.endswith("overflow"):
        assert all(item.review.state.value == "review_required" for item in document.items)
        assert all(any("3" in reason for reason in item.review.reasons) for item in document.items)
    if case.criteria:
        assert tuple(c.points for c in document.items[0].criteria) == case.criteria
    if case.kind == "matching":
        assert document.items[0].tick_points == Decimal("1")
    if case.type_conflict:
        assert document.items[0].review == admitted[0].review
