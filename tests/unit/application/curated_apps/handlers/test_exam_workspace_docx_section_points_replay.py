"""Replay of a one-family live run in which a section's points line misled the last question (D38).

``docx_build_v11_one_family_points`` holds the recordings of the course exam whose first
section prints "15 poäng" on its heading and again on a points line after its fifteenth
question. The fifteenth question's batch owned that line, gave the question the whole
total as its own points and left the line unclaimed.
"""

import pytest

from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    FIXTURES,
    build_replay,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_ROOT = FIXTURES / "docx_build_v11_one_family_points"
_COURSE_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_FIRST_SECTION = tuple(f"body:{start:04d}" for start in (8, *range(13, 53, 3)))
_POINTS_LINE = "body:0055"


async def test_section_total_is_split_over_its_questions_and_its_points_line_is_no_item():
    replay = build_replay(_COURSE_EXAM, root=_ROOT, families_per_batch=1)
    outcome = await replay.pipeline.convert(job=replay.job())

    items = {item.source_anchor: item for item in outcome.result.document.items}
    section = [items[anchor] for anchor in _FIRST_SECTION]
    assert [item.points for item in section] == [1] * 15
    assert all(item.points_estimated for item in section)
    assert not any(item.review.reasons for item in section)
    assert _POINTS_LINE not in items
