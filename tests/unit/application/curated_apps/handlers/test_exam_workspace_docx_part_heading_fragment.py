"""No fragment of a one-question part heading stays its own body paragraph (CH4FRAG).

Replay of chapter_4_poetry_and_lyrics_quiz_med_facit (lead, 2026-10-18): the heading
"Part 3, Question 3 (1 point)" opens a part that holds one question and is no question anchor.
The recorded reply lists it and gives the body ["Part 3,", stem] with printed_label
"Question 3". The source alignment puts "Part 3," on the heading chunk, but the join only
replaces the question's own headings, so the item published
["Part 3, Question 3", "Part 3,", stem]: the placed heading plus the reply's leftover of it.

Admission's ``headings`` owns the repair: a part line that opens no parent and heads its one
question is one of that question's headings, so the join replaces the aligned reply paragraph.
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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    build_replay,
    corpus_chunks,
)

pytestmark = pytest.mark.unit

_POETRY = "chapter_4_poetry_and_lyrics_quiz_med_facit"
# Two part lines that repeat one part identity, as chapter_4's "Part 3, Question N" lines do:
# each heads its one question and opens no parent.
_HEADINGS = ("Part 3, Question 1 (1 point)", "Part 3, Question 2 (1 point)")
_STEMS = ("Write a synonym for “profound”.", "Write a synonym for “frugal”.")
_CHUNKS = (
    DocxChunk("body:0001", "heading", _HEADINGS[0], _HEADINGS[0]),
    DocxChunk("body:0002", "paragraph", _STEMS[0], _STEMS[0]),
    DocxChunk("body:0003", "heading", _HEADINGS[1], _HEADINGS[1]),
    DocxChunk("body:0004", "paragraph", _STEMS[1], _STEMS[1]),
)
# As the chapter_4 grouping gives them: a part-labelled heading is never a question anchor.
_QUESTIONS: dict[str, tuple[str, ...]] = {"q1": ("body:0002",), "q2": ("body:0004",)}
_FREE_TEXT = frozenset({NativeExamItemKind.FREE_TEXT})


def _run(
    chunks: tuple[DocxChunk, ...] = _CHUNKS, questions: dict[str, tuple[str, ...]] = _QUESTIONS
) -> DocxConversionRun:
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
    )
    run = DocxConversionRun(job, 0.0)
    run.contexts = ()
    manifest = ExamManifest(
        questions=tuple(ManifestQuestion(q, a, (), ()) for q, a in questions.items()),
        contexts=(),
        title_anchors=(),
        header=(),
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=(),
    )
    run.context_anchors = frozenset()
    run.families = question_families(manifest, chunks)
    run.kinds = dict.fromkeys(questions, NativeExamItemKind.FREE_TEXT)
    run.label_kinds = dict(run.kinds)
    run.own_anchors = dict(questions)
    return run


def _entry(
    heading: str, stem_anchor: str, stem: str, part: str, label: str
) -> dict[str, JsonValue]:
    return {
        "source_anchors": [heading, stem_anchor],
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "free_text",
        "key_source": None,
        "facit_text": None,
        "printed_label": label,
        "body": [
            {"segments": [{"kind": "text", "text": text, "accepted_values": []}]}
            for text in (part, stem)
        ],
        "points": 1,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }


def _heading_fragments(heading: str, lines: tuple[str, ...]) -> list[str]:
    """Body lines that are only a leftover piece of the heading, never the heading itself."""
    shown = heading.split(" (")[0]
    return [line for line in lines if line != shown and line and shown.startswith(line)]


def test_reply_leftover_of_a_part_heading_leaves_the_item_body():
    run = _run()
    claims = frozenset().union(*(f.claims for f in run.families))
    batch = ConversionBatch("w1-01", _FREE_TEXT, tuple(_QUESTIONS), claims, frozenset())
    state = batch_state(run, batch)
    entries: list[JsonValue] = [
        _entry("body:0001", "body:0002", _STEMS[0], "Part 3,", "Question 1"),
        _entry("body:0003", "body:0004", _STEMS[1], "Part 3,", "Question 2"),
    ]
    admit_batch(
        {"items": entries, "answer_key_anchors": [], "title": None, "instructions": []}, state
    )
    merge_batch(run.state, state, frozenset())
    document = final_publication(run, None).result.document

    for heading, stem in zip(_HEADINGS, _STEMS, strict=True):
        (item,) = [i for i in document.items if stem in i.plain_text_lines()]
        assert _heading_fragments(heading, item.plain_text_lines()) == []
        assert item.plain_text_lines() == (heading.split(" (")[0], stem)


@pytest.mark.asyncio
async def test_chapter_4_replay_has_no_heading_leftover_paragraph():
    replay = build_replay(_POETRY)
    outcome = await replay.pipeline.convert(job=replay.job())
    chunks = {c.anchor: c for c in corpus_chunks(_POETRY)}

    leftovers = {
        item.item_id: fragments
        for item in outcome.result.document.items
        if item.source_anchor is not None
        if (chunk := chunks.get(item.source_anchor)) is not None and chunk.kind == "heading"
        if (fragments := _heading_fragments(chunk.text, item.plain_text_lines()))
    }
    assert leftovers == {}


def test_part_line_that_opens_a_parent_over_one_question_is_no_heading_of_it():
    """A part line naming its part once opens a parent (DEL 4); the question's heading rule
    does not take it, so the reply's own paragraph stays the only text the entry gives."""
    line = "Del 4: Textanalys (1 p)"
    chunks = (
        DocxChunk("body:0001", "heading", line, line),
        DocxChunk("body:0002", "paragraph", _STEMS[0], _STEMS[0]),
    )
    questions: dict[str, tuple[str, ...]] = {"q1": ("body:0002",)}
    run = _run(chunks, questions)
    claims = frozenset().union(*(f.claims for f in run.families))
    batch = ConversionBatch("w1-01", _FREE_TEXT, tuple(questions), claims, frozenset())
    state = batch_state(run, batch)
    entries: list[JsonValue] = [_entry("body:0001", "body:0002", _STEMS[0], "Del 4:", "Question 1")]
    admit_batch(
        {"items": entries, "answer_key_anchors": [], "title": None, "instructions": []}, state
    )
    merge_batch(run.state, state, frozenset())
    document = final_publication(run, None).result.document

    (item,) = [i for i in document.items if _STEMS[0] in i.plain_text_lines()]
    assert line.split(" (")[0] not in item.plain_text_lines()
