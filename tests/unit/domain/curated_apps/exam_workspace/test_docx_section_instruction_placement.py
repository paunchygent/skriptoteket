"""Where a section instruction lands in an item, on real live-run recordings.

Each build replays recorded model responses through the admission path and assembles the result
exactly as a job does. Items and instructions are selected by source anchor.
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
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildResult
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItem,
    NativeExamParent,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)

_FIXTURES = Path("tests/fixtures/exam_conversion")
_GRAMMAR_1 = "svenska_2_grammatik_omprov_variant_1_med_facit"
_GRAMMAR_2 = "svenska_2_grammatik_omprov_variant_2_med_facit"
_POETRY = "chapter_4_poetry_and_lyrics_quiz_med_facit"


@dataclass(frozen=True)
class _Build:
    state: DocxBuildState
    result: DocxBuildResult

    def item(self, anchor: str) -> NativeExamItem:
        return next(item for item in self.result.document.items if item.source_anchor == anchor)

    def parent_of(self, anchor: str) -> NativeExamParent | None:
        return self.result.document.parent_of(self.item(anchor).item_id)

    def wording(self, anchor: str) -> str:
        return self.state.chunk_by_anchor[anchor].text


def _build(stem: str) -> _Build:
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
    for recording in sorted((_FIXTURES / f"docx_build_round3_live1/{stem}").glob("round*.json")):
        admit_batch(json.loads(recording.read_text()), state)
    return _Build(state, state.result())


def test_instruction_printed_inside_the_item_opens_the_body_when_the_item_prints_nothing_before():
    build = _build(_GRAMMAR_1)
    item = build.item("body:0016")
    wording = build.wording("body:0017")

    lines = item.plain_text_lines()
    # The item's own printed heading opens the body (T1, 39-05-08); the instruction
    # printed inside the item follows it, ahead of the question's parts.
    assert lines[0] == "Ange frastyp."
    assert lines[1] == wording
    assert lines.count(wording) == 1
    assert lines[2].startswith("a) De trötta eleverna")
    assert len(lines) == 6


def test_short_label_survives_when_a_later_sentence_contains_it():
    for stem in (_GRAMMAR_1, _GRAMMAR_2):
        build = _build(stem)
        item = build.item("body:0085")
        lines = item.plain_text_lines()

        assert any("Text A och Text B" in line for line in lines)
        assert lines.count("Text A") == 1
        assert lines.count("Text B") == 1
        first_passage = next(k for k, line in enumerate(lines) if line.startswith("Igår när"))
        second_passage = next(
            k for k, line in enumerate(lines) if line.startswith("En vattenläcka")
        )
        assert lines.index("Text A") == first_passage - 1
        assert lines.index("Text B") == second_passage - 1
        # The printed section heading over this one question opens its body (T1, 39-05-08).
        assert lines[0] == "Del 4: Textanalys"
        assert lines[1] == build.wording("body:0075")


def test_instruction_over_a_run_of_reached_items_is_the_parent_of_exactly_those_items():
    build = _build(_POETRY)
    wording = build.wording("body:0018")
    assert wording == "Read the sentence:"

    parent = build.parent_of("body:0019")
    assert parent is not None
    assert parent.instruction == (wording,)
    assert parent == build.parent_of("body:0022")
    assert parent.item_ids == (build.item("body:0019").item_id, build.item("body:0022").item_id)
    for anchor in ("body:0019", "body:0022"):
        assert wording not in build.item(anchor).plain_text_lines()
    # The question after the run opens without a quote, so the instruction does not reach it.
    assert build.parent_of("body:0025") is None
    assert wording not in build.item("body:0025").plain_text_lines()


def test_mixed_kind_run_is_one_parent_and_no_child_repeats_the_instruction():
    build = _build(_GRAMMAR_1)
    wording = build.wording("body:0035")
    first, second = build.item("body:0037"), build.item("body:0045")

    assert first.kind != second.kind
    parent = build.parent_of("body:0037")
    assert parent is not None and parent == build.parent_of("body:0045")
    # The section heading opens the parent's instruction (T2, 39-05-08).
    assert parent.instruction == ("Del 2: Satsdelar", wording)
    assert parent.item_ids == (first.item_id, second.item_id)
    for item in (first, second):
        assert wording not in item.plain_text_lines()


def test_instruction_reaching_a_single_item_is_still_copied_not_parented():
    build = _build(_GRAMMAR_1)
    wording = build.wording("body:0054")
    carriers = [
        item.source_anchor
        for item in build.result.document.items
        if wording in item.plain_text_lines()
    ]

    assert carriers == ["body:0056"]
    # The section heading over the two questions forms their parent (T2, 39-05-08);
    # the instruction reaching one item stays a copy in that item, not a parent line.
    parent = build.parent_of("body:0056")
    assert parent is not None and parent == build.parent_of("body:0066")
    assert parent.instruction == ("Del 3: Bisatser och komplex meningsbyggnad",)
    assert build.item("body:0056").plain_text_lines()[0] == wording
