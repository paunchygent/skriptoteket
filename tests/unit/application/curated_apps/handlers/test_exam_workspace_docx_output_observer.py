"""Synthetic fragments prove framing and receipt semantics, not live import visibility."""

import json

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_output_observer import (
    CompletedItemsReader,
    DocxOutputObserver,
    DocxReceiptWriteError,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import QuestionFamily


def families() -> dict[str, QuestionFamily]:
    return {
        "q1": QuestionFamily("q1", 0, ("a1", "a1b"), frozenset({"a1", "a1b", "key"}), frozenset()),
        "q2": QuestionFamily("q2", 1, ("a2",), frozenset({"a2", "title"}), frozenset()),
    }


@pytest.mark.parametrize("chunk_size", [1, 2, 7, 65536])
def test_nested_escaped_and_fragmented_json_only_yields_top_level_items(chunk_size: int):
    items = [
        {"source_anchors": ["a1"], "body": [{"text": 'quoted \\" } ], { \\ \n å'}]},
        {"source_anchors": ["a2"], "nested": {"items": [{"text": "not a third item"}]}},
    ]
    text = json.dumps(
        {"metadata": {"items": [{"source_anchors": ["not-an-item"]}]}, "items": items},
        ensure_ascii=True,
    )
    reader = CompletedItemsReader()
    observed = []
    for start in range(0, len(text), chunk_size):
        observed.extend(reader.feed(text[start : start + chunk_size]))
    assert observed == items
    assert reader.feed("") == []


def test_complete_item_is_observed_before_array_or_envelope_closure_and_tail_waits():
    reader = CompletedItemsReader()
    assert reader.feed('{"items":[{"source_anchors":["a1"]}') == [{"source_anchors": ["a1"]}]
    assert reader.feed(',{"source_anchors":["a') == []
    assert reader.feed('2"]}') == [{"source_anchors": ["a2"]}]
    assert reader.feed('],"instructions":[]}') == []


@pytest.mark.parametrize("version", [12345, -1.25e30, 1e-15])
def test_every_possible_two_fragment_split_preserves_items(version: int | float):
    item = {"source_anchors": ["a1"], "body": [{"text": 'escaped \\" [ ] { }'}]}
    text = json.dumps({"version": version, "items": [item]})
    for split in range(len(text) + 1):
        reader = CompletedItemsReader()
        assert reader.feed(text[:split]) + reader.feed(text[split:]) == [item]


@pytest.mark.asyncio
async def test_review_conflict_repeats_and_multi_question_items_are_receipts_not_admission():
    received: list[tuple[str, ...]] = []

    async def record(question_ids: tuple[str, ...]) -> None:
        received.append(question_ids)

    observer = DocxOutputObserver(families(), record)
    await observer.on_text('{"title":{"source_anchors":["a1"]},"items":[')
    assert received == [], "metadata never establishes an item receipt"
    await observer.on_text('{"outcome":"review","source_anchors":["a1b"]}')
    await observer.on_text(',{"outcome":"type_conflict","source_anchors":["a2"]}')
    await observer.on_text(',{"source_anchors":["a1","a1b"]}')
    await observer.on_text(',{"source_anchors":["a2","a1"]}')
    await observer.on_text(',{"source_anchors":["title","key"]}]')
    assert received == [("q1",), ("q2",), ("q1",), ("q1", "q2")]
    assert set().union(*map(set, received)) == {"q1", "q2"}


@pytest.mark.asyncio
async def test_unfinished_or_unreadable_tail_does_not_reject_prior_output():
    received: list[tuple[str, ...]] = []

    async def record(question_ids: tuple[str, ...]) -> None:
        received.append(question_ids)

    observer = DocxOutputObserver(families(), record)
    await observer.on_text('{"items":[{"source_anchors":["a1"]},')
    await observer.on_text('{"source_anchors":["a2"],"unfinished":')
    await observer.on_text("not JSON")
    assert received == [("q1",)]


@pytest.mark.asyncio
async def test_progress_io_failure_is_not_swallowed_as_an_observation_problem():
    error = OSError("progress store unavailable")

    async def broken(question_ids: tuple[str, ...]) -> None:
        raise error

    observer = DocxOutputObserver(families(), broken)
    with pytest.raises(DocxReceiptWriteError) as caught:
        await observer.on_text('{"items":[{"source_anchors":["a1"]}')
    assert caught.value.error is error
