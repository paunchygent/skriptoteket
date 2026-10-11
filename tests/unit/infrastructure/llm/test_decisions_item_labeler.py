from __future__ import annotations

from uuid import uuid4

import pytest

from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    build_decisions_payload,
    split_items,
)
from skriptoteket.protocols.item_type_labeler import LabelingRequest
from tests.unit.infrastructure.llm.decisions_item_labeler_support import (
    CORPUS_24,
    CORPUS_204,
    SECOND_PASS_INPUT_TOKENS,
    Harness,
    escalated_answers,
    load,
    replay,
    request_for,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("name", [CORPUS_24, CORPUS_204])
def test_request_input_carries_each_source_text_verbatim_and_nothing_else(name: str) -> None:
    fixture = load(name)
    items = request_for(fixture).items
    inputs = [build_decisions_payload(chunk)["input"] for chunk in split_items(items)]
    assert all(isinstance(rendered, str) for rendered in inputs)
    offset = 0
    for rendered, chunk in zip(inputs, split_items(items), strict=True):
        assert isinstance(rendered, str)
        for forbidden in (
            "Answer key",
            "[Governing instruction",
            "Section heading:",
            "Question as the student sees it:",
        ):
            assert forbidden not in rendered.split("\n\n### Question ", 1)[1]
        for index, item in enumerate(chunk):
            block = rendered.split(f"### Question q{index + 1}\n", 1)[1]
            followed = f"\n\n### Question q{index + 2}\n"
            assert block.split(followed, 1)[0] == item.source_text
        offset += len(chunk)
    assert offset == len(items)


async def test_204_items_split_into_two_recorded_requests_in_item_order() -> None:
    fixture = load(CORPUS_204)
    harness = Harness(replay(fixture["exchanges"], fixture=fixture))
    escalated = len(escalated_answers(fixture))
    assert escalated > 0

    labeling = await harness.labeler().label(request=request_for(fixture))

    batched = [sent for sent in harness.requests if len(sent["questions"]) > 1]
    single = [sent for sent in harness.requests if len(sent["questions"]) == 1]
    assert sorted(len(sent["questions"]) for sent in batched) == [4, 200]
    assert len(single) == escalated
    for sent in batched:
        assert "### Question q1" in sent["input"]
    small = next(sent for sent in batched if len(sent["questions"]) == 4)
    assert "### Question q5" not in small["input"]
    assert [r.item_id for r in labeling.results] == [i["item_id"] for i in fixture["items"]]
    assert sum(r.first_pass is not None for r in labeling.results) == escalated
    recorded_tokens = sum(e["body"]["usage"]["input_tokens"] for e in fixture["exchanges"])
    assert labeling.usage.input_tokens == recorded_tokens + SECOND_PASS_INPUT_TOKENS * escalated
    assert labeling.usage.requests == 2 + escalated
    assert labeling.usage.attempts == 2 + escalated


async def test_empty_request_sends_nothing() -> None:
    harness = Harness(replay(load(CORPUS_24)["exchanges"]))

    labeling = await harness.labeler().label(request=LabelingRequest(job_id=uuid4(), items=()))

    assert labeling.results == ()
    assert harness.requests == []
