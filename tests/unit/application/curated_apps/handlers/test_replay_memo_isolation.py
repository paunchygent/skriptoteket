"""Memoised replay results are handed to each caller as an independent copy.

The sweeps compute a conversion's expensive result once per process. A test that mutates what it
received (a corruption stage, an added reason) must not change what the next test receives.
"""

from __future__ import annotations

import pytest

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_markdown import (  # noqa: E501
    PythonDocxLabelerMarkdown,
)
from tests.fixtures.docx_corpus import corpus_docx
from tests.unit.application.curated_apps.handlers.labeler_source_memo import _memoised_source
from tests.unit.application.curated_apps.handlers.test_docx_pipeline_replay_label_b_keys import (
    _EXAM,
    _label_requests,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_docx_type_conflict import (
    _convert,
)

pytestmark = pytest.mark.unit


def _labeler_source():
    return _memoised_source(PythonDocxLabelerMarkdown(), content=corpus_docx(_EXAM))


def test_labeler_source_maps_are_independent_between_calls():
    first = _labeler_source()
    first.unavailable["probe"] = "contamination"
    first.images["probe"] = b"contamination"

    second = _labeler_source()

    assert "probe" not in second.unavailable
    assert "probe" not in second.images
    assert second.unavailable is not first.unavailable
    assert second.images is not first.images


@pytest.mark.asyncio
async def test_type_conflict_request_ids_are_independent_between_calls():
    request_ids, _ = await _convert()
    request_ids.append("probe")

    second_ids, _ = await _convert()

    assert "probe" not in second_ids


@pytest.mark.asyncio
async def test_type_conflict_outcome_is_independent_between_calls():
    _, first = await _convert()
    first.update.item_ids["probe"] = "contamination"

    _, second = await _convert()

    assert second is not first
    assert "probe" not in second.update.item_ids


@pytest.mark.asyncio
async def test_label_requests_do_not_share_nested_schemas_between_calls():
    _, first = await _label_requests(_EXAM)
    first[0].output_spec.json_schema["probe"] = True

    _, second = await _label_requests(_EXAM)

    assert "probe" not in second[0].output_spec.json_schema
