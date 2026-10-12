"""A governing chunk no reply claims becomes its section parent's instruction (D40).

``docx_build_v16_low17_unclaimed_governing`` holds live recordings of a one-family-per-batch
run, edited so that no reply lists body:0058, which the grouping marks as governing q25–q27
(see its README). The parent shows the chunk's source text as its instruction, and no review
item holds it.
"""

import pytest

from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    FIXTURES,
    SecondWaveByAnchor,
    build_replay,
    corpus_chunks,
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_ROOT = FIXTURES / "docx_build_v16_low17_unclaimed_governing"
_EXAM = "bf26_english_1_unit_test_kap_1_2_med_facit"
_UNCLAIMED, _LISTED = "body:0058", "body:0060"


def _listed_anywhere(anchor: str) -> bool:
    return any(f'"{anchor}"' in path.read_text() for path in (_ROOT / _EXAM).glob("docx_w*.json"))


async def test_an_unclaimed_governing_chunk_is_its_section_parent_s_instruction():
    contexts = recording(_EXAM, "docx_grouping_1", root=_ROOT)["shared_contexts"]
    assert isinstance(contexts, list)
    (context,) = [c for c in contexts if isinstance(c, dict) and c["anchor"] == _UNCLAIMED]
    governs = context["governs"]
    assert isinstance(governs, list) and len(governs) >= 2
    assert not _listed_anywhere(_UNCLAIMED)
    text = {chunk.anchor: chunk.text for chunk in corpus_chunks(_EXAM)}

    replay = build_replay(
        _EXAM, root=_ROOT, families_per_batch=1, provider=SecondWaveByAnchor(_EXAM, root=_ROOT)
    )
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.result.document
    governed = [item_id for qid in governs for item_id in outcome.update.item_ids[str(qid)]]
    parent = document.parent_of(governed[0])
    assert parent is not None
    assert parent.instruction == (text[_UNCLAIMED], text[_LISTED])
    assert list(parent.item_ids) == governed
    assert all(item.source_anchor != _UNCLAIMED for item in document.items)
    assert [e for e in outcome.result.events if e.code == "parent_differs_from_grouping"] == []
    recorded = [e.code for e in outcome.result.events if _UNCLAIMED in e.anchors]
    assert recorded == ["governing_instruction"], "the events name what happens to the chunk"
