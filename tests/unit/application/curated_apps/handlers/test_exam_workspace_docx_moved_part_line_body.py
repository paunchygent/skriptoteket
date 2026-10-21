"""A moved part line leaves the item body too, not only its anchor list (review F1, 2026-10-21).

A part line that opens a parent is the parent's instruction, never the child's opening line
(user ruling 2026-10-18, DEL 4). Admission removes its anchor from every entry; the reply's
rendered copy of the line, whole or a fragment, is the part's source and so no paragraph of the
question that entry converts. The parent publishes the line once, and the question keeps its
own source paragraphs, also one whose wording the part line repeats.
"""

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
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import ConversionBatch
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines
from tests.unit.application.curated_apps.handlers.test_exam_workspace_docx_part_heading_fragment import (  # noqa: E501
    _CHUNKS,
    _FREE_TEXT,
    _HEADINGS,
    _QUESTIONS,
    _STEMS,
    _run,
)

pytestmark = pytest.mark.unit

_NOUN = "Förklara vad som kännetecknar ett substantiv."
_VERB = "Förklara vad som kännetecknar ett verb."
_DEL_2 = "Del 2: Verb (2 p)"


def _entry(anchors: list[str], lines: tuple[str, ...], points: int) -> dict[str, JsonValue]:
    return {
        "source_anchors": list[JsonValue](anchors),
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "free_text",
        "key_source": None,
        "facit_text": None,
        "printed_label": None,
        "body": [
            {"segments": [{"kind": "text", "text": line, "accepted_values": []}]} for line in lines
        ],
        "points": points,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }


def _published(
    chunks: tuple[DocxChunk, ...],
    questions: dict[str, tuple[str, ...]],
    entries: list[JsonValue],
) -> NativeExamDocument:
    """The final publication of one batch reply, through admission and the batch merge."""
    run = _run(chunks, questions)
    claims = frozenset().union(*(family.claims for family in run.families))
    batch = ConversionBatch("w1-01", _FREE_TEXT, tuple(questions), claims, frozenset())
    state = batch_state(run, batch)
    admit_batch(
        {"items": entries, "answer_key_anchors": [], "title": None, "instructions": []}, state
    )
    merge_batch(run.state, state, frozenset())
    document = final_publication(run, None).result.document
    assert all(
        item.review.parse_origin is NativeParseOrigin.LLM_PARSED
        and item.review.state is NativeItemReviewState.REVIEW_COMPLETE
        for item in document.items
    )
    return document


def _noun_and_verb(kind: str, verb_stem: tuple[str, ...] = (_VERB,)) -> tuple[DocxChunk, ...]:
    texts = (("paragraph", _NOUN), (kind, _DEL_2), *(("paragraph", t) for t in verb_stem))
    return tuple(
        DocxChunk(f"body:{index:04d}", chunk_kind, text, text)
        for index, (chunk_kind, text) in enumerate(texts, start=1)
    )


@pytest.mark.parametrize("kind", ["heading", "paragraph"])
@pytest.mark.parametrize("rendered", [_DEL_2, "Del 2: Verb", "Del 2:"])
def test_part_line_rendered_in_a_foreign_entry_leaves_its_body(kind: str, rendered: str):
    # The noun entry lists the DEL 2 line and renders it before its own stem.
    document = _published(
        _noun_and_verb(kind),
        {"q1": ("body:0001",), "q2": ("body:0003",)},
        [
            _entry(["body:0001", "body:0002"], (rendered, _NOUN), 4),
            _entry(["body:0003"], (_VERB,), 2),
        ],
    )

    noun, verb = sorted(document.items, key=lambda item: item.sequence)
    assert noun.plain_text_lines() == (_NOUN,)
    assert verb.plain_text_lines() == (_VERB,)
    assert [(p.item_ids, p.printed_total) for p in document.parents] == [((verb.item_id,), 2)]
    assert [body_text_lines(p.instruction) for p in document.parents] == [("Del 2: Verb",)]
    assert (noun.points, verb.points) == (4, 2)


@pytest.mark.parametrize("kind", ["heading", "paragraph"])
def test_part_line_rendered_in_its_own_child_entry_leaves_its_body(kind: str):
    # The verb entry lists and renders the line that opens its parent.
    document = _published(
        _noun_and_verb(kind),
        {"q1": ("body:0001",), "q2": ("body:0003",)},
        [
            _entry(["body:0001"], (_NOUN,), 4),
            _entry(["body:0002", "body:0003"], (_DEL_2, _VERB), 2),
        ],
    )

    noun, verb = sorted(document.items, key=lambda item: item.sequence)
    assert noun.plain_text_lines() == (_NOUN,)
    assert verb.plain_text_lines() == (_VERB,)
    assert [body_text_lines(p.instruction) for p in document.parents] == [("Del 2: Verb",)]


@pytest.mark.parametrize("separator", [" ", "\n"])
@pytest.mark.parametrize("rendered", [_DEL_2, "Del 2: Verb", "Del 2:"])
@pytest.mark.parametrize("trailing", [False, True])
def test_part_line_merged_into_a_stem_paragraph_leaves_the_body(
    separator: str, rendered: str, trailing: bool
):
    # One reply paragraph holds the DEL 2 line, whole or a fragment, beside the noun stem: no
    # alignment separates them, so the noun's body is its own source paragraph, never the
    # reply's merged text.
    merged = f"{_NOUN}{separator}{rendered}" if trailing else f"{rendered}{separator}{_NOUN}"
    document = _published(
        _noun_and_verb("heading"),
        {"q1": ("body:0001",), "q2": ("body:0003",)},
        [
            _entry(["body:0001", "body:0002"], (merged,), 4),
            _entry(["body:0003"], (_VERB,), 2),
        ],
    )

    noun, verb = sorted(document.items, key=lambda item: item.sequence)
    assert noun.plain_text_lines() == (_NOUN,)
    assert verb.plain_text_lines() == (_VERB,)
    assert [body_text_lines(p.instruction) for p in document.parents] == [("Del 2: Verb",)]


@pytest.mark.parametrize("rendered", ["Del 2: Verb", "Del 2:"])
def test_part_fragment_merged_into_its_own_child_stem_leaves_the_body(rendered: str):
    # The verb entry renders a fragment of the line that opens its parent inside its own stem
    # paragraph: the verb's body is its own source paragraph and the parent keeps the line.
    document = _published(
        _noun_and_verb("heading"),
        {"q1": ("body:0001",), "q2": ("body:0003",)},
        [
            _entry(["body:0001"], (_NOUN,), 4),
            _entry(["body:0002", "body:0003"], (f"{rendered} {_VERB}",), 2),
        ],
    )

    noun, verb = sorted(document.items, key=lambda item: item.sequence)
    assert noun.plain_text_lines() == (_NOUN,)
    assert verb.plain_text_lines() == (_VERB,)
    assert [body_text_lines(p.instruction) for p in document.parents] == [("Del 2: Verb",)]
    assert (noun.points, verb.points) == (4, 2)


def test_own_stem_paragraph_the_part_line_repeats_stays_in_the_item():
    # The teacher's own paragraph "Verb" is wording the part line holds; it is the question's
    # source, so it stays, while the reply's copy of the part line leaves.
    document = _published(
        _noun_and_verb("heading", ("Verb", _VERB)),
        {"q1": ("body:0001",), "q2": ("body:0003", "body:0004")},
        [
            _entry(["body:0001"], (_NOUN,), 4),
            _entry(["body:0002", "body:0003", "body:0004"], (_DEL_2, "Verb", _VERB), 2),
        ],
    )

    _, verb = sorted(document.items, key=lambda item: item.sequence)
    assert verb.plain_text_lines() == ("Verb", _VERB)
    assert [body_text_lines(p.instruction) for p in document.parents] == [("Del 2: Verb",)]


@pytest.mark.parametrize("rendered", ["Part 3,", _HEADINGS[1]])
def test_question_heading_line_listed_by_a_foreign_entry_heads_its_question_once(rendered: str):
    # Chapter_4 shape: the first entry lists the second question's part heading; the second
    # entry renders it, whole or as a fragment. The heading opens its own question once.
    document = _published(
        _CHUNKS,
        _QUESTIONS,
        [
            _entry(["body:0001", "body:0002", "body:0003"], (_HEADINGS[0], _STEMS[0]), 1),
            _entry(["body:0004"], (rendered, _STEMS[1]), 1),
        ],
    )

    first, second = sorted(document.items, key=lambda item: item.sequence)
    assert first.plain_text_lines() == ("Part 3, Question 1", _STEMS[0])
    assert second.plain_text_lines() == ("Part 3, Question 2", _STEMS[1])
    assert document.parents == ()


@pytest.mark.parametrize("rendered", ["Del 4:", "Del 4: Textanalys (1 p)"])
def test_del_4_line_over_one_question_leaves_its_child_body(rendered: str):
    # The DEL 4 shape: a part line naming its part once opens a parent over one question; the
    # reply renders a fragment of it, or all of it, before the stem.
    line = "Del 4: Textanalys (1 p)"
    stem = "Write a synonym for profound."
    document = _published(
        (
            DocxChunk("body:0001", "heading", line, line),
            DocxChunk("body:0002", "paragraph", stem, stem),
        ),
        {"q1": ("body:0002",)},
        [_entry(["body:0001", "body:0002"], (rendered, stem), 1)],
    )

    (item,) = document.items
    assert item.plain_text_lines() == (stem,)
    assert [(p.item_ids, p.printed_total) for p in document.parents] == [((item.item_id,), 1)]
    assert [body_text_lines(p.instruction) for p in document.parents] == [("Del 4: Textanalys",)]
