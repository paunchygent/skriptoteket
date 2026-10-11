"""Batch admission enforces source-structure rules on real recorded model output."""

import json
from pathlib import Path
from uuid import uuid4

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)

_FIXTURES = Path("tests/fixtures/exam_conversion")


def _admitted(recording: str, docx: str) -> DocxBuildState:
    chunks = PythonDocxExamChunker().chunk(
        content=(_FIXTURES / f"docx_corpus/{docx}.docx").read_bytes()
    )
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="test.docx",
        source_sha256="a" * 64,
        chunks=chunks,
    )
    admit_batch(json.loads((_FIXTURES / recording).read_text()), state)
    return state


def test_opening_heading_listed_as_facit_stays_pending_for_the_title():
    state = _admitted(
        "sa24_solid_gold_3_docx_build_response_round1.json",
        "sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit",
    )
    assert "body:0002" not in state.key_anchors
    assert "body:0002" not in state.claimed
    assert "body:0002" in {chunk.anchor for chunk in state.pending}
    assert len([f for f in state.failures if "opening heading" in f]) == 1
    assert any(event.code == "answer_key_source_rule" for event in state.events)


def test_items_breaking_unit_segmentation_rule_are_rejected_and_stay_pending():
    state = _admitted(
        "svenska_2_grammatik_variant_1_docx_build_response.json",
        "svenska_2_grammatik_omprov_variant_1_med_facit",
    )
    accepted_first_anchors = {anchors[0] for _, anchors in state.accepted}
    assert {"body:0008", "body:0045"}.isdisjoint(accepted_first_anchors)
    pending = {chunk.anchor for chunk in state.pending}
    assert {"body:0008", "body:0045"} <= pending
    source_rule_failures = [
        f for f in state.failures if f.startswith("items[") and "source_rule" in f
    ]
    assert len(source_rule_failures) == 2


def test_items_and_title_matching_source_structure_are_admitted():
    state = _admitted(
        "svenska_2_kursavslutande_prov_docx_build_response.json",
        "svenska_2_kursavslutande_prov_med_facit",
    )
    assert not any("source_rule" in event.code for event in state.events)
    assert state.title is not None
    assert state.title.source_anchors == ("body:0002", "body:0003")
