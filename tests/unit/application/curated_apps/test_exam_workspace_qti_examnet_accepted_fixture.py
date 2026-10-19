"""The Exam.net-accepted QTI package imports back into the workspace.

The fixture is the exact package Exam.net accepted on import as exam 5345261
(Exam.net offers no exam-content export, so no round-trip export exists). The
test parses the real bytes through ``ParseExamWorkspaceQtiPackageHandler`` with
the real ``ExamNetQtiPackageReader`` on the guest path (``course_key=None``)
and compares every item against ``svenska2-rev11-expected.json``, which was
derived once from the v6 source document (see the fixture README).

The parent ruling of 2026-10-18 names the accepted losses; the two that occur
in this package each have their own test below. Every other difference fails.
The comparison maps imported items with ``body_plain_text`` — the shared
primitive the round-trip projection in ``qti_round_trip_support`` builds on —
instead of copying that projection, because the expected values live in a
static JSON file as plain text.
"""

import hashlib
from pathlib import Path
from typing import TypedDict
from uuid import uuid4

from pydantic import TypeAdapter

from skriptoteket.application.curated_apps.handlers.exam_workspace_qti_import import (
    ParseExamWorkspaceQtiPackageHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_package_reader import (  # noqa: E501
    ExamNetQtiPackageReader,
)
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    SequenceIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _settings,
)

_FIXTURE_DIR = Path("tests/fixtures/exam_conversion/examnet_accepted")
_PACKAGE = _FIXTURE_DIR / "svenska2-rev11-qti.zip"
_EXPECTED = _FIXTURE_DIR / "svenska2-rev11-expected.json"

# Sequences whose answer-key projection carries an accepted loss; asserted
# exactly in the named loss tests instead of the main comparison.
_GAP_MERGE_SEQUENCE = 20
_CRITERION_LOSS_SEQUENCES = (21, 22, 23, 24)


class _ExpectedCriterion(TypedDict):
    text: str
    points: int


class _ExpectedInline(TypedDict):
    options: list[str]
    correct_position: int | None


class _ExpectedItem(TypedDict):
    sequence: int
    kind: str
    points: int
    prompt: str
    choices: list[str]
    correct_positions: list[int]
    gaps_accepted: list[list[str]]
    gaps_automatic: list[list[str]]
    inline: list[_ExpectedInline]
    match_pairs: list[tuple[str, str]]
    print_order: list[int]
    criteria: list[_ExpectedCriterion]


class _ExpectedParent(TypedDict):
    child_positions: list[int]
    instruction: str


class _ExpectedFile(TypedDict):
    derived_from: str
    items: list[_ExpectedItem]
    parents: list[_ExpectedParent]


def _parse_fixture() -> tuple[bytes, ExamWorkspaceContainerContent, _ExpectedFile]:
    content = _PACKAGE.read_bytes()
    assert _PACKAGE.with_suffix(".zip.sha256").read_text().split()[0] == (
        hashlib.sha256(content).hexdigest()
    )
    handler = ParseExamWorkspaceQtiPackageHandler(
        reader=ExamNetQtiPackageReader(),
        settings=_settings(),
        id_generator=SequenceIdGenerator([uuid4() for _ in range(5)]),
    )
    container = handler.handle(filename=_PACKAGE.name, content=content, course_key=None)
    expected = TypeAdapter(_ExpectedFile).validate_json(_EXPECTED.read_bytes())
    return content, container, expected


def _correct_positions(item: NativeExamItem) -> tuple[int, ...]:
    choice_ids = [choice.choice_id for choice in item.choices]
    return tuple(choice_ids.index(choice_id) for choice_id in item.answer_key.correct_choice_ids)


def _inline_projection(item: NativeExamItem) -> tuple[tuple[tuple[str, ...], int | None], ...]:
    return tuple(
        (
            tuple(body_plain_text(option.body) for option in gap.options),
            (
                [option.choice_id for option in gap.options].index(gap.correct_option_id)
                if gap.correct_option_id is not None
                else None
            ),
        )
        for gap in item.gaps
    )


def test_examnet_accepted_fixture_imports_24_items_worth_36_points() -> None:
    content, container, expected = _parse_fixture()
    document = container.document

    assert [item.sequence for item in document.items] == list(range(1, 25))
    assert sum(item.points or 0 for item in document.items) == 36
    assert container.notes == ()
    assert document.instructions == ()
    assert document.origin.kind == "qti_import"
    assert document.origin.source_filename == _PACKAGE.name
    assert document.origin.source_sha256 == hashlib.sha256(content).hexdigest()

    assert len(document.parents) == 2
    for parent, expected_parent in zip(document.parents, expected["parents"], strict=True):
        positions = tuple(
            sorted(item.sequence for item in document.items if item.item_id in parent.item_ids)
        )
        assert positions == tuple(expected_parent["child_positions"])
        assert body_plain_text(parent.instruction) == expected_parent["instruction"]

    assert [expected_item["sequence"] for expected_item in expected["items"]] == list(range(1, 25))
    for item, expected_item in zip(document.items, expected["items"], strict=True):
        assert item.kind.value == expected_item["kind"]
        assert item.points == expected_item["points"]
        assert body_plain_text(item.body) == expected_item["prompt"]
        assert [body_plain_text(choice.body) for choice in item.choices] == expected_item["choices"]
        assert _correct_positions(item) == tuple(expected_item["correct_positions"])
        assert tuple(item.print_order) == tuple(expected_item["print_order"])
        assert [(pair.left_id, pair.right_id) for pair in item.answer_key.match_pairs] == [
            tuple(pair) for pair in expected_item["match_pairs"]
        ]
        assert _inline_projection(item) == tuple(
            (tuple(inline["options"]), inline["correct_position"])
            for inline in expected_item["inline"]
        )
        if item.sequence == _GAP_MERGE_SEQUENCE:
            continue
        assert [tuple(gap.accepted_values) for gap in item.gaps] == [
            tuple(values) for values in expected_item["gaps_accepted"]
        ]
        assert [tuple(gap.automatic_values) for gap in item.gaps] == [
            tuple(values) for values in expected_item["gaps_automatic"]
        ]
        if item.sequence in _CRITERION_LOSS_SEQUENCES:
            continue
        assert [(criterion.text, criterion.points) for criterion in item.criteria] == [
            (criterion["text"], criterion["points"]) for criterion in expected_item["criteria"]
        ]


def test_examnet_accepted_fixture_loses_free_text_criterion_text() -> None:
    _content, container, expected = _parse_fixture()

    for item, expected_item in zip(container.document.items, expected["items"], strict=True):
        if item.sequence not in _CRITERION_LOSS_SEQUENCES:
            continue
        assert expected_item["criteria"] != []
        assert item.criteria == ()
        assert item.points == expected_item["points"]


def test_examnet_accepted_fixture_merges_automatic_gap_values_into_accepted() -> None:
    _content, container, expected = _parse_fixture()

    item = next(item for item in container.document.items if item.sequence == _GAP_MERGE_SEQUENCE)
    expected_item = next(
        expected_item
        for expected_item in expected["items"]
        if expected_item["sequence"] == _GAP_MERGE_SEQUENCE
    )
    assert all(values for values in expected_item["gaps_automatic"])
    assert [tuple(gap.accepted_values) for gap in item.gaps] == [
        tuple([*accepted, *automatic])
        for accepted, automatic in zip(
            expected_item["gaps_accepted"], expected_item["gaps_automatic"], strict=True
        )
    ]
    assert [tuple(gap.automatic_values) for gap in item.gaps] == [
        () for _ in expected_item["gaps_automatic"]
    ]
