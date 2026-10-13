"""The section parent follows the grouping's governs list (step 3, D27, D36).

``docx_build_v13_low15_section_parent`` holds the live recordings of a one-family-per-batch
run in which the grouping makes one instruction the shared context of the first fifteen
questions, and the converter puts the section heading before that instruction into the first
question's item while keeping the instruction itself as an instruction. The instruction stays
the parent of exactly the fifteen governed questions and is printed once, on the parent.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeTextSegment,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    FIXTURES,
    build_replay,
    corpus_chunks,
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_ROOT = FIXTURES / "docx_build_v13_low15_section_parent"
_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_INSTRUCTION = "body:0009"


async def test_a_governing_instruction_is_the_parent_of_every_question_it_governs():
    grouping = recording(_EXAM, "docx_grouping_1", root=_ROOT)
    contexts = grouping["shared_contexts"]
    assert isinstance(contexts, list)
    context = next(c for c in contexts if isinstance(c, dict) and c["anchor"] == _INSTRUCTION)
    governed = context["governs"]
    assert isinstance(governed, list) and len(governed) == 15
    text = {chunk.anchor: chunk.text for chunk in corpus_chunks(_EXAM)}

    replay = build_replay(_EXAM, root=_ROOT, families_per_batch=1)
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.result.document
    update = outcome.update
    governed_items = [item_id for qid in governed for item_id in update.item_ids[str(qid)]]
    parent = document.parent_of(governed_items[0])
    assert parent is not None, "the first governed question has no section parent"
    assert parent.instruction == (text[_INSTRUCTION],)
    assert list(parent.item_ids) == governed_items
    first = next(item for item in document.items if item.item_id == governed_items[0])
    printed = [
        segment.text
        for paragraph in first.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]
    assert text[_INSTRUCTION] not in printed, "the first question prints the parent's instruction"
    assert text[_INSTRUCTION] not in document.instructions
    assert [e for e in outcome.result.events if e.code == "parent_differs_from_grouping"] == []
