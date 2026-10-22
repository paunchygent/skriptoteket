"""Synthetic producer replies challenge heading ownership and header exclusion.

These tests exercise the real manifest post-step, admission and assembly, without
claiming live model or application proof.
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
    manifest_from_output,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_instructions import (
    assign_question_headings,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines

pytestmark = pytest.mark.unit

_TITLE = "Verbprov"
_HEADING = "2. Tempus (3 p)"
_PROMPT = "Beskriv skillnaden mellan presens och preteritum."
_HEADER = "Total: 36 poäng"


def _chunk(number: int, kind: str, text: str) -> DocxChunk:
    return DocxChunk(f"body:{number:04d}", kind, text, text)


def _item(
    anchors: list[str], text: str = _PROMPT, points: JsonValue = None
) -> dict[str, JsonValue]:
    return {
        "source_anchors": [anchor for anchor in anchors],
        "outcome": "converted",
        "review_reason": None,
        "kind": "free_text",
        "printed_label": None,
        "body": [{"segments": [{"kind": "text", "text": text, "accepted_values": []}]}],
        "key_source": None,
        "facit_text": None,
        "points": points,
        "choices": [],
    }


def _manifest(
    chunks: tuple[DocxChunk, ...], *, heading: bool = True, question_count: int = 1
) -> ExamManifest:
    ids = [f"q{n}" for n in range(1, question_count + 1)]
    raw: dict[str, JsonValue] = {
        "title_anchors": ["body:0001"],
        "header_anchors": [],
        "questions": [
            {
                "id": qid,
                "anchors": [f"body:{n + 3:04d}"],
                "subpart_anchors": [],
                "answer_key_anchors": [],
            }
            for n, qid in enumerate(ids)
        ],
        "shared_contexts": (
            [
                {
                    "anchor": "body:0002",
                    "scope": "section_instruction",
                    "owner": "exam",
                    "governs": [qid for qid in ids],
                }
            ]
            if heading
            else []
        ),
    }
    return manifest_from_output(raw, chunks)


def _state(
    chunks: tuple[DocxChunk, ...],
    *,
    questions: tuple[tuple[str, ...], ...],
    headers: frozenset[str] = frozenset(),
    governing: frozenset[str] = frozenset(),
) -> DocxBuildState:
    state = DocxBuildState(
        origin_kind="docx_import",
        job_id=uuid4(),
        document_id=uuid4(),
        filename="verbprov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=questions,
        header_anchors=headers,
        governing=governing,
    )
    title = next((c for c in chunks if c.text == _TITLE), None)
    if title is not None:
        admit_batch({"title": {"text": title.text, "source_anchors": [title.anchor]}}, state)
    return state


@pytest.mark.parametrize("grouped_as_context", [True, False], ids=["section", "unplaced"])
@pytest.mark.parametrize(
    ("heading", "label", "points"),
    [(_HEADING, "2", 3), ("2. Tempus", "2", None), ("Tempus 3 poäng", None, 3)],
    ids=["number-and-points", "number-only", "points-only"],
)
def test_numbered_pointed_heading_opens_its_question_without_a_stray_review_item(
    grouped_as_context: bool, heading: str, label: str | None, points: int | None
) -> None:
    chunks = (
        _chunk(1, "heading", _TITLE),
        _chunk(2, "heading", heading),
        _chunk(3, "paragraph", _PROMPT),
    )
    manifest = assign_question_headings(_manifest(chunks, heading=grouped_as_context), chunks)
    families = question_families(manifest, chunks)
    own = tuple(family.question_anchors for family in families)
    state = _state(chunks, questions=own)
    state.claimable = frozenset().union(*(family.claims for family in families))
    # Even a producer that omits the heading must not lose its question label or points.
    admit_batch(
        {
            "title": {"text": _TITLE, "source_anchors": ["body:0001"]},
            "items": [_item(["body:0003"])],
        },
        state,
    )
    document = state.result(questions=own).document

    assert len(document.items) == 1
    item = document.items[0]
    assert item.printed_label == label
    assert item.points == points
    assert "Tempus" in " ".join(item.plain_text_lines())
    assert _PROMPT in " ".join(item.plain_text_lines())
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert document.parents == ()
    assert document.instructions == ()


@pytest.mark.parametrize("grouped_as_context", [True, False], ids=["section", "unplaced"])
def test_numbered_pointed_heading_over_three_questions_is_only_the_parent_instruction(
    grouped_as_context: bool,
) -> None:
    chunks = (
        _chunk(1, "heading", _TITLE),
        _chunk(2, "heading", _HEADING),
        *(_chunk(n, "paragraph", f"Beskriv verbform {n}.") for n in range(3, 6)),
    )
    manifest = assign_question_headings(
        _manifest(chunks, heading=grouped_as_context, question_count=3), chunks
    )
    own = tuple(question.anchors for question in manifest.questions)
    governing = frozenset({"body:0002"}) if grouped_as_context else frozenset()
    state = _state(chunks, questions=own, governing=governing)
    admit_batch(
        {
            "title": {"text": _TITLE, "source_anchors": ["body:0001"]},
            "instructions": [{"text": _HEADING, "source_anchors": ["body:0002"]}],
            "items": [_item([chunk.anchor], chunk.text, 1) for chunk in chunks[2:]],
        },
        state,
    )
    governed = {"body:0002": frozenset(c.anchor for c in chunks[2:])} if grouped_as_context else {}
    document = state.result(governed=governed, questions=own).document

    assert len(document.items) == 3
    assert len(document.parents) == 1
    assert "Tempus" in " ".join(body_text_lines(document.parents[0].instruction))
    assert document.parents[0].item_ids == tuple(item.item_id for item in document.items)
    assert all("Tempus" not in " ".join(item.plain_text_lines()) for item in document.items)
    assert [item.points for item in document.items] == [1, 1, 1]
    assert document.instructions == ()


def test_unnumbered_heading_without_points_is_not_reassigned_by_the_rule() -> None:
    chunks = (
        _chunk(1, "heading", _TITLE),
        _chunk(2, "heading", "Tempus"),
        _chunk(3, "paragraph", _PROMPT),
    )
    manifest = _manifest(chunks)
    assert assign_question_headings(manifest, chunks) == manifest


@pytest.mark.parametrize("role", ["instructions", "title", "item"])
def test_header_only_producer_content_never_becomes_exam_text(role: str) -> None:
    chunks = (
        _chunk(1, "heading", _TITLE),
        _chunk(2, "paragraph", _HEADER),
        _chunk(3, "paragraph", _PROMPT),
    )
    own = (("body:0003",),)
    state = _state(chunks, questions=own, headers=frozenset({"body:0002"}))
    reply: dict[str, JsonValue] = {"items": [_item(["body:0003"], points=2)]}
    metadata: dict[str, JsonValue] = {"text": _HEADER, "source_anchors": ["body:0002"]}
    if role == "instructions":
        reply["instructions"] = [metadata]
    elif role == "title":
        reply["title"] = metadata
    else:
        reply["items"] = [_item(["body:0002"], _HEADER), _item(["body:0003"], points=2)]
    admit_batch(reply, state)
    document = state.result(questions=own).document

    assert len(document.items) == 1
    assert document.title != _HEADER
    assert document.instructions == ()
    assert document.parents == ()
    assert _HEADER not in " ".join(document.items[0].plain_text_lines())


@pytest.mark.parametrize("layout", ["one-segment", "separate-paragraph", "split-header"])
def test_header_anchor_mixed_into_item_leaves_no_header_text(layout: str) -> None:
    chunks = (
        _chunk(1, "heading", _TITLE),
        _chunk(2, "paragraph", _HEADER),
        _chunk(3, "paragraph", _PROMPT),
    )
    own = (("body:0003",),)
    state = _state(chunks, questions=own, headers=frozenset({"body:0002"}))
    produced = _item(["body:0002", "body:0003"], f"{_HEADER}\n{_PROMPT}", 2)
    if layout != "one-segment":
        produced["body"] = [
            {"segments": [{"kind": "text", "text": text, "accepted_values": []}]}
            for text in (_HEADER, _PROMPT)
        ]
    if layout == "split-header":
        produced["body"] = [
            {
                "segments": [
                    {"kind": "text", "text": text, "accepted_values": []}
                    for text in ("Total: ", "36 poäng")
                ]
            },
            {"segments": [{"kind": "text", "text": _PROMPT, "accepted_values": []}]},
        ]
    admit_batch({"items": [produced]}, state)
    document = state.result(questions=own).document

    assert len(document.items) == 1
    item = document.items[0]
    assert item.source_anchor == "body:0003"
    assert _HEADER not in " ".join(item.plain_text_lines())
    assert _PROMPT in " ".join(item.plain_text_lines())
    assert item.points == 2


def test_unclaimed_header_heading_never_becomes_fallback_title_or_parent_instruction() -> None:
    chunks = (
        _chunk(1, "heading", _HEADER),
        _chunk(2, "paragraph", _PROMPT),
        _chunk(3, "paragraph", "Förklara perfekt."),
    )
    own = (("body:0002",), ("body:0003",))
    state = _state(
        chunks,
        questions=own,
        headers=frozenset({"body:0001"}),
        governing=frozenset({"body:0001"}),
    )
    state.review_questions(
        own,
        keys=frozenset(),
        contexts=frozenset({"body:0001"}),
        title=frozenset({"body:0001"}),
        reason="Producenten svarade inte.",
    )
    document = state.result(
        governed={"body:0001": frozenset({"body:0002", "body:0003"})}, questions=own
    ).document

    assert len(document.items) == 2
    assert document.title != _HEADER
    assert document.instructions == ()
    assert document.parents == ()
    assert all(_HEADER not in " ".join(item.plain_text_lines()) for item in document.items)


def test_printed_heading_points_replace_build_points_without_conflict_review() -> None:
    chunks = (_chunk(2, "heading", _HEADING), _chunk(3, "paragraph", _PROMPT))
    own = (("body:0002", "body:0003"),)
    state = _state(chunks, questions=own)
    admit_batch({"items": [_item(["body:0002", "body:0003"], "Tempus\n" + _PROMPT, 5)]}, state)
    item = state.result(questions=own).document.items[0]

    assert item.points == 3
    assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert item.review.reasons == ()


def test_producer_emitting_the_question_heading_as_a_separate_item_creates_no_extra_item() -> None:
    chunks = (_chunk(2, "heading", _HEADING), _chunk(3, "paragraph", _PROMPT))
    own = (("body:0002", "body:0003"),)
    state = _state(chunks, questions=own)
    admit_batch({"items": [_item(["body:0002"], _HEADING), _item(["body:0003"])]}, state)
    document = state.result(questions=own).document

    assert len(document.items) == 1
    item = document.items[0]
    assert item.printed_label == "2"
    assert item.points == 3
    assert "Tempus" in " ".join(item.plain_text_lines())
    assert _PROMPT in " ".join(item.plain_text_lines())
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED


def test_heading_label_split_from_its_words_keeps_one_converted_question() -> None:
    chunks = (_chunk(2, "heading", _HEADING), _chunk(3, "paragraph", _PROMPT))
    own = (("body:0002", "body:0003"),)
    state = _state(chunks, questions=own)
    produced = _item(["body:0002", "body:0003"])
    produced["body"] = [
        {
            "segments": [
                {"kind": "text", "text": text, "accepted_values": []}
                for text in ("2.", " Tempus (3 p)")
            ]
        },
        {"segments": [{"kind": "text", "text": _PROMPT, "accepted_values": []}]},
    ]
    admit_batch({"items": [produced]}, state)
    document = state.result(questions=own).document

    assert len(document.items) == 1
    item = document.items[0]
    assert item.printed_label == "2"
    assert item.points == 3
    assert "Tempus" in " ".join(item.plain_text_lines())
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED


def test_first_source_heading_opens_question_instead_of_becoming_a_document_title() -> None:
    chunks = (_chunk(1, "heading", _HEADING), _chunk(2, "paragraph", _PROMPT))
    raw: dict[str, JsonValue] = {
        "title_anchors": [],
        "header_anchors": [],
        "questions": [
            {
                "id": "q1",
                "anchors": ["body:0002"],
                "subpart_anchors": [],
                "answer_key_anchors": [],
            }
        ],
        "shared_contexts": [
            {
                "anchor": "body:0001",
                "scope": "section_instruction",
                "owner": "exam",
                "governs": ["q1"],
            }
        ],
    }
    manifest = assign_question_headings(manifest_from_output(raw, chunks), chunks)
    own = tuple(q.anchors for q in manifest.questions)
    state = _state(chunks, questions=own)
    admit_batch({"items": [_item(["body:0002"])]}, state)
    document = state.result(questions=own).document

    assert len(document.items) == 1
    assert document.items[0].printed_label == "2"
    assert document.items[0].points == 3
    assert "Tempus" in " ".join(document.items[0].plain_text_lines())
    assert "Tempus" not in document.title
    assert document.instructions == ()
