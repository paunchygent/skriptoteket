"""A chunk the grouping marks as governing several questions belongs to the section parent (D40).

``docx_build_v15_governing_chunk_in_item`` holds unedited live recordings of two
one-family-per-batch runs in which a converter reply lists a governing chunk in a question's
source_anchors instead of its instructions. ``docx_build_v15_low17_governing_heading`` holds a
live run whose grouping is edited so that a section heading governs a run of questions (see
its README). In each, the governing chunk is shown once, as the parent's instruction, and the
parent holds exactly the items of the questions the grouping says it governs.
"""

from pathlib import Path

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline import (
    DocxConversionOutcome,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamParent,
    NativeTextSegment,
)
from skriptoteket.protocols.docx_conversion_progress import ConversionUpdate
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    FIXTURES,
    SecondWaveByAnchor,
    build_replay,
    corpus_chunks,
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_IN_ITEM = FIXTURES / "docx_build_v15_governing_chunk_in_item"
_HEADING = FIXTURES / "docx_build_v15_low17_governing_heading"
_ENGLISH = "bf26_english_1_unit_test_kap_1_2_med_facit"
_SWEDISH = "svenska_2_kursavslutande_prov_med_facit"


def _governs(exam: str, root: Path, anchor: str) -> list[str]:
    contexts = recording(exam, "docx_grouping_1", root=root)["shared_contexts"]
    assert isinstance(contexts, list)
    (context,) = [c for c in contexts if isinstance(c, dict) and c["anchor"] == anchor]
    governs = context["governs"]
    assert isinstance(governs, list) and len(governs) >= 2
    return [str(q) for q in governs]


def _listed_in_an_item(exam: str, root: Path, anchor: str) -> bool:
    for path in sorted((root / exam).glob("docx_w*.json")):
        items = recording(exam, path.stem, root=root)["items"]
        assert isinstance(items, list)
        for item in items:
            assert isinstance(item, dict)
            anchors = item["source_anchors"]
            assert isinstance(anchors, list)
            if anchor in anchors:
                return True
    return False


async def _convert(exam: str, root: Path) -> DocxConversionOutcome:
    replay = build_replay(
        exam, root=root, families_per_batch=1, provider=SecondWaveByAnchor(exam, root=root)
    )
    return await replay.pipeline.convert(job=replay.job())


def _governed_items(update: ConversionUpdate, governs: list[str]) -> list[str]:
    return [item_id for qid in governs for item_id in update.item_ids[qid]]


def _parent_of(document: NativeExamDocument, item_ids: list[str]) -> NativeExamParent:
    parent = document.parent_of(item_ids[0])
    assert parent is not None, "the first governed question has no section parent"
    return parent


async def test_a_governing_chunk_an_item_prints_at_its_start_moves_to_the_parent():
    anchor = "body:0074"
    governs = _governs(_SWEDISH, _IN_ITEM, anchor)
    assert _listed_in_an_item(_SWEDISH, _IN_ITEM, anchor)
    text = {chunk.anchor: chunk.text for chunk in corpus_chunks(_SWEDISH)}

    outcome = await _convert(_SWEDISH, _IN_ITEM)

    document = outcome.result.document
    governed = _governed_items(outcome.update, governs)
    parent = _parent_of(document, governed)
    assert parent.instruction == (text[anchor],)
    assert list(parent.item_ids) == governed
    first = next(item for item in document.items if item.item_id == governed[0])
    assert first.source_anchor != anchor
    opening = first.body[0].segments[0]
    assert isinstance(opening, NativeTextSegment)
    assert opening.text.startswith("Noah"), "the item still prints the parent's instruction"
    codes = [(e.code, e.anchors) for e in outcome.result.events]
    assert ("governing_text_kept", (anchor,)) not in codes
    assert [e for e in outcome.result.events if e.code == "parent_differs_from_grouping"] == []


async def test_a_governing_chunk_that_is_an_item_whole_body_is_kept_there_and_reported():
    """Removing the only body text would leave the item without a body, so the item keeps
    it, an event names the chunk, and the parent still shows it."""
    listed, instruction = "body:0060", "body:0058"
    governs = _governs(_ENGLISH, _IN_ITEM, listed)
    assert governs == _governs(_ENGLISH, _IN_ITEM, instruction)
    assert _listed_in_an_item(_ENGLISH, _IN_ITEM, listed)
    text = {chunk.anchor: chunk.text for chunk in corpus_chunks(_ENGLISH)}

    outcome = await _convert(_ENGLISH, _IN_ITEM)

    document = outcome.result.document
    governed = _governed_items(outcome.update, governs)
    parent = _parent_of(document, governed)
    assert parent.instruction == (text[instruction], text[listed])
    assert list(parent.item_ids) == governed
    assert all(item.source_anchor != listed for item in document.items)
    codes = [(e.code, e.anchors) for e in outcome.result.events]
    assert ("governing_text_kept", (listed,)) in codes
    assert [e for e in outcome.result.events if e.code == "parent_differs_from_grouping"] == []


async def test_a_governing_heading_keeps_its_text_on_the_parent():
    heading, instruction = "body:0006", "body:0009"
    governs = _governs(_SWEDISH, _HEADING, heading)
    assert governs == _governs(_SWEDISH, _HEADING, instruction)
    chunks = {chunk.anchor: chunk for chunk in corpus_chunks(_SWEDISH)}
    assert chunks[heading].kind == "heading"

    outcome = await _convert(_SWEDISH, _HEADING)

    document = outcome.result.document
    governed = _governed_items(outcome.update, governs)
    parent = _parent_of(document, governed)
    assert parent.instruction == (chunks[heading].text, chunks[instruction].text)
    assert list(parent.item_ids) == governed
    assert chunks[heading].text not in document.instructions
    assert [e for e in outcome.result.events if e.code == "parent_differs_from_grouping"] == []
