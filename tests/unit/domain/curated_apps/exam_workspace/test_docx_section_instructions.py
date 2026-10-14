"""Section instructions become parents or stay copied, on the fresh live recordings.

Each build runs the production pipeline over one exam's fresh recordings and asserts on the
assembled document. Instructions and items are selected by source anchor; wording is read
from the corpus chunks, and every recorded instruction must land in a parent, an item, or
the document's own instruction list.
"""

import json
import re
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    defined_terms,
    points_line,
    uses_term,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamItem,
    NativeExamItemKind,
    NativeExamParent,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    RECORDINGS,
    build_replay,
    corpus_chunks,
)
from tests.unit.domain.curated_apps.exam_workspace.source_rules_test_support import (
    recorded_produced_items,
)

_NUMBERED_LINE = re.compile(r"^\s*(?:[^\W\d_]+\s+)?\d{1,3}\s*[.)]\s+")

_GRAMMAR_1 = "svenska_2_grammatik_omprov_variant_1_med_facit"
_GRAMMAR_2 = "svenska_2_grammatik_omprov_variant_2_med_facit"
_POETRY = "chapter_4_poetry_and_lyrics_quiz_med_facit"
_CLEAN = (_GRAMMAR_1, _GRAMMAR_2, _POETRY)


@dataclass(frozen=True)
class _Build:
    document: NativeExamDocument
    chunks: dict[str, DocxChunk]

    def wording(self, anchor: str) -> str:
        return self.chunks[anchor].text

    def item(self, anchor: str) -> NativeExamItem:
        return next(item for item in self.document.items if item.source_anchor == anchor)

    def parent_of(self, anchor: str) -> NativeExamParent | None:
        return self.document.parent_of(self.item(anchor).item_id)

    def children(self, parent: NativeExamParent) -> list[NativeExamItem]:
        return [self.document.item_by_id(item_id) for item_id in parent.item_ids]


_BUILDS: dict[str, _Build] = {}


async def _build(exam: str) -> _Build:
    if exam not in _BUILDS:
        replay = build_replay(exam)
        outcome = await replay.pipeline.convert(job=replay.job())
        # These exams' recordings convert without a producer fault; a fault here would
        # mean the test's instruction-placement claim rests on a broken run.
        assert not outcome.result.events, exam
        _BUILDS[exam] = _Build(
            outcome.result.document, {chunk.anchor: chunk for chunk in corpus_chunks(exam)}
        )
    return _BUILDS[exam]


def _item_text(item: NativeExamItem) -> str:
    return " ".join(" ".join(item.plain_text_lines()).split())


def _recorded_instructions(exam: str) -> list[tuple[tuple[str, ...], str]]:
    """Every instruction the exam's envelopes returned, as (anchors, text)."""
    entries: list[tuple[tuple[str, ...], str]] = []
    for path in sorted((RECORDINGS / exam).glob("docx_w*.json")):
        content = json.loads(path.read_text())
        for raw in content.get("instructions", []):
            anchors = tuple(anchor for anchor in raw["source_anchors"] if isinstance(anchor, str))
            entries.append((anchors, str(raw["text"])))
    return entries


def _shown_variants(text: str) -> tuple[str, ...]:
    """The instruction text as printed, also without its points label and question number."""
    normalized = _NUMBERED_LINE.sub(
        "", " ".join(POINT_LABEL.sub(" ", text).split()), count=1
    ).rstrip(" ,;")
    return (text, normalized) if normalized != text else (text,)


async def test_a_section_instruction_becomes_one_parent_over_its_run():
    build = await _build(_GRAMMAR_1)
    wording = build.wording("body:0035")

    parent = build.parent_of("body:0037")
    assert parent is not None and parent == build.parent_of("body:0045")
    # The printed section heading opens the parent's instruction (T2, 39-05-08).
    assert body_text_lines(parent.instruction) == ("Del 2: Satsdelar", wording)
    assert [child.source_anchor for child in build.children(parent)] == [
        "body:0037",
        "body:0045",
    ]
    # The instruction reached items, so it is no document-level instruction.
    assert wording not in body_text_lines(build.document.instructions)
    # The next section's questions belong to the next parent, never to this one.
    other = build.parent_of("body:0056")
    assert other is not None and other.parent_id != parent.parent_id
    assert body_text_lines(other.instruction) == ("Del 3: Bisatser och komplex meningsbyggnad",)


async def test_every_parent_holds_contiguous_children_in_order_and_never_repeats_its_instruction():
    for exam in _CLEAN:
        build = await _build(exam)
        document = build.document
        assert document.parents
        assert [p.parent_id for p in document.parents] == [
            f"parent_{n:03d}" for n in range(1, len(document.parents) + 1)
        ]
        for parent in document.parents:
            children = build.children(parent)
            assert len(children) >= 2
            first = children[0].sequence
            assert [c.sequence for c in children] == list(range(first, first + len(children)))
            lines = body_text_lines(parent.instruction)
            for child in children:
                assert not set(lines) & set(child.plain_text_lines()), (exam, child.source_anchor)
        claimed = [item_id for parent in document.parents for item_id in parent.item_ids]
        assert len(claimed) == len(set(claimed))


async def test_a_run_of_one_kind_in_a_section_is_one_parent_of_that_kind():
    build = await _build(_POETRY)
    parent = build.parent_of("body:0006")

    assert parent is not None and parent == build.parent_of("body:0015")
    assert [child.source_anchor for child in build.children(parent)] == [
        "body:0006",
        "body:0009",
        "body:0012",
        "body:0015",
    ]
    assert {child.kind for child in build.children(parent)} == {NativeExamItemKind.SINGLE_CHOICE}
    assert body_text_lines(parent.instruction) == ("Part 1",)


async def test_points_lines_are_structure_and_never_reach_a_parent_or_an_item():
    for exam in _CLEAN:
        build = await _build(exam)
        document = build.document

        assert not [
            line
            for parent in document.parents
            for line in body_text_lines(parent.instruction)
            if points_line(line)
        ]
        assert not [
            line for item in document.items for line in item.plain_text_lines() if points_line(line)
        ]
        # The exam total is kept, once, as a document-level instruction; the per-question
        # points lines are structure and reach neither a parent nor an item.
        totals = [
            chunk.text
            for chunk in build.chunks.values()
            if points_line(chunk.text) and chunk.text.casefold().startswith("total")
        ]
        assert totals
        kept = body_text_lines(document.instructions)
        assert all(total in kept for total in totals), exam


async def test_a_shared_term_defining_instruction_is_parented_and_not_copied():
    build = await _build(_GRAMMAR_1)
    wording = build.wording("body:0035")
    terms = defined_terms(wording)
    assert terms

    parent = build.parent_of("body:0037")
    assert parent is not None
    for anchor in ("body:0037", "body:0045"):
        raw = next(
            item for item in recorded_produced_items(_GRAMMAR_1) if item.source_anchors[0] == anchor
        )
        assert uses_term(terms, (build.chunks[a] for a in raw.source_anchors))
        assert wording not in build.item(anchor).plain_text_lines()


async def test_an_instruction_listing_types_reaches_only_the_item_that_names_them():
    build = await _build(_GRAMMAR_1)
    wording = build.wording("body:0054")
    carriers = [
        item.source_anchor for item in build.document.items if wording in item.plain_text_lines()
    ]

    # It reaches only some items of its run, so it is copied and builds no parent line.
    assert carriers == ["body:0056"]
    parent = build.parent_of("body:0056")
    assert parent is not None
    assert wording not in body_text_lines(parent.instruction)
    assert wording not in body_text_lines(build.document.instructions)
    assert build.item("body:0056").plain_text_lines()[0] == wording


async def test_every_recorded_instruction_is_in_a_parent_or_an_item_or_stays_document_level():
    for exam in _CLEAN:
        build = await _build(exam)
        document = build.document
        kept = {line for parent in document.parents for line in body_text_lines(parent.instruction)}
        item_texts = [_item_text(item) for item in document.items]
        for anchors, text in _recorded_instructions(exam):
            reached = any(
                variant in kept or any(variant in item_text for item_text in item_texts)
                for variant in _shown_variants(text)
            )
            assert reached != (text in body_text_lines(document.instructions)), (exam, anchors)
