"""Accepted answer forms a gap gains, judged against real recordings and gold."""

import re

from scripts.exam_conversion_eval.gold import GoldExam
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    definition_context,
    with_accepted_forms,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from tests.unit.domain.curated_apps.exam_workspace.source_rules_test_support import (
    FIXTURES,
    chunks_by_anchor,
    recorded_produced_items,
)


def _gaps(item: ProducedItem) -> list[list[str]]:
    return [list(s.accepted_values) for p in item.body for s in p.segments if s.kind == "gap"]


def _gold_gaps(docx: str) -> list[list[list[str]]]:
    gold = GoldExam.model_validate_json((FIXTURES / f"docx_corpus/gold/{docx}.json").read_text())
    return [[list(gap.accepted_values) for gap in item.gaps] for item in gold.questions]


def _widened(recording: str, docx: str) -> list[tuple[ProducedItem, ProducedItem]]:
    chunks = PythonDocxExamChunker().chunk(
        content=(FIXTURES / f"docx_corpus/{docx}.docx").read_bytes()
    )
    return [
        (item, with_accepted_forms(item, definition_context(chunks, item.source_anchors)))
        for item in recorded_produced_items(recording)
    ]


def test_facit_term_defined_in_the_section_instruction_also_accepts_its_short_form():
    docx = "svenska_2_grammatik_omprov_variant_2_med_facit"
    pairs = _widened("svenska_2_grammatik_variant_2_docx_build_response.json", docx)
    gold = _gold_gaps(docx)
    # The comparator pairs recorded and gold items by position.
    item, widened = pairs[3]
    assert item.source_anchors[0] == "body:0037"
    for original, values, gold_values in zip(_gaps(item), _gaps(widened), gold[3], strict=True):
        assert len(values) > len(original)
        # Every gold answer is accepted, including each part of a slash-joined facit form,
        # and nothing outside gold is added.
        assert {g.casefold() for g in gold_values} <= {v.casefold() for v in values}
        assert {v.casefold() for v in values} <= {g.casefold() for g in gold_values}
    # Short forms listed without "=" define nothing.
    item, widened = pairs[1]
    assert item.source_anchors[0] == "body:0016"
    assert _gaps(widened) == _gaps(item)


def test_facit_already_in_short_form_gains_no_term():
    docx = "svenska_2_kursavslutande_prov_med_facit"
    chunks = chunks_by_anchor(docx)
    # The questions' own instructions define their labels with "=".
    assert sum(chunks[a].text.count("=") for a in chunks) >= 6
    pairs = _widened("svenska_2_kursavslutande_prov_docx_build_response.json", docx)
    assert [_gaps(widened) for _, widened in pairs] == [_gaps(item) for item, _ in pairs]


def test_term_added_beside_a_short_form_facit_is_kept():
    """A live round added each defined term next to the short form the inline facit writes."""
    chunks = PythonDocxExamChunker().chunk(
        content=(FIXTURES / "docx_corpus/svenska_2_kursavslutande_prov_med_facit.docx").read_bytes()
    )
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    item = next(
        item
        for item in recorded_produced_items(
            "svenska_2_kursavslutande_prov_docx_build_response.json"
        )
        if item.source_anchors[0] == "body:0061"
    )
    instruction = by_anchor["body:0062"].text
    assert instruction.count(" = ") == 3

    def defined_term(short: str) -> str:
        match = re.search(re.escape(short) + r" = (\w+)", instruction)
        assert match is not None
        return match.group(1)

    padded = item.model_copy(
        update={
            "body": tuple(
                p.model_copy(
                    update={
                        "segments": tuple(
                            s.model_copy(
                                update={
                                    "accepted_values": (
                                        *s.accepted_values,
                                        *(defined_term(v) for v in s.accepted_values),
                                    )
                                }
                            )
                            if s.kind == "gap"
                            else s
                            for s in p.segments
                        )
                    }
                )
                for p in item.body
            )
        }
    )
    assert padded != item

    widened = with_accepted_forms(padded, definition_context(chunks, item.source_anchors))

    assert _gaps(widened) == _gaps(padded)


def test_facit_printed_with_a_typographic_apostrophe_also_accepts_the_keyboard_form():
    """The source prints the facit and its "also accepted" form with the same curly apostrophe."""
    docx = "bf26_english_1_unit_test_kap_1_2_med_facit"
    chunks = chunks_by_anchor(docx)
    pairs = _widened(f"docx_build_v5/{docx}/round1.json", docx)
    gold = _gold_gaps(docx)
    curly = [
        index
        for index, (item, _) in enumerate(pairs)
        if any("\u2019" in value for gap in _gaps(item) for value in gap)
    ]
    assert curly
    for index in curly:
        item, widened = pairs[index]
        facit = " ".join(chunks[a].text for a in chunks if a not in item.source_anchors)
        assert all(value in facit for gap in _gaps(item) for value in gap)
        for values, gold_values in zip(_gaps(widened), gold[index], strict=True):
            assert set(gold_values) <= set(values)
