"""Section instructions become parents or stay copied, on real chunks and real recordings.

Each build runs a recorded model response through the admission path and assembles it exactly as
a job does. Instructions and items are selected by source anchor; wording is read from the chunks.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

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
    NativeExamItemKind,
    NativeExamParent,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)

_FIXTURES = Path("tests/fixtures/exam_conversion")
_SECTIONED = "svenska_2_grammatik_omprov_variant_1_med_facit"
_REPEATED = "bf26_diagnostic_grammar_test_ht26_med_facit"
_ENGLISH = "bf26_english_1_unit_test_kap_1_2_med_facit"
_COURSE = "svenska_2_kursavslutande_prov_med_facit"


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

    def parent_with(self, anchor: str) -> NativeExamParent | None:
        return self.result.document.parent_of(self.item(anchor).item_id)

    def children(self, parent: NativeExamParent) -> list[NativeExamItem]:
        return [self.result.document.item_by_id(item_id) for item_id in parent.item_ids]


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
    admit_batch(json.loads((_FIXTURES / f"docx_build_v7/{stem}/round1.json").read_text()), state)
    assert state.instructions
    if not carry:
        state.instructions = ()
    return _Build(state, state.result())


def _text(item: NativeExamItem) -> str:
    return " ".join(" ".join((item.title or "", *item.plain_text_lines())).split())


def _prints(item: NativeExamItem, wording: str) -> bool:
    return " ".join(wording.split()) in _text(item)


def _carrying(build: _Build, wording: str) -> set[str | None]:
    return {item.source_anchor for item in build.result.document.items if _prints(item, wording)}


def _first_paragraph(item: NativeExamItem) -> str:
    return item.plain_text_lines()[0]


def _in_parents(build: _Build, wording: str) -> bool:
    return any(wording in parent.instruction for parent in build.result.document.parents)


def test_vocabulary_section_becomes_one_parent_with_the_shared_instruction():
    build = _build(_ENGLISH)
    wording = build.wording("body:0006")

    parent = build.parent_with("body:0007")
    assert parent is not None
    assert parent.instruction == (wording,)
    children = build.children(parent)
    assert len(children) == 24
    assert {c.kind for c in children} == {NativeExamItemKind.GAP_FILL}
    assert children[0].source_anchor == "body:0007"
    assert children[-1].source_anchor == "body:0053"
    assert not any(_prints(child, wording) for child in children)
    # The instruction reached items, so it is no document-level instruction.
    assert wording not in build.result.document.instructions
    # The next section's questions belong to the next parent, never to this one.
    other = build.parent_with("body:0075")
    assert other is not None and other.parent_id != parent.parent_id
    assert other.instruction == (build.wording("body:0074"),)


def test_every_parent_holds_contiguous_children_of_one_kind_in_order():
    for stem in (_ENGLISH, _REPEATED, _COURSE):
        build = _build(stem)
        document = build.result.document
        assert document.parents
        assert [p.parent_id for p in document.parents] == [
            f"parent_{n:03d}" for n in range(1, len(document.parents) + 1)
        ]
        for parent in document.parents:
            children = build.children(parent)
            assert len(children) >= 2
            assert len({c.kind for c in children}) == 1
            first = children[0].sequence
            assert [c.sequence for c in children] == list(range(first, first + len(children)))
        claimed = [item_id for parent in document.parents for item_id in parent.item_ids]
        assert len(claimed) == len(set(claimed))


def test_parent_instruction_covers_each_of_a_section_with_several_instruction_lines():
    build = _build(_REPEATED)
    first, second = build.wording("body:0004"), build.wording("body:0042")
    assert first != second

    opening = build.parent_with("body:0005")
    assert opening is not None
    assert opening.instruction == (first,)
    assert len(opening.item_ids) == 18
    # One question under a second instruction forms no run of two: it keeps a copy.
    single = build.item("body:0043")
    assert build.parent_with("body:0043") is None
    assert _first_paragraph(single) == second
    assert not _prints(single, first)
    resumed = build.parent_with("body:0046")
    assert resumed is not None and resumed.instruction == (build.wording("body:0045"),)
    assert build.wording("body:0045") == first
    assert resumed.parent_id != opening.parent_id


def test_exam_total_line_is_never_instruction_text_of_a_parent_or_an_item():
    build = _build(_REPEATED)
    total = build.wording("body:0003")
    assert "body:0003" in {a for v in build.state.instructions for a in v.source_anchors}

    assert _carrying(build, total) == set()
    assert not _in_parents(build, total)
    assert total in build.result.document.instructions


def test_questions_of_different_kinds_get_no_parent_and_the_run_is_reported():
    build = _build(_SECTIONED)
    wording = build.wording("body:0035")
    kinds = {build.item(a).kind for a in ("body:0037", "body:0045")}
    assert len(kinds) == 2

    assert build.result.document.parents == ()
    (event,) = [e for e in build.result.events if e.code == "parent_kinds_mixed"]
    assert "item_004" in event.detail and "item_005" in event.detail
    assert "body:0035" in event.anchors
    assert _carrying(build, wording) == {"body:0037", "body:0045"}


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

    # It reaches only some items of its run, so it is copied and builds no parent.
    assert _carrying(build, wording) == {"body:0056"}
    assert not _in_parents(build, wording)
    assert _first_paragraph(build.item("body:0056")) == wording
    # The later item, still inside the same section, is exactly what the model built.
    assert build.item("body:0066").body == _build(_SECTIONED, carry=False).item("body:0066").body


def test_section_headings_and_points_lines_are_never_instruction_text():
    build = _build(_SECTIONED)
    recorded = {a for v in build.state.instructions for a in v.source_anchors}
    headings = [a for a in recorded if build.state.chunk_by_anchor[a].kind == "heading"]
    # Two headings label the stretches of one passage inside an instruction lead-in.
    passage_labels = {"body:0077", "body:0081"}
    points = [a for a in recorded if a == "body:0004"]
    assert len(headings) == 6
    assert passage_labels <= set(headings)
    assert points

    for anchor in (*(set(headings) - passage_labels), *points):
        wording = build.wording(anchor)
        assert _carrying(build, wording) == set()
        assert not _in_parents(build, wording)
    for anchor in passage_labels:
        assert _carrying(build, build.wording(anchor)) == {"body:0085"}
        assert not _in_parents(build, build.wording(anchor))


def test_every_recorded_instruction_is_in_a_parent_or_an_item_or_stays_document_level():
    for stem in (_SECTIONED, _REPEATED, _ENGLISH, _COURSE):
        build = _build(stem)
        document = build.result.document
        kept = {line for parent in document.parents for line in parent.instruction}
        for instruction in build.state.instructions:
            texts = [build.state.chunk_by_anchor[a].text for a in instruction.source_anchors]
            reached = any(text in kept or _carrying(build, text) for text in texts)
            assert reached != (instruction.text in document.instructions), (
                stem,
                instruction.source_anchors,
            )
        # Without recorded instructions no parent exists and the items are unchanged.
        bare = _build(stem, carry=False).result.document
        assert bare.parents == ()
        assert len(bare.items) == len(document.items)


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


def test_course_exam_choice_section_is_one_parent_of_single_choice_questions():
    build = _build(_COURSE)
    parent = build.parent_with("body:0010")

    assert parent is not None
    assert parent.instruction == (build.wording("body:0009"),)
    assert len(parent.item_ids) == 15
    assert {c.kind for c in build.children(parent)} == {NativeExamItemKind.SINGLE_CHOICE}
    assert [c.sequence for c in build.children(parent)] == list(range(1, 16))
