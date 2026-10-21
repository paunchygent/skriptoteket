"""A reply paragraph aligned to the question's heading chunk is that chunk (review-3 N5/N6).

Staging walk 2026-10-18 (exempelprov, question 1c): the heading chunk
"Uppgift 1.3: Identifiera huvudord (4 p)" over the stem published as
["Identifiera huvudord", "Identifiera huvudord (4 p)", "Stryk under …"]: the heading in the
form its join gives it, plus the reply's own copy of the heading line with its printed points.
The reply paragraph's source alignment decides that it is the heading chunk, so the heading
shows once, in its joined form, and its points label never stays in the body. The build and
the one-question retry give the same body.
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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeParseOrigin,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import Env
from tests.unit.llm_door_fakes import fixture_caller

pytestmark = pytest.mark.unit

_Q1 = "1. Förklara vad ett substantiv är. (5 p)"
_HEADING = "Uppgift 1.3: Identifiera huvudord (4 p)"
_WORDING = "Identifiera huvudord"
_STEM = "Stryk under huvudordet i nominalfrasen."
_CHUNKS = (
    DocxChunk("body:0001", "paragraph", _Q1, _Q1),
    DocxChunk("body:0002", "heading", _HEADING, _HEADING),
    DocxChunk("body:0003", "paragraph", _STEM, _STEM),
)
_QUESTIONS = {"q1": ("body:0001",), "q2": ("body:0002", "body:0003")}
_FREE_TEXT = frozenset({NativeExamItemKind.FREE_TEXT})

# The reply copies the heading line with its printed points, or leaves it out.
_BODIES = {
    "heading_with_points": ("Identifiera huvudord (4 p)", _STEM),
    "heading_left_out": (_STEM,),
}


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
    run.families = question_families(manifest, _CHUNKS)
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
        "printed_label": "Uppgift 1.3" if "body:0002" in anchors else None,
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


def _reply(*entries: dict[str, JsonValue]) -> dict[str, JsonValue]:
    return {"items": list(entries), "answer_key_anchors": [], "title": None, "instructions": []}


def _published(body: tuple[str, ...]) -> NativeExamDocument:
    run = _run()
    claims = frozenset().union(*(f.claims for f in run.families))
    batch = ConversionBatch("w1-01", _FREE_TEXT, tuple(_QUESTIONS), claims, frozenset())
    state = batch_state(run, batch)
    q2 = _entry(("body:0002", "body:0003"), body, 4)
    admit_batch(_reply(_entry(("body:0001",), (_Q1,), 5), q2), state)
    merge_batch(run.state, state, frozenset())
    return final_publication(run, None).result.document


def _q2(document: NativeExamDocument) -> NativeExamItem:
    (item,) = [i for i in document.items if _STEM in i.plain_text_lines()]
    return item


@pytest.mark.parametrize("case", sorted(_BODIES))
def test_build_shows_the_heading_once_without_its_points(case):
    item = _q2(_published(_BODIES[case]))

    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.plain_text_lines() == (_WORDING, _STEM)
    assert item.points == 4


@pytest.fixture()
def env() -> Env:
    return Env()


@pytest.mark.asyncio
@pytest.mark.parametrize("case", sorted(_BODIES))
async def test_retry_shows_the_heading_once_without_its_points(env: Env, case):
    document = _published(_BODIES["heading_left_out"]).model_copy(
        update={"document_id": UUID(int=9), "revision": 1}
    )
    await env.seed(document)
    env.exchange.reply = _reply(_entry(("body:0002", "body:0003"), _BODIES[case], 4))
    response = await env.retry(document, item_id=_q2(document).item_id)

    assert response.item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert response.item.plain_text_lines() == (_WORDING, _STEM)
    assert response.item.points == 4
