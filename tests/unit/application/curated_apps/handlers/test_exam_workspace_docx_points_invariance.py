"""Invariance: where the grouping places a points line never changes the published points.

Every printed points line in each recorded conversion is moved to every placement the
grouping can give it. Each question's published points and estimate mark, the parts'
totals and the exam total must equal the recorded conversion's every time (TASK-SKRIPT-39-04-11).
A changed batch claim would raise ``MissingRecording``: that fails the test like any other
difference.
"""

import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import line_points
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    RECORDINGS,
    build_replay,
    corpus_chunks,
    recorded_exams,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

Grouping = dict
Place = Callable[[Grouping, str, str | None, str | None], bool]


def _context(scope: str, owner: str | None) -> Place:
    def place(grouping: Grouping, line: str, before: str | None, after: str | None) -> bool:
        question = owner and (before if owner == "before" else after)
        if owner is not None and question is None:
            return False
        grouping["shared_contexts"].append(
            {
                "anchor": line,
                "scope": scope,
                "owner": question or "exam",
                "governs": [question] if question else [],
            }
        )
        return True

    return place


def _header(kind: str) -> Place:
    def place(grouping: Grouping, line: str, before: str | None, after: str | None) -> bool:
        governs = [q for q in (before, after) if q] if kind != "course" else []
        grouping["header_anchors"].append({"anchor": line, "kind": kind, "governs": governs})
        return True

    return place


def _question(field: str, side: str) -> Place:
    def place(grouping: Grouping, line: str, before: str | None, after: str | None) -> bool:
        target = before if side == "before" else after
        if target is None:
            return False
        question = next(q for q in grouping["questions"] if q["id"] == target)
        question[field] = [*question[field], line]
        return True

    return place


def _title(grouping: Grouping, line: str, before: str | None, after: str | None) -> bool:
    grouping["title_anchors"].append(line)
    return True


def _unplaced(grouping: Grouping, line: str, before: str | None, after: str | None) -> bool:
    return True


_PLACEMENTS: dict[str, Place] = {
    "unplaced": _unplaced,
    "title": _title,
    "exam_metadata": _context("exam_metadata", None),
    "context_of_previous_question": _context("other", "before"),
    "instruction_of_next_question": _context("section_instruction", "after"),
    "course_header": _header("course"),
    "part_total_header": _header("part_total"),
    "question_total_header": _header("question_total"),
    "anchor_of_previous_question": _question("anchors", "before"),
    "anchor_of_next_question": _question("anchors", "after"),
    "subpart_of_previous_question": _question("subpart_anchors", "before"),
    "answer_key_of_previous_question": _question("answer_key_anchors", "before"),
}


def _grouping(exam: str) -> Grouping:
    grouping: Grouping = json.loads((RECORDINGS / exam / "docx_grouping_1.json").read_text())
    return grouping


def _strip(grouping: Grouping, line: str) -> None:
    grouping["title_anchors"] = [a for a in grouping["title_anchors"] if a != line]
    grouping["shared_contexts"] = [c for c in grouping["shared_contexts"] if c["anchor"] != line]
    grouping["header_anchors"] = [h for h in grouping["header_anchors"] if h["anchor"] != line]
    for question in grouping["questions"]:
        for field in ("anchors", "subpart_anchors", "answer_key_anchors"):
            question[field] = [a for a in question[field] if a != line]


def _neighbours(exam: str, grouping: Grouping, line: str) -> tuple[str | None, str | None]:
    """The questions whose first own chunk comes last before and first after the line."""
    order = {chunk.anchor: index for index, chunk in enumerate(corpus_chunks(exam))}
    starts = sorted(
        (min(order[a] for a in q["anchors"]), q["id"])
        for q in grouping["questions"]
        if q["anchors"]
    )
    before = [qid for start, qid in starts if start < order[line]]
    after = [qid for start, qid in starts if start > order[line]]
    return (before[-1] if before else None), (after[0] if after else None)


def _cases() -> list[tuple[str, str, str]]:
    return [
        (exam, chunk.anchor, placement)
        for exam in recorded_exams()
        for chunk in corpus_chunks(exam)
        if line_points(chunk) is not None
        for placement in _PLACEMENTS
    ]


async def _published(exam: str, root: Path) -> tuple:
    replay = build_replay(exam, root=root)
    document = (await replay.pipeline.convert(job=replay.job())).result.document
    return (
        tuple(
            (item.source_anchor, item.kind, item.points, item.points_estimated, item.tick_points)
            for item in sorted(document.items, key=lambda item: item.sequence)
        ),
        tuple(parent.printed_total for parent in document.parents),
        document.header.printed_total,
    )


_BASELINES: dict[str, tuple] = {}


@pytest.mark.parametrize(("exam", "line", "placement"), _cases())
async def test_a_points_lines_placement_never_changes_the_published_points(
    tmp_path: Path, exam: str, line: str, placement: str
):
    if exam not in _BASELINES:
        _BASELINES[exam] = await _published(exam, RECORDINGS)
    grouping = _grouping(exam)
    _strip(grouping, line)
    before, after = _neighbours(exam, grouping, line)
    if not _PLACEMENTS[placement](grouping, line, before, after):
        pytest.skip(f"{line} has no question on that side")
    shutil.copytree(RECORDINGS / exam, tmp_path / exam)
    (tmp_path / exam / "docx_grouping_1.json").write_text(json.dumps(grouping))

    assert await _published(exam, tmp_path) == _BASELINES[exam]
