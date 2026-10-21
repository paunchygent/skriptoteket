"""Single-question retry settles trailing points wording on the retried item (D2, D7).

Each case drives the real retry handler the way the answer-line gate tests do,
with a scripted reply whose text ends in a points label: with settled points 2
the wording leaves the body, with points 3 it stays and is recorded.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import (
    body_plain_text,
    body_text_lines,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    Env,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    document as make_document,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    item as make_item,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    source as make_source,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _reply(
    text: str, points: int | float, anchors: tuple[str, ...] = ("body:0001",)
) -> dict[str, JsonValue]:
    return {
        "title": None,
        "instructions": [],
        "answer_key_anchors": [],
        "items": [
            {
                "source_anchors": list(anchors),
                "outcome": "converted",
                "conflict_kind": None,
                "review_reason": None,
                "kind": "free_text",
                "key_source": None,
                "facit_text": None,
                "printed_label": None,
                "body": [
                    {
                        "segments": [
                            {
                                "kind": "text",
                                "text": text,
                                "accepted_values": [],
                                "asset_id": None,
                            }
                        ]
                    }
                ],
                "points": points,
                "choices": [],
                "match_left": [],
                "match_right": [],
                "match_pairs": [],
                "criteria": [],
            }
        ],
    }


async def test_retry_with_matching_points_loses_the_trailing_wording() -> None:
    env = Env()
    source = make_source(text="Svara utförligt och tydligt. (2 p)")
    document = make_document(
        lineage_id=uuid4(),
        items=(make_item("item_001", 1, anchor="body:0001", source=source),),
    )
    await env.seed(document)
    env.exchange.reply = _reply("Svara utförligt och tydligt. (2 p)", 2)

    response = await env.retry(document)

    item = response.item
    assert body_plain_text(item.body) == "Svara utförligt och tydligt."
    assert item.points == 2
    assert item.leftover_points_text is None


async def test_retry_with_differing_points_keeps_the_text_and_records_it() -> None:
    env = Env()
    source = make_source(text="Svara utförligt och tydligt. (2 p)")
    document = make_document(
        lineage_id=uuid4(),
        items=(make_item("item_001", 1, anchor="body:0001", source=source),),
    )
    await env.seed(document)
    env.exchange.reply = _reply("Svara utförligt och tydligt. (2 p)", 3)

    response = await env.retry(document, kind=NativeExamItemKind.FREE_TEXT)

    item = response.item
    assert body_plain_text(item.body) == "Svara utförligt och tydligt. (2 p)"
    assert item.points == 3
    assert item.leftover_points_text == "(2 p)"


_PROSE = "Svara utförligt."
_TIDNINGAR = "2. Tidningsartiklar (2 poäng)"
_IN_SENTENCE = "2. Svara (2 p) och motivera."


def _heading_saved_source(heading: str):
    saved = make_source(text=heading)
    first = saved.chunks[0].model_copy(update={"kind": "heading"})
    second = make_source(anchor="body:0002", text=_PROSE).chunks[0]
    return saved.model_copy(update={"chunks": (first, second)})


async def _retry_heading(heading: str, points: int | float):
    env = Env()
    saved_source = _heading_saved_source(heading)
    saved = make_document(
        lineage_id=uuid4(),
        items=(make_item("item_001", 1, anchor="body:0001", source=saved_source),),
    )
    await env.seed(saved)
    reply = _reply(_PROSE, points, anchors=("body:0001", "body:0002"))
    env.exchange.reply = reply
    response = await env.retry(saved)
    return response.item


async def test_item_heading_with_differing_points_keeps_its_label() -> None:
    """D12/F1: a differing first-paragraph label stays; the final gate owns removal."""

    item = await _retry_heading(_TIDNINGAR, 3)

    assert body_text_lines(item.body) == ("Tidningsartiklar (2 poäng)", _PROSE)
    assert item.points == 3
    assert item.leftover_points_text is None


async def test_item_heading_with_equal_points_loses_its_label() -> None:
    """D12: an equal first-paragraph label leaves through the final gate."""

    item = await _retry_heading(_TIDNINGAR, 2)

    assert body_text_lines(item.body) == ("Tidningsartiklar", _PROSE)
    assert item.points == 2
    assert item.leftover_points_text is None


async def test_in_sentence_item_heading_keeps_its_wording_at_equal_points() -> None:
    """D12/F1: in-sentence wording is never touched, even at equal points."""

    item = await _retry_heading(_IN_SENTENCE, 2)

    assert body_text_lines(item.body) == ("Svara (2 p) och motivera.", _PROSE)
    assert item.points == 2
    assert item.leftover_points_text is None


async def test_in_sentence_item_heading_keeps_its_wording_at_differing_points() -> None:
    """D12/F1: in-sentence wording is never touched, even at differing points."""

    item = await _retry_heading(_IN_SENTENCE, 3)

    assert body_text_lines(item.body) == ("Svara (2 p) och motivera.", _PROSE)
    assert item.points == 3
    assert item.leftover_points_text is None


_RANGE = "Använd mellan 3 poäng och 5 poäng."
_VOLT = (
    "Pelle gör en fin volt, Sara gör en ful. Sätt poäng på Sara och Pelles volter. "
    "Använd mellan 3 poäng och 5 poäng."
)
_SENTENCE = "Väljer eleven det får den 2 poäng."


@pytest.mark.parametrize(
    ("heading", "points", "expected"),
    [
        ("2. " + _RANGE, 5, (_RANGE, _PROSE)),
        ("2. " + _VOLT, 5, (_VOLT, _PROSE)),
        ("2. " + _SENTENCE, 2, (_SENTENCE, _PROSE)),
    ],
)
async def test_retry_range_or_sentence_heading_keeps_its_words(
    heading: str, points: int, expected: tuple[str, ...]
) -> None:
    """D12 Correction (rereview R1): the production retry keeps sentence and range endings."""

    item = await _retry_heading(heading, points)

    assert body_text_lines(item.body) == expected
    assert item.points == points
    assert item.leftover_points_text is None


def _build_with_heading(heading: str, points: int | float):
    """The build path for an item heading, through the production assembly."""

    from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import (
        assemble_build_result,
    )
    from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
        ProducedItem,
    )
    from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_item import (
        aligned_native_item,
    )
    from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk

    chunks = (
        DocxChunk("body:0001", "heading", heading, heading),
        DocxChunk("body:0002", "paragraph", _PROSE, _PROSE),
    )
    produced = ProducedItem.model_validate(
        {
            "source_anchors": ["body:0001"],
            "outcome": "converted",
            "review_reason": None,
            "kind": "free_text",
            "key_source": None,
            "facit_text": None,
            "body": [{"segments": [{"kind": "text", "text": _PROSE, "accepted_values": []}]}],
            "points": points,
            "choices": [],
        }
    )
    aligned = aligned_native_item(produced, language="sv", foreign_chunks=())
    built = assemble_build_result(
        origin_kind="docx_import",
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        accepted=((aligned, ("body:0001", "body:0002")),),
        review_reasons={},
        questions=(("body:0001", "body:0002"),),
    )
    (converted,) = built.document.items
    return converted


async def test_build_with_differing_points_keeps_the_heading_label() -> None:
    """D12/F1 on the build path: the differing heading label stays."""

    item = _build_with_heading(_TIDNINGAR, 3)

    assert body_text_lines(item.body) == ("Tidningsartiklar (2 poäng)", _PROSE)
    assert item.points == 3
    assert item.leftover_points_text is None


async def test_build_with_equal_points_loses_the_heading_label() -> None:
    """D12 on the build path: the equal heading label leaves."""

    item = _build_with_heading(_TIDNINGAR, 2)

    assert body_text_lines(item.body) == ("Tidningsartiklar", _PROSE)
    assert item.points == 2
    assert item.leftover_points_text is None


async def test_instruction_heading_with_item_none_still_shows_without_its_label() -> None:
    """Instruction and part headings (item None) keep today's deletion."""

    from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
    from skriptoteket.domain.curated_apps.exam_workspace.docx_heading_wording import (
        heading_wording,
    )

    chunk = DocxChunk("body:0009", "heading", "Del A (10 p)", "Del A (10 p)")

    assert heading_wording(chunk, None) == "Del A"
