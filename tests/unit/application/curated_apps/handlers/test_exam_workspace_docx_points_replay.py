"""Printed points lines reach their questions however the grouping tags them.

The recorded Svenska 2 conversion is replayed with four grouping variants of its header
anchors; every variant must produce the same printed points and no points-line item.
"""

import json
import re
import shutil
from pathlib import Path

import pytest

from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    RECORDINGS,
    build_replay,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_POINTS_LINES = {
    "body:0064": "q16",
    "body:0070": "q17",
    "body:0076": "q18",
    "body:0082": "q19",
    "body:0087": "q20",
    "body:0096": "q21",
    "body:0102": "q22",
    "body:0108": "q23",
    "body:0114": "q24",
}
_PRINTED_POINTS = [3, 3, 4, 4, 2, 1, 2, 1, 1]
_ONLY_POINTS_LINE = re.compile(r"^\s*Poäng:\s*\d+(?:[.,]\d+)?\s*poäng\.?\s*$", re.IGNORECASE)


def _part_total(ids: list[str]) -> list[dict]:
    return [{"anchor": "body:0006", "kind": "part_total", "governs": ids[:15]}]


def _question_totals(ids: list[str]) -> list[dict]:
    return [
        {"anchor": anchor, "kind": "question_total", "governs": [question]}
        for anchor, question in _POINTS_LINES.items()
    ]


_CASES = {
    "A_none": lambda ids: [],
    "B_part_total": _part_total,
    "D_question_totals": _question_totals,
    "E_both": lambda ids: _part_total(ids) + _question_totals(ids),
}


async def _replay(tmp_path: Path, tag, answer_key_edit=None):
    shutil.copytree(RECORDINGS / _EXAM, tmp_path / _EXAM)
    path = tmp_path / _EXAM / "docx_grouping_1.json"
    grouping = json.loads(path.read_text())
    ids = [question["id"] for question in grouping["questions"]]
    grouping["header_anchors"] = tag(ids)
    if answer_key_edit is not None:
        answer_key_edit(grouping)
    path.write_text(json.dumps(grouping))
    replay = build_replay(_EXAM, root=tmp_path)
    return await replay.pipeline.convert(job=replay.job())


def _assert_printed_points(outcome) -> None:
    result = outcome.result
    document = result.document
    items = sorted(document.items, key=lambda item: item.sequence)
    assert len(items) == 24
    assert sum(item.points for item in items) == 36
    assert document.header.printed_total == 36
    for item in items[:15]:
        assert item.points == 1
        assert item.points_estimated is True
    assert [item.points for item in items[15:]] == _PRINTED_POINTS
    assert not any(item.points_estimated for item in items[15:20])
    for item in items:
        assert not any(_ONLY_POINTS_LINE.match(line) for line in item.plain_text_lines()), (
            item.item_id
        )
    assert [parent.printed_total for parent in document.parents] == [15, 16, 5]
    forbidden = {*_POINTS_LINES, "body:0055"}
    flagged = {
        anchor
        for event in result.events
        if event.code in {"review_item", "own_chunks_left_out", "chunk_unclaimed"}
        for anchor in event.anchors
    }
    assert not flagged & forbidden


@pytest.mark.parametrize("case", list(_CASES))
async def test_points_reach_their_questions_whatever_the_grouping_tags(tmp_path: Path, case: str):
    _assert_printed_points(await _replay(tmp_path, _CASES[case]))


async def test_a_points_line_tagged_as_a_facit_still_reaches_its_question(tmp_path: Path):
    def tag_facit(grouping: dict) -> None:
        question = next(q for q in grouping["questions"] if q["id"] == "q23")
        question["answer_key_anchors"] = [*question["answer_key_anchors"], "body:0108"]

    outcome = await _replay(tmp_path, _CASES["A_none"], tag_facit)
    items = sorted(outcome.result.document.items, key=lambda item: item.sequence)
    assert items[22].points == 1
    assert "Poäng" not in (items[22].facit_text or "")
    assert len(items) == 24
    assert sum(item.points for item in items) == 36
