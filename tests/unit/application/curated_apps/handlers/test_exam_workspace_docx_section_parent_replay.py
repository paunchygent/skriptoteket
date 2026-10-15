"""The grouping's governing chunk is the section parent's instruction (T2, D27, D36, D40).

The fresh course-exam recording has the grouping mark body:0009 ("Skriv rätt bokstav.") as
governing the fifteen questions of section one, and the reply lists it as an instruction.
The printed section heading body:0008 opens the section. Both lines stand once, on the
parent; the first governed question prints neither, and no event reports a section that
differs from the grouping.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    build_replay,
    corpus_chunks,
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_HEADING = "body:0008"
_INSTRUCTION = "body:0009"


def _lines(value: object) -> list[str]:
    assert isinstance(value, list)
    return [str(entry) for entry in value]


async def test_a_governing_instruction_is_the_parent_of_every_question_it_governs():
    contexts = recording(_EXAM, "docx_grouping_1")["shared_contexts"]
    assert isinstance(contexts, list)
    context = next(c for c in contexts if isinstance(c, dict) and c["anchor"] == _INSTRUCTION)
    governed = _lines(context["governs"])
    assert len(governed) == 15
    text = {chunk.anchor: chunk.text for chunk in corpus_chunks(_EXAM)}

    replay = build_replay(_EXAM)
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.result.document
    governed_items = [item_id for qid in governed for item_id in outcome.update.item_ids[qid]]
    parent = document.parent_of(governed_items[0])
    assert parent is not None, "the first governed question has no section parent"
    # The section title above the subsection heading opens its own parent (TASK-SKRIPT-39-09-09).
    assert body_text_lines(parent.instruction) == (
        "Del 1: litteraturhistoria",
        "Flervalsfrågor",
        text[_INSTRUCTION],
    )
    assert list(parent.item_ids) == governed_items
    for item in document.items:
        assert text[_INSTRUCTION] not in item.plain_text_lines()
    assert text[_INSTRUCTION] not in body_text_lines(document.instructions)
    assert not any(line.startswith("Del 1") for line in body_text_lines(document.instructions))
    assert [e for e in outcome.result.events if e.code == "parent_differs_from_grouping"] == []
