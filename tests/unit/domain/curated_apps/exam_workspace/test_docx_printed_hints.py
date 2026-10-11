"""Cues printed beside a blank become student-visible text, on a real recording."""

import re

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import with_printed_hints
from tests.unit.domain.curated_apps.exam_workspace.source_rules_test_support import (
    chunks_by_anchor,
    recorded_produced_items,
)

_HINT_DOCX = "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit"
_HINT_RECORDING = f"docx_build_v6/{_HINT_DOCX}/round1.json"


def _recorded(recording: str, anchor: str) -> ProducedItem:
    return next(
        item for item in recorded_produced_items(recording) if item.source_anchors[0] == anchor
    )


def _body_segments(item: ProducedItem) -> list[ProducedSegment]:
    return [segment for paragraph in item.body for segment in paragraph.segments]


def _text_of(item: ProducedItem) -> str:
    return "".join(s.text or "" for s in _body_segments(item))


def _gap_hints(item: ProducedItem) -> list[str | None]:
    return [s.hint for s in _body_segments(item) if s.kind == "gap"]


def _with_hints(item: ProducedItem, hints: list[str]) -> ProducedItem:
    """The item with each gap's hint set, in gap order."""
    pending = iter(hints)
    paragraphs = tuple(
        paragraph.model_copy(
            update={
                "segments": tuple(
                    segment.model_copy(update={"hint": next(pending)})
                    if segment.kind == "gap"
                    else segment
                    for segment in paragraph.segments
                )
            }
        )
        for paragraph in item.body
    )
    return item.model_copy(update={"body": paragraphs})


def test_cue_the_source_prints_in_brackets_becomes_bracketed_text_after_its_gap():
    chunks = chunks_by_anchor(_HINT_DOCX)
    item = _recorded(_HINT_RECORDING, "body:0034")
    (cue,) = _gap_hints(item)
    assert cue
    sources = [chunks[a] for a in item.source_anchors]
    assert f"({cue})" in sources[0].text
    assert cue not in _text_of(item)

    folded = with_printed_hints(item, sources)

    before, after = _body_segments(item), _body_segments(folded)
    assert after[0].kind == "gap"
    assert after[0].hint is None
    assert after[0].accepted_values == before[0].accepted_values
    assert (after[1].kind, after[1].text) == ("text", f" ({cue})")
    assert after[2:] == before[1:]


def test_cue_already_printed_in_the_paragraph_is_not_added_twice():
    chunks = chunks_by_anchor(_HINT_DOCX)
    item = _recorded(_HINT_RECORDING, "body:0034")
    sources = [chunks[a] for a in item.source_anchors]
    (cue,) = _gap_hints(item)
    assert cue

    folded = with_printed_hints(item, sources)
    refolded = with_printed_hints(_with_hints(folded, [cue]), sources)

    assert _text_of(refolded) == _text_of(folded)
    assert _text_of(refolded).count(f"({cue})") == 1
    assert _gap_hints(refolded) == [None]


def test_every_gap_cue_the_text_already_prints_is_folded_away_without_new_text():
    docx = "bf26_diagnostic_grammar_test_ht26_med_facit"
    chunks = chunks_by_anchor(docx)
    item = _recorded(f"docx_build_v6/{docx}/round1.json", "body:0017")
    sources = [chunks[a] for a in item.source_anchors]
    cues = [cue for cue in re.findall(r"\(([^()]+)\)", sources[0].text) if cue in _text_of(item)]
    assert len(cues) == len(_gap_hints(item)) == 2
    assert _gap_hints(item) == [None, None]

    folded = with_printed_hints(_with_hints(item, cues), sources)

    assert _body_segments(folded) == _body_segments(item)


def test_cue_the_source_does_not_bracket_is_appended_as_plain_text():
    chunks = chunks_by_anchor(_HINT_DOCX)
    item = _recorded(_HINT_RECORDING, "body:0034")
    sources = [chunks[a] for a in item.source_anchors]
    plain = sources[0].text.split(".", 1)[0] + "."
    assert plain in sources[0].text
    assert f"({plain})" not in sources[0].text

    folded = with_printed_hints(_with_hints(item, [plain]), sources)

    assert _body_segments(folded)[1].text == f" {plain}"
    assert _gap_hints(folded) == [None]
