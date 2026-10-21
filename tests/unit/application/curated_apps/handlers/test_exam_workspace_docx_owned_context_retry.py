"""A question's owned context keeps its source place, its item's identity and its retry.

Ruling 2026-10-18 c: a context owned by one question that no reply entry holds joins that
question's item; it is never an item of its own. A context printed before the question
opens the item. A context printed after the question's heading follows the heading's
content, and the item keeps the question's first own anchor as its source anchor, so the
printed points still find their question. One-question retry treats the owned context as
the question's own: a retry reply that leaves it out joins it the same way, and a reply
that holds it keeps it once.
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
    SharedContext,
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

pytestmark = pytest.mark.unit

_HEADING = "Uppgift 1.1: Morfemanalys (4 p)"
_WORDING = "Morfemanalys"
_TASK = "Dela upp följande ord i morfem."
_Q1 = "1. otrolig"
_TEXT_A = "Text A"
_PASSAGE = "Igår kom en ny elev till klassen. Han var blyg."
_Q2 = "2. Jämför texterna och ge exempel. (10 p)"
# D6+D3: the trailing label equals q2's settled points (10), so the final body
# shows the question without it; lookups and expectations use this literal.
_Q2_SHOWN = "2. Jämför texterna och ge exempel."
_CHUNKS = (
    DocxChunk("body:0001", "heading", _HEADING, _HEADING),
    DocxChunk("body:0002", "paragraph", _TASK, _TASK),
    DocxChunk("body:0003", "paragraph", _Q1, _Q1),
    DocxChunk("body:0004", "paragraph", _TEXT_A, _TEXT_A),
    DocxChunk("body:0005", "paragraph", _PASSAGE, _PASSAGE),
    DocxChunk("body:0006", "paragraph", _Q2, _Q2),
)
_TEXTS = {chunk.anchor: chunk.text for chunk in _CHUNKS} | {"body:0001": _WORDING}
_QUESTIONS = {"q1": ("body:0001", "body:0003"), "q2": ("body:0006",)}
_CONTEXTS = (
    SharedContext("body:0002", "section_instruction", "q1", ("q1",)),
    SharedContext("body:0004", "shared_passage", "q2", ("q2",)),
    SharedContext("body:0005", "shared_passage", "q2", ("q2",)),
)
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
    run.contexts = _CONTEXTS
    manifest = ExamManifest(
        questions=tuple(ManifestQuestion(q, a, (), ()) for q, a in _QUESTIONS.items()),
        contexts=run.contexts,
        title_anchors=(),
        header=(),
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=(),
    )
    run.context_anchors = frozenset(c.anchor for c in _CONTEXTS)
    run.families = question_families(manifest, _CHUNKS)
    run.kinds = dict.fromkeys(_QUESTIONS, NativeExamItemKind.FREE_TEXT)
    run.label_kinds = dict(run.kinds)
    run.own_anchors = dict(_QUESTIONS)
    return run


def _entry(anchors: tuple[str, ...], points: int) -> dict[str, JsonValue]:
    """A reply entry whose body is the listed chunks' wording; the heading's label is the
    printed label, as the producer writes it."""
    return {
        "source_anchors": list(anchors),
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "free_text",
        "key_source": None,
        "facit_text": None,
        "printed_label": "Uppgift 1.1" if "body:0001" in anchors else None,
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


def _reply(*entries: dict[str, JsonValue]) -> dict[str, JsonValue]:
    return {"items": list(entries), "answer_key_anchors": [], "title": None, "instructions": []}


def _published() -> NativeExamDocument:
    """The build of both questions, each reply entry leaving its owned contexts out."""
    run = _run()
    claims = frozenset().union(*(f.claims for f in run.families))
    batch = ConversionBatch("w1-01", _FREE_TEXT, tuple(_QUESTIONS), claims, frozenset())
    state = batch_state(run, batch)
    admit_batch(_reply(_entry(("body:0001", "body:0003"), 4), _entry(("body:0006",), 10)), state)
    merge_batch(run.state, state, frozenset())
    return final_publication(run, None).result.document


def _item(document: NativeExamDocument, text: str) -> NativeExamItem:
    (item,) = [i for i in document.items if text in i.plain_text_lines()]
    return item


def test_context_after_the_heading_follows_the_heading_and_keeps_the_item_identity():
    document = _published()
    q1 = _item(document, _Q1)

    assert len(document.items) == 2
    assert q1.plain_text_lines() == (_WORDING, _TASK, _Q1)
    assert q1.source_anchor == "body:0001"
    assert q1.review.parse_origin is NativeParseOrigin.LLM_PARSED


def test_context_before_the_question_opens_the_item_and_keeps_the_item_identity():
    q2 = _item(_published(), _Q2_SHOWN)

    assert q2.plain_text_lines() == (_TEXT_A, _PASSAGE, _Q2_SHOWN)
    assert q2.source_anchor == "body:0006"


def test_the_retry_record_names_the_contexts_the_question_owns():
    q2 = _item(_published(), _Q2_SHOWN)

    assert q2.retry_source is not None
    assert q2.retry_source.owned_context_anchors == ("body:0004", "body:0005")
    assert [c.anchor for c in q2.retry_source.chunks] == ["body:0004", "body:0005", "body:0006"]


@pytest.fixture()
def env() -> Env:
    return Env()


async def _retry(env: Env, text: str, reply: dict[str, JsonValue]) -> NativeExamItem:
    document = _published().model_copy(update={"document_id": UUID(int=9), "revision": 1})
    await env.seed(document)
    env.exchange.reply = reply
    response = await env.retry(document, item_id=_item(document, text).item_id)
    return response.item


@pytest.mark.asyncio
async def test_retry_reply_leaving_the_passage_out_keeps_it_once_ahead(env: Env):
    item = await _retry(env, _Q2_SHOWN, _reply(_entry(("body:0006",), 10)))

    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.plain_text_lines() == (_TEXT_A, _PASSAGE, _Q2_SHOWN)
    assert item.source_anchor == "body:0006"


@pytest.mark.asyncio
async def test_retry_reply_holding_the_passage_keeps_it_once(env: Env):
    held = _entry(("body:0004", "body:0005", "body:0006"), 10)
    item = await _retry(env, _Q2_SHOWN, _reply(held))

    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.plain_text_lines() == (_TEXT_A, _PASSAGE, _Q2_SHOWN)


@pytest.mark.asyncio
async def test_retry_reply_leaving_the_heading_context_out_keeps_it_after_the_heading(env: Env):
    item = await _retry(env, _Q1, _reply(_entry(("body:0001", "body:0003"), 4)))

    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.plain_text_lines() == (_WORDING, _TASK, _Q1)
    assert item.source_anchor == "body:0001"


@pytest.mark.asyncio
async def test_retry_without_a_converted_item_reviews_the_passage_with_its_question(env: Env):
    item = await _retry(env, _Q2_SHOWN, _reply())

    assert item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    assert item.plain_text_lines() == (_TEXT_A, _PASSAGE, _Q2_SHOWN)
    assert item.source_anchor == "body:0006"


def _listed(
    entries: tuple[dict[str, JsonValue], ...],
    *,
    instructions: tuple[str, ...] = (),
    keys: tuple[str, ...] = (),
) -> dict[str, JsonValue]:
    """A retry reply that lists ``instructions`` as one instruction and ``keys`` as keys."""
    reply = _reply(*entries)
    if instructions:
        text = "\n".join(_TEXTS[a] for a in instructions)
        reply["instructions"] = [{"text": text, "source_anchors": list(instructions)}]
    reply["answer_key_anchors"] = list(keys)
    return reply


@pytest.mark.asyncio
async def test_retry_reply_listing_the_passage_as_an_instruction_joins_it_ahead(env: Env):
    reply = _listed((_entry(("body:0006",), 10),), instructions=("body:0004", "body:0005"))
    item = await _retry(env, _Q2_SHOWN, reply)

    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.plain_text_lines() == (_TEXT_A, _PASSAGE, _Q2_SHOWN)
    assert item.source_anchor == "body:0006"


@pytest.mark.asyncio
async def test_retry_reply_listing_the_passage_as_an_answer_key_joins_it_ahead(env: Env):
    reply = _listed((_entry(("body:0006",), 10),), keys=("body:0004", "body:0005"))
    item = await _retry(env, _Q2_SHOWN, reply)

    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.plain_text_lines() == (_TEXT_A, _PASSAGE, _Q2_SHOWN)
    assert item.source_anchor == "body:0006"


@pytest.mark.asyncio
async def test_retry_reply_listing_one_passage_line_as_an_instruction_keeps_both(env: Env):
    held = _entry(("body:0004", "body:0006"), 10)
    item = await _retry(env, _Q2_SHOWN, _listed((held,), instructions=("body:0005",)))

    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.plain_text_lines() == (_TEXT_A, _PASSAGE, _Q2_SHOWN)


@pytest.mark.asyncio
async def test_retry_reply_listing_the_heading_context_as_an_instruction_joins_it_after(
    env: Env,
):
    reply = _listed((_entry(("body:0001", "body:0003"), 4),), instructions=("body:0002",))
    item = await _retry(env, _Q1, reply)

    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.plain_text_lines() == (_WORDING, _TASK, _Q1)
    assert item.source_anchor == "body:0001"


@pytest.mark.asyncio
async def test_retry_review_reply_listing_the_passage_elsewhere_reviews_it_as_printed(env: Env):
    review = _entry(("body:0006",), 10) | {"outcome": "review", "review_reason": "oklart"}
    item = await _retry(env, _Q2_SHOWN, _listed((review,), instructions=("body:0004", "body:0005")))

    assert item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    assert item.plain_text_lines() == (_TEXT_A, _PASSAGE, _Q2_SHOWN)
    assert item.source_anchor == "body:0006"
