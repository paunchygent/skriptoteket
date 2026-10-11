"""Section instructions repeated into the items they serve, on real chunks and real recordings.

Each build runs a recorded model response through the admission path and assembles it exactly as
a job does. Instructions and items are selected by source anchor; wording is read from the chunks.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from scripts.exam_conversion_eval.compare import compare_native_exam
from scripts.exam_conversion_eval.gold import GoldExam
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import assemble_build_result
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildResult
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    defined_terms,
    uses_term,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItem,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)

_FIXTURES = Path("tests/fixtures/exam_conversion")
_SECTIONED = "svenska_2_grammatik_omprov_variant_1_med_facit"
_REPEATED = "bf26_diagnostic_grammar_test_ht26_med_facit"


@dataclass(frozen=True)
class _Build:
    state: DocxBuildState
    result: DocxBuildResult

    def wording(self, anchor: str) -> str:
        return self.state.chunk_by_anchor[anchor].text

    def item(self, anchor: str) -> NativeExamItem:
        return next(item for item in self.result.document.items if item.source_anchor == anchor)

    def own_chunks(self, anchor: str) -> list[DocxChunk]:
        """The chunks of the accepted item that opens at ``anchor``."""
        (anchors,) = (a for _, a in self.state.accepted if a[0] == anchor)
        return [self.state.chunk_by_anchor[a] for a in anchors]

    def index(self, anchor: str) -> int:
        return self.result.document.items.index(self.item(anchor))


def _build(stem: str, *, carry: bool = True) -> _Build:
    chunks = PythonDocxExamChunker().chunk(
        content=(_FIXTURES / f"docx_corpus/{stem}.docx").read_bytes()
    )
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename=f"{stem}.docx",
        source_sha256="0" * 64,
        chunks=chunks,
    )
    admit_batch(json.loads((_FIXTURES / f"docx_build_v6/{stem}/round1.json").read_text()), state)
    assert state.instructions
    if not carry:
        state.instructions = ()
    return _Build(state, state.result())


def _gold(stem: str) -> GoldExam:
    return GoldExam.model_validate_json((_FIXTURES / f"docx_corpus/gold/{stem}.json").read_text())


def _text(item: NativeExamItem) -> str:
    return " ".join(" ".join((item.title or "", *item.plain_text_lines())).split())


def _prints(item: NativeExamItem, wording: str) -> bool:
    return " ".join(wording.split()) in _text(item)


def _carrying(build: _Build, wording: str) -> set[str | None]:
    return {item.source_anchor for item in build.result.document.items if _prints(item, wording)}


def _first_paragraph(item: NativeExamItem) -> str:
    return item.plain_text_lines()[0]


def _content_failures(build: _Build, stem: str) -> set[str | None]:
    comparison = compare_native_exam(_gold(stem), build.result.document)
    return {
        build.result.document.items[entry.index].source_anchor
        for entry in comparison.items
        if "content_present" in entry.failed_principles()
    }


def test_term_defining_instruction_reaches_only_the_items_naming_its_terms():
    build = _build(_SECTIONED)
    wording = build.wording("body:0035")
    terms = defined_terms(wording)
    assert terms

    assert _carrying(build, wording) == {"body:0037", "body:0045"}
    for anchor in ("body:0037", "body:0045"):
        assert _first_paragraph(build.item(anchor)) == wording
        assert uses_term(terms, build.own_chunks(anchor))
    # The next section's item names the same short forms, but a section heading closes the run.
    assert uses_term(terms, build.own_chunks("body:0056"))
    assert not _prints(build.item("body:0056"), wording)


def test_instruction_listing_types_is_withheld_from_a_later_item_that_names_none():
    build = _build(_SECTIONED)
    wording = build.wording("body:0054")
    terms = defined_terms(wording)
    assert len(terms) >= 2
    assert uses_term(terms, build.own_chunks("body:0056"))
    assert not uses_term(terms, build.own_chunks("body:0066"))

    assert _carrying(build, wording) == {"body:0056"}
    assert _first_paragraph(build.item("body:0056")) == wording
    # The later item, still inside the same section, is exactly what the model built.
    assert build.item("body:0066").body == _build(_SECTIONED, carry=False).item("body:0066").body


def test_headings_and_points_lines_are_never_carried_into_items():
    build = _build(_SECTIONED)
    recorded = {a for v in build.state.instructions for a in v.source_anchors}
    headings = [a for a in recorded if build.state.chunk_by_anchor[a].kind == "heading"]
    points = [a for a in recorded if a == "body:0004"]
    assert len(headings) == 4
    assert points

    for anchor in (*headings, *points):
        assert _carrying(build, build.wording(anchor)) == set()


def test_exam_total_line_is_never_carried_and_every_item_carries_one_instruction():
    build = _build(_REPEATED)
    total = build.wording("body:0003")
    first, second = build.wording("body:0004"), build.wording("body:0042")
    assert "body:0003" in {a for v in build.state.instructions for a in v.source_anchors}
    assert first != second

    assert _carrying(build, total) == set()
    for item in build.result.document.items:
        assert [_prints(item, first), _prints(item, second)].count(True) == 1, item.source_anchor


def test_item_after_a_second_instruction_carries_only_that_instruction():
    build = _build(_REPEATED)
    first, second = build.wording("body:0004"), build.wording("body:0042")
    assert build.wording("body:0045") == first

    after_second = build.item("body:0043")
    assert _first_paragraph(after_second) == second
    assert not _prints(after_second, first)
    after_third = build.item("body:0046")
    assert _first_paragraph(after_third) == first
    assert not _prints(after_third, second)
    before_second = build.item("body:0040")
    assert _first_paragraph(before_second) == first
    assert not _prints(before_second, second)


def test_instruction_already_printed_in_the_item_is_not_repeated():
    build = _build(_SECTIONED)
    anchors = {item.source_anchor: anchors for item, anchors in build.state.accepted}
    carried = {
        anchor: item
        for anchor in anchors
        if _prints(item := build.item(str(anchor)), build.wording("body:0035"))
    }
    assert set(carried) == {"body:0037", "body:0045"}

    # Assemble again from the items that already carry the instruction.
    again = assemble_build_result(
        document_id=build.result.document.document_id,
        filename=build.result.document.origin.source_filename or "",
        source_sha256="0" * 64,
        chunks=build.state.chunks,
        accepted=tuple(
            (build.item(str(anchor)), anchor_tuple) for anchor, anchor_tuple in anchors.items()
        ),
        review_reasons={},
        key_anchors=frozenset(build.state.key_anchors),
        title=build.state.title,
        instructions=build.state.instructions,
    )
    assert [item.body for item in again.document.items] == [
        item.body for item in build.result.document.items
    ]
    wording = " ".join(build.wording("body:0035").split())
    for anchor in carried:
        assert _text(again.document.items[build.index(str(anchor))]).count(wording) == 1


def test_instruction_printed_by_an_item_is_kept_once_while_its_sibling_still_gets_it():
    build = _build(_SECTIONED)
    wording = build.wording("body:0035")
    printed = NativeParagraph(segments=(NativeTextSegment(text=wording),))
    accepted = tuple(
        (
            item.model_copy(update={"body": (printed, *item.body)})
            if anchors[0] == "body:0037"
            else item,
            anchors,
        )
        for item, anchors in build.state.accepted
    )

    again = assemble_build_result(
        document_id=build.result.document.document_id,
        filename="x.docx",
        source_sha256="0" * 64,
        chunks=build.state.chunks,
        accepted=accepted,
        review_reasons={},
        instructions=build.state.instructions,
    )

    by_anchor = {item.source_anchor: item for item in again.document.items}
    for anchor in ("body:0037", "body:0045"):
        assert _text(by_anchor[anchor]).count(" ".join(wording.split())) == 1
        assert _first_paragraph(by_anchor[anchor]) == wording


def test_carried_instructions_keep_every_gold_wording_present():
    with_carry = _build(_SECTIONED)
    without_carry = _build(_SECTIONED, carry=False)

    assert _content_failures(with_carry, _SECTIONED) == set()
    # The comparator is not vacuous: gold wording of the served items needs the carried line.
    assert {"body:0037", "body:0045", "body:0056"} <= _content_failures(without_carry, _SECTIONED)


def test_repeated_instruction_runs_keep_gold_wording_present_for_every_converted_item():
    build = _build(_REPEATED)
    dropped = build.item("body:0078")
    assert dropped.review.state.value == "review_required"

    assert _content_failures(build, _REPEATED) == {"body:0078"}
    assert "body:0043" in _content_failures(_build(_REPEATED, carry=False), _REPEATED)
