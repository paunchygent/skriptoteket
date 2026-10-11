"""Accepted answer forms a gap gains, judged against real recordings and gold."""

import json
import re
from uuid import uuid4

import pytest

from scripts.exam_conversion_eval.gold import GoldExam
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    definition_context,
    with_accepted_forms,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
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
        assert set(original) <= set(values)
        # Every gold answer is accepted, including each part of a slash-joined facit form,
        # and nothing outside gold is added.
        assert {g.casefold() for g in gold_values} <= {v.casefold() for v in values}
        assert {v.casefold() for v in values} <= {g.casefold() for g in gold_values}
    # Short forms listed without "=" define nothing.
    item, widened = pairs[1]
    assert item.source_anchors[0] == "body:0016"
    assert _gaps(widened) == _gaps(item)


_COURSE_FINAL = "svenska_2_kursavslutande_prov_med_facit"
# Live rounds that return the defining instruction inside the item, and as its own instruction.
_DEFINING_RECORDINGS = ("docx_build_v9", "docx_build_round3_live2")


def _defined(chunks: dict[str, DocxChunk], item: ProducedItem) -> dict[str, str]:
    """Each short form the source defines with " = " in the lines the item spans."""
    positions = sorted(chunks)
    first, last = positions.index(item.source_anchors[0]), positions.index(item.source_anchors[-1])
    text = "\n".join(chunks[a].text for a in positions[first : last + 1])
    return dict(re.findall(r"(\S+) = (\w+)", text))


_Found = tuple[ProducedItem, dict[str, str]]


def test_the_separately_returned_instruction_lies_inside_the_defining_items():
    """The live round returned the defining line as an instruction printed inside each item."""
    content = json.loads(
        (FIXTURES / "docx_build_round3_live2" / _COURSE_FINAL / "round1.json").read_text()
    )
    _, found = _admitted("docx_build_round3_live2", as_terms=False)
    assert found
    for item, _ in found:
        assert not any(" = " in chunk_text for chunk_text in _own_texts(item))
        assert any(
            " = " in m["text"]
            and item.source_anchors[0] < m["source_anchors"][0] < item.source_anchors[-1]
            for m in content["instructions"]
        ), item.source_anchors


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
        for original, values in zip(_gaps(item), _gaps(widened), strict=True):
            assert set(original) <= set(values)


def _own_texts(item: ProducedItem) -> list[str]:
    chunks = chunks_by_anchor(_COURSE_FINAL)
    return [chunks[a].text for a in item.source_anchors]


def _admitted(recording: str, as_terms: bool) -> tuple[NativeExamDocument, list[_Found]]:
    """The recorded round, admitted and built; ``as_terms`` makes each defined facit the term."""
    chunks = chunks_by_anchor(_COURSE_FINAL)
    content = json.loads((FIXTURES / recording / _COURSE_FINAL / "round1.json").read_text())
    found: list[_Found] = []
    for raw in content["items"]:
        item = ProducedItem.model_validate(raw)
        defined = _defined(chunks, item)
        if not (_gaps(item) and defined and all(set(g) <= set(defined) for g in _gaps(item))):
            continue
        if as_terms:
            for paragraph in raw["body"]:
                for segment in paragraph["segments"]:
                    if segment["kind"] == "gap":
                        segment["accepted_values"] = [
                            defined[v] for v in segment["accepted_values"]
                        ]
        # Return exactly what admission receives, including the term-only mutation.
        found.append((ProducedItem.model_validate(raw), defined))
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename=f"{_COURSE_FINAL}.docx",
        source_sha256="0" * 64,
        chunks=tuple(chunks.values()),
    )
    admit_batch(content, state)
    return state.result().document, found


@pytest.mark.parametrize("as_terms", [False, True], ids=["short_form_facit", "term_facit"])
@pytest.mark.parametrize("recording", _DEFINING_RECORDINGS)
def test_admitted_defined_gaps_accept_both_halves(recording: str, as_terms: bool):
    """D13 through admission and the build: a facit giving either half accepts both."""
    document, found = _admitted(recording, as_terms)
    assert len(found) >= 2
    for item, defined in found:
        native = next(i for i in document.items if i.source_anchor == item.source_anchors[0])
        short_by_term = {term: short for short, term in defined.items()}
        for submitted, gap in zip(_gaps(item), native.gaps, strict=True):
            if as_terms:
                assert set(submitted) <= set(short_by_term)
                short_forms = {short_by_term[term] for term in submitted}
                terms = set(submitted)
                assert short_forms.isdisjoint(submitted)
            else:
                assert set(submitted) <= set(defined)
                short_forms = set(submitted)
                terms = {defined[short] for short in submitted}
                assert terms.isdisjoint(submitted)
            assert short_forms <= set(gap.accepted_values)
            assert terms <= set(gap.accepted_values)
            assert set(submitted) <= set(gap.accepted_values)
