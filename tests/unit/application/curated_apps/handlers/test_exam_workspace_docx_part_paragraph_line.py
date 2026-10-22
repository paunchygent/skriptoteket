"""A part-labelled paragraph printing its own total opens its part (review-3 N3, D10a).

A paragraph that opens with a part label and prints exactly one points label opens its part
whatever its title length. It is never a question anchor and never an item of its own. As a
plan part opener it is section structure whatever its Word kind (review-3 N3b): listed or
omitted by the reply, it opens its part's parent, whose instruction is its wording without the
points label, as a part heading's is.
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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeParseOrigin,
)

pytestmark = pytest.mark.unit

_QUESTIONS = (
    ("paragraph", "1. Förklara vad ett substantiv är."),
    ("paragraph", "2. Förklara vad ett adjektiv är."),
    ("heading", "DEL 2: Satsdelar (4 p)"),
    ("paragraph", "3. Förklara vad ett subjekt är."),
    ("paragraph", "4. Förklara vad ett objekt är."),
)
_IN_Q1 = ((0, 1), (2,), (4,), (5,))
_IN_NO_QUESTION = ((1,), (2,), (4,), (5,))


def _built(opener: str, grouped: tuple[tuple[int, ...], ...], listed: bool) -> NativeExamDocument:
    chunks = tuple(
        DocxChunk(f"body:{index + 1:04d}", kind, text, text)
        for index, (kind, text) in enumerate((("paragraph", opener), *_QUESTIONS))
    )
    manifest = ExamManifest(
        questions=tuple(
            ManifestQuestion(f"q{number + 1}", tuple(chunks[i].anchor for i in own), (), ())
            for number, own in enumerate(grouped)
        ),
        contexts=(),
        title_anchors=(),
        header=(),
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=(),
    )
    state = DocxBuildState(
        origin_kind="docx_import",
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=manifest_questions(assign_points_lines(manifest, chunks)),
    )
    # The reply lists each question's own line alone, 2 p each, and the opener in no item:
    # as an instruction when ``listed``, else nowhere.
    own_lines = [chunks[1], chunks[2], chunks[4], chunks[5]]
    entries: list[JsonValue] = [
        _entry(chunk.anchor, chunk.text, str(number + 1)) for number, chunk in enumerate(own_lines)
    ]
    instructions: list[JsonValue] = (
        [{"text": opener.split(" (")[0], "source_anchors": ["body:0001"]}] if listed else []
    )
    admit_batch({"items": entries, "instructions": instructions}, state)
    return state.result().document


def _entry(anchor: str, text: str, label: str) -> dict[str, JsonValue]:
    return {
        "source_anchors": [anchor],
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


def _texts(paragraphs: tuple[NativeParagraph, ...]) -> list[str]:
    return [
        segment.text
        for paragraph in paragraphs
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]


_LONG_TITLES = ("DEL 1: Ordklasser (6 p)", "Del 1: Ordklasser och ordbildning (6 p)")
_GROUPINGS = pytest.mark.parametrize(
    "grouped", [_IN_Q1, _IN_NO_QUESTION], ids=["in_q1", "in_no_question"]
)


@pytest.mark.parametrize("listed", [True, False], ids=["listed", "omitted"])
@pytest.mark.parametrize("opener", [*_LONG_TITLES, "DEL 1 (6 p)"])
@_GROUPINGS
def test_a_part_labelled_paragraph_total_is_shared_by_its_questions(
    opener: str, grouped: tuple[tuple[int, ...], ...], listed: bool
) -> None:
    # Review-3 N3 rows 1-3, row 4 the control: the part line is no question anchor, so q1
    # never takes the part total as its own points and q1, q2 share it.
    document = _built(opener, grouped, listed)

    questions = {item.source_anchor: item for item in document.items}
    assert [questions[a].points for a in ("body:0002", "body:0003")] == [3, 3]
    assert [questions[a].points for a in ("body:0005", "body:0006")] == [2, 2]
    assert all(
        questions[a].review.parse_origin is NativeParseOrigin.LLM_PARSED
        for a in ("body:0002", "body:0003", "body:0005", "body:0006")
    )


_ALL_OPENERS = pytest.mark.parametrize("opener", [*_LONG_TITLES, "DEL 1 (6 p)"])


def _part_of_six(document: NativeExamDocument) -> tuple[str, ...]:
    """The 6 p parent over q1 and q2, as its instruction texts; it must exist."""
    items = sorted(document.items, key=lambda item: item.sequence)
    part = next(parent for parent in document.parents if parent.printed_total == 6)
    assert part.item_ids == (items[0].item_id, items[1].item_id)
    return tuple(_texts(part.instruction))


@pytest.mark.parametrize("listed", [True, False], ids=["listed", "omitted"])
@_ALL_OPENERS
@_GROUPINGS
def test_a_part_paragraph_opens_a_parent_over_its_questions(
    opener: str, grouped: tuple[tuple[int, ...], ...], listed: bool
) -> None:
    # N3b requirements 1-3: listed or omitted, whatever its title length, the part paragraph
    # opens the DEL 1 parent; its instruction is the line without its points label, as a part
    # heading's is ("DEL 2: Satsdelar"), and no item holds it.
    document = _built(opener, grouped, listed)

    assert [item.source_anchor for item in sorted(document.items, key=lambda i: i.sequence)] == [
        "body:0002",
        "body:0003",
        "body:0005",
        "body:0006",
    ]
    assert not [
        item
        for item in document.items
        if item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    ]
    assert _part_of_six(document) == (opener.split(" (")[0],)
    assert not _texts(document.instructions)
