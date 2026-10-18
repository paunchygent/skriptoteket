"""A left-out context a question owns joins its owner's item (ruling 2026-10-18 c).

A passage the grouping gives a question as its owner, printed before the question, that no
reply entry holds goes ahead of that question's item text as its source paragraphs, pictures
and marks included; kind, points and answer key stay the reply's. When the question has no
converted item, its one source-review item shows the passage and the question's source.
The passage is never an item of its own. The rule follows the grouping's owner alone.
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
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    ManifestQuestion,
    SharedContext,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeParseOrigin,
)

pytestmark = pytest.mark.unit

_Q1 = "1. Förklara vad ett substantiv är. (5 p)"
_TEXT_A = "Text A"
_PASSAGE = "Igår kom en ny elev till klassen. Han var blyg."
_Q2 = "2. Jämför texterna och ge exempel. (10 p)"
_PICTURE = DocxImage(b"passage picture", "image/png", offset=len(_PASSAGE), marked_offset=0)
_CHUNKS = (
    DocxChunk("body:0001", "paragraph", _Q1, _Q1),
    DocxChunk("body:0002", "paragraph", _TEXT_A, _TEXT_A),
    DocxChunk(
        "body:0003",
        "paragraph",
        _PASSAGE,
        _PASSAGE,
        images=(_PICTURE,),
        runs=(DocxSourceRun(0, "Igår", ("italic",)), DocxSourceRun(4, _PASSAGE[4:])),
    ),
    DocxChunk("body:0004", "paragraph", _Q2, _Q2),
)
_TEXTS = {chunk.anchor: chunk.text for chunk in _CHUNKS}
_QUESTIONS = {"q1": "body:0001", "q2": "body:0004"}
_OWNED = ("body:0002", "body:0003")
_FREE_TEXT = frozenset({NativeExamItemKind.FREE_TEXT})


def _run() -> DocxConversionRun:
    job = DocxConversionJob(
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
    run.contexts = tuple(SharedContext(a, "shared_passage", "q2", ("q2",)) for a in _OWNED)
    manifest = ExamManifest(
        questions=tuple(ManifestQuestion(q, (a,), (), ()) for q, a in _QUESTIONS.items()),
        contexts=run.contexts,
        title_anchors=(),
        header=(),
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=(),
    )
    run.context_anchors = frozenset(_OWNED)
    run.families = question_families(manifest, _CHUNKS)
    run.kinds = dict.fromkeys(_QUESTIONS, NativeExamItemKind.FREE_TEXT)
    return run


def _item(anchors: tuple[str, ...], points: int, **update: JsonValue) -> dict[str, JsonValue]:
    item: dict[str, JsonValue] = {
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
            if a != "body:0003"
        ],
        "points": points,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }
    item.update(update)
    return item


def _passage_paragraph() -> dict[str, JsonValue]:
    return {
        "segments": [
            {"kind": "text", "text": _PASSAGE, "accepted_values": []},
            {"kind": "asset", "text": None, "accepted_values": [], "asset_id": _PICTURE.asset_id},
        ]
    }


def _batch_result(run: DocxConversionRun, state: DocxBuildState) -> DocxBuildResult:
    return state.result(
        governed=governed_anchors(run.contexts, run.families),
        questions=tuple(f.question_anchors for f in run.families),
        exam_wide=exam_wide_anchors(run.contexts, run.families),
        exam_metadata=exam_metadata_anchors(run.contexts),
    )


def _run_result(run: DocxConversionRun, state: DocxBuildState) -> DocxBuildResult:
    """The final publication's path: the batch merged into the run state, built there."""
    merge_batch(run.state, state, frozenset())
    return _batch_result(run, run.state)


_PATHS: dict[str, Callable[[DocxConversionRun, DocxBuildState], DocxBuildResult]] = {
    "batch_state": _batch_result,
    "run_state": _run_result,
}


def _admitted(items: list[JsonValue], path: str) -> tuple[DocxBuildResult, DocxBuildState]:
    run = _run()
    claims = frozenset().union(*(f.claims for f in run.families))
    batch = ConversionBatch("w1-01", _FREE_TEXT, tuple(_QUESTIONS), claims, frozenset())
    state = batch_state(run, batch)
    admit_batch(
        {"items": items, "answer_key_anchors": [], "title": None, "instructions": []}, state
    )
    return _PATHS[path](run, state), state


def _build(items: list[JsonValue], path: str) -> DocxBuildResult:
    return _admitted(items, path)[0]


def _q2(result: DocxBuildResult) -> NativeExamItem:
    (item,) = [i for i in result.document.items if _Q2 in i.plain_text_lines()]
    return item


def _q1(result: DocxBuildResult) -> NativeExamItem:
    (item,) = [i for i in result.document.items if i.source_anchor == "body:0001"]
    return item


@pytest.mark.parametrize("path", sorted(_PATHS))
def test_left_out_owned_passage_opens_its_question_item(path):
    result = _build([_item(("body:0001",), 5), _item(("body:0004",), 10)], path)
    item = _q2(result)

    assert len(result.document.items) == 2
    assert item.plain_text_lines() == (_TEXT_A, _PASSAGE, _Q2)
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.kind is NativeExamItemKind.FREE_TEXT
    assert item.points == 10
    passage = item.body[1].segments
    assert passage[0] == NativeTextSegment(text="Igår", marks=("italic",))
    assert passage[-1] == NativeAssetSegment(asset_id=_PICTURE.asset_id)
    assert item.source_anchor == "body:0004"


@pytest.mark.parametrize("path", sorted(_PATHS))
@pytest.mark.parametrize(
    "q2_entry",
    [
        None,
        _item(("body:0004",), 10, outcome="review", review_reason="Oklar fråga"),
    ],
    ids=["omitted", "model_review"],
)
def test_question_without_converted_item_reviews_its_passage_with_its_source(path, q2_entry):
    items: list[JsonValue] = [_item(("body:0001",), 5)]
    if q2_entry is not None:
        items.append(q2_entry)
    result = _build(items, path)
    item = _q2(result)

    assert len(result.document.items) == 2
    assert item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    assert item.plain_text_lines() == (_TEXT_A, _PASSAGE, _Q2)
    assert item.source_anchor == "body:0004"


@pytest.mark.parametrize("path", sorted(_PATHS))
def test_passage_the_reply_holds_is_not_joined_again(path):
    held = _item(
        ("body:0002", "body:0003", "body:0004"),
        10,
        body=[
            {"segments": [{"kind": "text", "text": _TEXT_A, "accepted_values": []}]},
            _passage_paragraph(),
            {"segments": [{"kind": "text", "text": _Q2, "accepted_values": []}]},
        ],
    )
    result = _build([_item(("body:0001",), 5), held], path)
    item = _q2(result)

    assert len(result.document.items) == 2
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.plain_text_lines() == (_TEXT_A, _PASSAGE, _Q2)


def _paragraph(text: str) -> dict[str, JsonValue]:
    return {"segments": [{"kind": "text", "text": text, "accepted_values": []}]}


# Review-3 N5: q1's entry lists contexts the grouping gives q2 (parent ruling 2026-10-18).
_FOREIGN: dict[str, tuple[tuple[str, ...], list[JsonValue]]] = {
    "text_a": (("body:0001", "body:0002"), [_paragraph(_Q1), _paragraph(_TEXT_A)]),
    "text_a_and_passage": (
        ("body:0001", "body:0002", "body:0003"),
        [_paragraph(_Q1), _paragraph(_TEXT_A), _passage_paragraph()],
    ),
}


def _foreign(case: str, path: str) -> tuple[DocxBuildResult, DocxBuildState]:
    anchors, body = _FOREIGN[case]
    return _admitted([_item(anchors, 5, body=body), _item(("body:0004",), 10)], path)


@pytest.mark.parametrize("path", sorted(_PATHS))
@pytest.mark.parametrize("case", sorted(_FOREIGN))
def test_context_another_question_lists_opens_its_owner_item(case, path):
    result, state = _foreign(case, path)
    item = _q2(result)

    assert len(result.document.items) == 2
    assert item.plain_text_lines() == (_TEXT_A, _PASSAGE, _Q2)
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.body[1].segments[-1] == NativeAssetSegment(asset_id=_PICTURE.asset_id)
    assert item.source_anchor == "body:0004"
    moved = [e.anchors for e in state.events if e.code == "owned_context_moved"]
    assert moved == [_FOREIGN[case][0][1:]]
    assert all(e.detail == "" for e in state.events if e.code == "owned_context_moved")


@pytest.mark.parametrize("path", sorted(_PATHS))
def test_question_listing_another_question_context_is_its_source_review_item(path):
    """Parent ruling 2026-10-18 (a): the entry is not converted; it shows its own source."""
    result, state = _foreign("text_a", path)
    item = _q1(result)

    assert item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    assert item.plain_text_lines() == (_Q1,)
    assert [e.anchors for e in state.events if e.code == "foreign_context_listed"] == [
        ("body:0001",)
    ]
    q2 = _q2(result)
    assert q2.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert q2.plain_text_lines() == (_TEXT_A, _PASSAGE, _Q2)


@pytest.mark.parametrize("path", sorted(_PATHS))
def test_question_placing_the_moved_context_picture_is_its_source_review_item(path):
    """The picture belongs to the context's source, so it leaves with the context: a q1
    reply that places it no longer matches q1's own source pictures (no wording is read)."""
    item = _q1(_foreign("text_a_and_passage", path)[0])

    assert item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    assert item.plain_text_lines() == (_Q1,)
