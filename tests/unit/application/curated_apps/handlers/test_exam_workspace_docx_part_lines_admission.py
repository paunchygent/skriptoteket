"""A part line is never held by an item (TASK-SKRIPT-39-04-12 review-3 N1, N2, L1).

A multi-question part's line leaves every entry that lists it, also the entry of a question
inside its part, and reaches its part's parent through placement. An entry that holds no
question anchor is no item. Every part line that leaves an entry is recorded once.
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
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    ManifestQuestion,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import (
    assign_points_lines,
    manifest_questions,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeTextSegment
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeParseOrigin,
)

pytestmark = pytest.mark.unit


def _normalised_state(
    chunks: tuple[tuple[str, str], ...], grouped: tuple[tuple[int, ...], ...]
) -> DocxBuildState:
    """The batch state built as the pipeline builds it: from the normalised manifest."""
    docx = tuple(
        DocxChunk(f"body:{index + 1:04d}", kind, text, text)
        for index, (kind, text) in enumerate(chunks)
    )
    manifest = ExamManifest(
        questions=tuple(
            ManifestQuestion(f"q{number + 1}", tuple(docx[i].anchor for i in own), (), ())
            for number, own in enumerate(grouped)
        ),
        contexts=(),
        title_anchors=(),
        header=(),
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=(),
    )
    return DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=docx,
        questions=manifest_questions(assign_points_lines(manifest, docx)),
    )


def _entry(anchors: list[str], text: str, label: str) -> dict[str, JsonValue]:
    return {
        "source_anchors": list(anchors),
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "free_text",
        "key_source": None,
        "facit_text": None,
        "printed_label": label,
        "body": [{"segments": [{"kind": "text", "text": text, "accepted_values": []}]}],
        "points": 2,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }


def _texts(item: NativeExamItem) -> list[str]:
    return [
        segment.text
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]


def _by_anchor(document: NativeExamDocument) -> dict[str | None, NativeExamItem]:
    return {item.source_anchor: item for item in document.items}


def _moved(state: DocxBuildState) -> list[tuple[str, ...]]:
    return [e.anchors for e in state.events if e.code == "part_heading_moved"]


_TWO_PARTS = (
    ("heading", "DEL 1: Ordklasser (6 p)"),
    ("paragraph", "1. Förklara vad ett substantiv är."),
    ("paragraph", "2. Förklara vad ett adjektiv är."),
    ("heading", "DEL 2: Satsdelar (4 p)"),
    ("paragraph", "3. Förklara vad ett subjekt är."),
    ("paragraph", "4. Förklara vad ett objekt är."),
)


@pytest.mark.parametrize("holder", [0, 1], ids=["in_q1_entry", "in_q2_entry"])
@pytest.mark.parametrize("reverse", [False, True], ids=["source_order", "reversed"])
def test_a_multi_question_part_line_an_entry_of_its_part_lists_reaches_its_parent(
    holder: int, reverse: bool
):
    # Review-3 N1 reproduction 1: the grouping puts DEL 1 in q1 and the reply copies it into
    # the entry of a question inside DEL 1. The line opens DEL 1's parent, no item holds it,
    # and each question's item takes its share of the part's printed total.
    state = _normalised_state(_TWO_PARTS, ((0, 1), (2,), (4,), (5,)))
    own = ["body:0002", "body:0003", "body:0005", "body:0006"]
    entries: list[JsonValue] = [
        _entry(
            ["body:0001", anchor] if number == holder else [anchor],
            state.chunk_by_anchor[anchor].text,
            str(number + 1),
        )
        for number, anchor in enumerate(own)
    ]

    admit_batch({"items": entries[::-1] if reverse else entries}, state)
    document = state.result().document

    items = _by_anchor(document)
    assert sorted(a or "" for a in items) == own
    assert [items[a].points for a in own] == [3, 3, 2, 2]
    assert not [i for i in document.items if any("DEL 1" in t for t in _texts(i))]
    assert all(i.review.parse_origin is NativeParseOrigin.LLM_PARSED for i in document.items)
    totals = {
        tuple(items_of): parent.printed_total
        for parent in document.parents
        for items_of in [[i.source_anchor for i in document.items if i.item_id in parent.item_ids]]
    }
    assert totals == {("body:0002", "body:0003"): 6, ("body:0005", "body:0006"): 4}
    assert _moved(state) == [("body:0001",)]


def test_a_nested_part_line_listed_with_its_first_question_leaves_the_item():
    # Review-3 N1 reproduction 2: the reply lists "Uppgift 1.1: Subjekt (4 p)" in q1's entry.
    # The points plan makes it an inner part over q1-q3 (1.2 and 1.3 print no total), so no
    # item holds it; q1's item starts at its own chunk and the Del 1 parent carries its total.
    chunks = (
        ("heading", "Del 1: Grammatik (10 p)"),
        ("heading", "Uppgift 1.1: Subjekt (4 p)"),
        ("paragraph", "Stryk under subjektet."),
        ("paragraph", "Uppgift 1.2: Förklara predikat."),
        ("paragraph", "Uppgift 1.3: Förklara objekt."),
    )
    state = _normalised_state(chunks, ((1, 2), (3,), (4,)))
    entries: list[JsonValue] = [
        _entry(["body:0002", "body:0003"], "Stryk under subjektet.", "1.1"),
        _entry(["body:0004"], "Förklara predikat.", "1.2"),
        _entry(["body:0005"], "Förklara objekt.", "1.3"),
    ]

    admit_batch({"items": entries}, state)
    document = state.result().document

    items = _by_anchor(document)
    assert sorted(a or "" for a in items) == ["body:0003", "body:0004", "body:0005"]
    assert not [i for i in document.items if any("Uppgift 1.1" in t for t in _texts(i))]
    assert all(i.review.parse_origin is NativeParseOrigin.LLM_PARSED for i in document.items)
    assert [parent.printed_total for parent in document.parents] == [10]
    assert set(document.parents[0].item_ids) == {i.item_id for i in document.items}
    assert _moved(state) == [("body:0002",)]


def test_an_entry_holding_only_a_part_line_is_no_item():
    # Review-3 N2: the reply lists q2's part heading as an entry of its own. The heading opens
    # q2's one-child parent through placement (ruling 2026-10-18); the entry is no third item.
    chunks = (
        ("paragraph", "Förklara vad som kännetecknar ett substantiv. (4 p)"),
        ("heading", "Del 2: Verb (2 p)"),
        ("paragraph", "Förklara vad som kännetecknar ett verb."),
    )
    state = _normalised_state(chunks, ((0,), (2,)))
    entries: list[JsonValue] = [
        _entry(["body:0001"], "Förklara vad som kännetecknar ett substantiv.", "1"),
        _entry(["body:0002"], "Del 2: Verb", "2"),
        _entry(["body:0003"], "Förklara vad som kännetecknar ett verb.", "2"),
    ]

    admit_batch({"items": entries}, state)
    document = state.result().document

    assert len(document.items) == 2
    noun, verb = sorted(document.items, key=lambda item: item.sequence)
    assert noun.source_anchor == "body:0001"
    assert (noun.points, verb.points) == (4, 2)
    assert not [t for t in _texts(verb) if "Del 2" in t]
    assert [(p.item_ids, p.printed_total) for p in document.parents] == [((verb.item_id,), 2)]
    assert all(i.review.parse_origin is NativeParseOrigin.LLM_PARSED for i in document.items)
    assert _moved(state) == [("body:0002",)]


def test_a_one_question_part_line_another_entry_of_its_part_holds_is_recorded_once():
    # Review-3 L1: q2's part heading is listed in q1's entry and in q2's own entry. It opens
    # q2's one-child parent (ruling 2026-10-18), so it leaves both entries, recorded once.
    chunks = (
        ("paragraph", "Förklara vad som kännetecknar ett substantiv. (4 p)"),
        ("heading", "Del 2: Verb (2 p)"),
        ("paragraph", "Förklara vad som kännetecknar ett verb."),
    )
    state = _normalised_state(chunks, ((0,), (2,)))
    entries: list[JsonValue] = [
        _entry(["body:0001", "body:0002"], "Förklara vad som kännetecknar ett substantiv.", "1"),
        _entry(["body:0002", "body:0003"], "Förklara vad som kännetecknar ett verb.", "2"),
    ]

    admit_batch({"items": entries}, state)
    document = state.result().document

    noun, verb = sorted(document.items, key=lambda item: item.sequence)
    assert not [t for t in _texts(noun) if "Del 2" in t]
    assert verb.source_anchor == "body:0003"
    assert not [t for t in _texts(verb) if "Del 2" in t]
    assert [(p.item_ids, p.printed_total) for p in document.parents] == [((verb.item_id,), 2)]
    assert _moved(state) == [("body:0002",)]
