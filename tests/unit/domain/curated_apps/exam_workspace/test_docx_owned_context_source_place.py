"""A joined context stands at its source place by structure (review-3 N6).

A context the grouping gives a question, printed after the question's first own chunk and
held by no reply entry, follows the item content that chunk produced; one printed before it
opens the item. The place follows the source order of the question's chunks, never the
wording of the reply.
"""

from collections.abc import Callable
from uuid import UUID

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_assembly import (
    exam_metadata_anchors,
    exam_wide_anchors,
    governed_anchors,
    merge_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeParseOrigin,
)

pytestmark = pytest.mark.unit

_Q1 = "1. Förklara vad ett substantiv är. (5 p)"
_STEM = "2. Läs texten och svara på frågorna. (6 p)"
_PASSAGE = "Igår kom en ny elev till klassen. Han var blyg."
_SUB = "a) Vem är huvudpersonen?"
_CHUNKS = (
    DocxChunk("body:0001", "paragraph", _Q1, _Q1),
    DocxChunk("body:0002", "paragraph", _STEM, _STEM),
    DocxChunk("body:0003", "paragraph", _PASSAGE, _PASSAGE),
    DocxChunk("body:0004", "paragraph", _SUB, _SUB),
)
_TEXTS = {chunk.anchor: chunk.text for chunk in _CHUNKS}
_QUESTIONS = {"q1": ("body:0001",), "q2": ("body:0002", "body:0004")}
_FREE_TEXT = frozenset({NativeExamItemKind.FREE_TEXT})


def _run() -> DocxConversionRun:
    job = DocxConversionJob(
        origin_kind="docx_import",
        job_id=UUID(int=1),
        worker_id="worker",
        document_id=UUID(int=2),
        filename="prov.docx",
        source_sha256="0" * 64,
        source_docx=b"",
        chunks=_CHUNKS,
        course_key=None,
    )
    run = DocxConversionRun(job, 0.0)
    run.contexts = (SharedContext("body:0003", "shared_passage", "q2", ("q2",)),)
    manifest = ExamManifest(
        questions=tuple(ManifestQuestion(q, a, (), ()) for q, a in _QUESTIONS.items()),
        contexts=run.contexts,
        title_anchors=(),
        header=(),
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=(),
    )
    run.context_anchors = frozenset({"body:0003"})
    run.families = question_families(manifest, _CHUNKS)
    run.kinds = dict.fromkeys(_QUESTIONS, NativeExamItemKind.FREE_TEXT)
    return run


def _item(anchors: tuple[str, ...], points: int) -> dict[str, JsonValue]:
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
            {"segments": [{"kind": "text", "text": _TEXTS[a], "accepted_values": []}]}
            for a in anchors
        ],
        "points": points,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }


def _batch_result(run: DocxConversionRun, state: DocxBuildState) -> DocxBuildResult:
    return state.result(
        governed=governed_anchors(run.contexts, run.families),
        questions=tuple(f.question_anchors for f in run.families),
        exam_wide=exam_wide_anchors(run.contexts, run.families),
        exam_metadata=exam_metadata_anchors(run.contexts),
    )


def _run_result(run: DocxConversionRun, state: DocxBuildState) -> DocxBuildResult:
    merge_batch(run.state, state, frozenset())
    return _batch_result(run, run.state)


_PATHS: dict[str, Callable[[DocxConversionRun, DocxBuildState], DocxBuildResult]] = {
    "batch_state": _batch_result,
    "run_state": _run_result,
}


def _q2(path: str) -> NativeExamItem:
    run = _run()
    claims = frozenset().union(*(f.claims for f in run.families))
    batch = ConversionBatch("w1-01", _FREE_TEXT, tuple(_QUESTIONS), claims, frozenset())
    state = batch_state(run, batch)
    items: list[JsonValue] = [_item(("body:0001",), 5), _item(("body:0002", "body:0004"), 6)]
    admit_batch(
        {"items": items, "answer_key_anchors": [], "title": None, "instructions": []}, state
    )
    result = _PATHS[path](run, state)
    (item,) = [i for i in result.document.items if _SUB in i.plain_text_lines()]
    return item


@pytest.mark.parametrize("path", sorted(_PATHS))
def test_context_printed_after_the_first_own_chunk_follows_that_chunk_content(path):
    item = _q2(path)

    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.plain_text_lines() == (
        "2. Läs texten och svara på frågorna.",
        "Igår kom en ny elev till klassen. Han var blyg.",
        "a) Vem är huvudpersonen?",
    )
    assert item.source_anchor == "body:0002"
    # D12: the first-paragraph label leaves only because it equals the settled points.
    assert item.points == 6


# A reply paragraph no source chunk aligns to: no word of it appears in the source, and two
# or more source paragraphs remain for it, so the source formatting finds no unique one.
_UNALIGNED = "Motivera."


def _q2_with_body(path: str, body: tuple[str, ...]) -> NativeExamItem:
    run = _run()
    claims = frozenset().union(*(f.claims for f in run.families))
    batch = ConversionBatch("w1-01", _FREE_TEXT, tuple(_QUESTIONS), claims, frozenset())
    state = batch_state(run, batch)
    paragraphs: list[JsonValue] = [
        {"segments": [{"kind": "text", "text": text, "accepted_values": []}]} for text in body
    ]
    q2 = _item(("body:0002", "body:0004"), 6)
    q2["body"] = paragraphs
    items: list[JsonValue] = [_item(("body:0001",), 5), q2]
    admit_batch(
        {"items": items, "answer_key_anchors": [], "title": None, "instructions": []}, state
    )
    result = _PATHS[path](run, state)
    (item,) = [i for i in result.document.items if _SUB in i.plain_text_lines()]
    return item


@pytest.mark.parametrize("path", sorted(_PATHS))
@pytest.mark.parametrize(
    ("body", "expected"),
    [
        # An unaligned paragraph keeps the place of the aligned paragraph before it.
        (
            (
                "2. Läs texten och svara på frågorna. (6 p)",
                "a) Vem är huvudpersonen?",
                "Motivera.",
            ),
            (
                "2. Läs texten och svara på frågorna.",
                "Igår kom en ny elev till klassen. Han var blyg.",
                "a) Vem är huvudpersonen?",
                "Motivera.",
            ),
        ),
        # With no aligned paragraph before it, it keeps the place of the first one after it.
        # The mid-body label is not a first paragraph, so it stays.
        (
            (
                "Motivera.",
                "2. Läs texten och svara på frågorna. (6 p)",
                "a) Vem är huvudpersonen?",
            ),
            (
                "Motivera.",
                "2. Läs texten och svara på frågorna. (6 p)",
                "Igår kom en ny elev till klassen. Han var blyg.",
                "a) Vem är huvudpersonen?",
            ),
        ),
    ],
    ids=["trailing", "leading"],
)
def test_unaligned_reply_paragraph_keeps_the_place_of_its_aligned_neighbour(path, body, expected):
    item = _q2_with_body(path, body)

    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.plain_text_lines() == expected
    # D12: the first-paragraph label leaves only because it equals the settled points.
    assert item.points == 6
