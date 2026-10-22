"""A question heading's place in its item body and the reply text around it (CH4FRAG, review 4).

Review 4 (2026-10-18): with the source alignment (heading, None, stem) the unaligned reply
paragraph took the heading copy's place, and the joined heading landed after it, giving
["Svara kort.", heading, stem]. A joined chunk stands before every unaligned paragraph that
inherited its source place, so the body keeps [heading, "Svara kort.", stem].

The teacher's stem keeps a points phrase its heading also prints: the join's shown heading is
the one owner of removing a heading's points label, never a text strip of the reply.

The chapter_4 shape (one-question part opener "Part 3, Question 3 (1 point)", reply body
["Part 3,", stem]) is in ``test_exam_workspace_docx_part_heading_fragment.py``.
"""

from uuid import UUID

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_assembly import (
    merge_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline_batches import (
    batch_state,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_publication import (
    final_publication,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionJob,
    DocxConversionRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import (
    ConversionBatch,
    question_families,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    ManifestQuestion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeParseOrigin,
)
from tests.unit.llm_door_fakes import fixture_caller

pytestmark = pytest.mark.unit

_Q1 = "1. Förklara vad ett substantiv är. (5 p)"
_HEADING = "Fråga 2: Identifiera huvudord (4 p)"
_WORDING = "Identifiera huvudord"
_STEM = "Stryk under huvudordet i nominalfrasen."
_SUB = "Skriv sedan ordklassen."
# No word of it is in the source and two plain source paragraphs remain for it, so the
# source formatting aligns it to no chunk.
_UNALIGNED = "Svara kort."
_FREE_TEXT = frozenset({NativeExamItemKind.FREE_TEXT})


def _chunks(heading: str, stem: str) -> tuple[DocxChunk, ...]:
    return (
        DocxChunk("body:0001", "paragraph", _Q1, _Q1),
        DocxChunk("body:0002", "heading", heading, heading),
        DocxChunk("body:0003", "paragraph", stem, stem),
        DocxChunk("body:0004", "paragraph", _SUB, _SUB),
    )


_QUESTIONS = {"q1": ("body:0001",), "q2": ("body:0002", "body:0003", "body:0004")}


def _run(chunks: tuple[DocxChunk, ...]) -> DocxConversionRun:
    job = DocxConversionJob(
        origin_kind="docx_import",
        job_id=UUID(int=1),
        worker_id="worker",
        document_id=UUID(int=2),
        filename="prov.docx",
        source_sha256="0" * 64,
        source_docx=b"",
        chunks=chunks,
        course_key=None,
        caller=fixture_caller(),
    )
    run = DocxConversionRun(job, 0.0)
    run.contexts = ()
    manifest = ExamManifest(
        questions=tuple(ManifestQuestion(q, a, (), ()) for q, a in _QUESTIONS.items()),
        contexts=(),
        title_anchors=(),
        header=(),
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=(),
    )
    run.context_anchors = frozenset()
    run.families = question_families(manifest, chunks)
    run.kinds = dict.fromkeys(_QUESTIONS, NativeExamItemKind.FREE_TEXT)
    run.label_kinds = dict(run.kinds)
    run.own_anchors = dict(_QUESTIONS)
    return run


def _entry(anchors: tuple[str, ...], body: tuple[str, ...], points: int) -> dict[str, JsonValue]:
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
            {"segments": [{"kind": "text", "text": text, "accepted_values": []}]} for text in body
        ],
        "points": points,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }


def _q2(chunks: tuple[DocxChunk, ...], body: tuple[str, ...]) -> NativeExamItem:
    run = _run(chunks)
    claims = frozenset().union(*(f.claims for f in run.families))
    batch = ConversionBatch("w1-01", _FREE_TEXT, tuple(_QUESTIONS), claims, frozenset())
    state = batch_state(run, batch)
    entries: list[JsonValue] = [
        _entry(("body:0001",), (_Q1,), 5),
        _entry(_QUESTIONS["q2"], body, 4),
    ]
    admit_batch(
        {"items": entries, "answer_key_anchors": [], "title": None, "instructions": []}, state
    )
    merge_batch(run.state, state, frozenset())
    document = final_publication(run, None).result.document
    (item,) = [i for i in document.items if _SUB in i.plain_text_lines()]
    return item


@pytest.mark.parametrize(
    "body",
    [
        # Review 4: the unaligned paragraph follows the reply's heading copy.
        ("Identifiera huvudord (4 p)", _UNALIGNED, _STEM, _SUB),
        # It stands before the heading copy: the heading still opens the item.
        (_UNALIGNED, "Identifiera huvudord (4 p)", _STEM, _SUB),
    ],
    ids=["after_heading_copy", "before_heading_copy"],
)
def test_joined_heading_stands_before_the_unaligned_paragraph_at_its_place(body):
    item = _q2(_chunks(_HEADING, _STEM), body)

    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.plain_text_lines() == (_WORDING, _UNALIGNED, _STEM, _SUB)


def test_stem_keeps_a_points_phrase_its_heading_prints():
    heading = "Fråga 2: 1 point"
    stem = "Each correct word gives 1 point. Underline the head word."
    item = _q2(_chunks(heading, stem), (stem, _SUB))

    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.plain_text_lines() == (stem, _SUB)
