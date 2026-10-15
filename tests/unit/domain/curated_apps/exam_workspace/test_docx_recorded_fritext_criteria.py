"""R14 on the real v14 prose-guide recordings, rewritten to the current schema."""

import json
from pathlib import Path

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    recorded_exam_language,
)

_RECORDINGS = Path("tests/fixtures/exam_conversion/docx_key_provenance_v14")


def test_recorded_prose_guides_become_estimated_native_criteria() -> None:
    observed = []
    for path in sorted(_RECORDINGS.rglob("docx_w*.json")):
        recording = json.loads(path.read_text())
        for raw in recording["items"]:
            if not raw["criteria"]:
                continue
            produced = ProducedItem.model_validate(raw)
            assert len(produced.criteria) == 1, path
            (criterion,) = produced.criteria
            # These recordings contain prose guides, not per-criterion point breakdowns.
            assert criterion.points is None, path
            native = native_item(produced, language=recorded_exam_language(path.parent.name))
            assert len(native.criteria) == 1, path
            assert native.criteria[0].text == criterion.text, path
            assert native.criteria[0].points == (produced.points or 1), path
            assert native.points == native.criteria[0].points, path
            assert native.points_estimated is True, path
            observed.append((path, produced.source_anchors))
    assert len(observed) == 5
