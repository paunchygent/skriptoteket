"""Decisions first pass and content tags through the provider door.

Proves the adapter sends unchanged Decisions bodies as DECISIONS with the
action's caller, maps door and HTTP failures to typed labeler errors, retries
only 503/504, and never retries a door limit or the overage cap.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import ExamContentItem
from skriptoteket.domain.llm_door import AiDailyLimit, AiDailyLimitReached, AiJobOverageCapReached
from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    OpenAIDecisionsItemTypeLabeler,
    build_decisions_payload,
    split_items,
)
from skriptoteket.protocols.item_type_labeler import (
    ContentTagClassificationRequest,
    ItemTypeLabelerError,
    LabelingItem,
    LabelingRequest,
)
from skriptoteket.protocols.llm_door import DoorOperation, DoorReply
from tests.unit.infrastructure.llm.decisions_item_labeler_support import (
    CORPUS_24,
    RecordingSleeper,
    load,
    recorded_door_reply,
    request_for,
)
from tests.unit.llm_door_fakes import (
    DoorSent,
    RecordingDoor,
    fixture_caller,
    json_reply,
    limit_refusal,
)

pytestmark = pytest.mark.unit

_CONTENT = (ExamContentItem(id="course:a", text="Språkets uppbyggnad"),)


def _labeler(door: RecordingDoor, *, max_attempts: int = 3) -> OpenAIDecisionsItemTypeLabeler:
    return OpenAIDecisionsItemTypeLabeler(
        door=door, timeout_seconds=30, sleeper=RecordingSleeper(), max_attempts=max_attempts
    )


def _recorded_reply() -> DoorReply:
    """The corpus's first recorded Decisions exchange, replayed at the door."""

    return recorded_door_reply(load(CORPUS_24)["exchanges"][0])


async def test_label_sends_decisions_with_the_caller_and_the_unchanged_payload() -> None:
    fixture = load(CORPUS_24)
    request = request_for(fixture)
    seen: list[DoorSent] = []

    def respond(sent: DoorSent) -> DoorReply:
        seen.append(sent)
        return _recorded_reply()

    labeling = await _labeler(RecordingDoor(respond)).label(request=request)

    assert len(labeling.results) == len(fixture["items"])
    assert len(seen) == 1
    sent = seen[0]
    assert sent.operation is DoorOperation.DECISIONS
    assert sent.caller is request.caller
    assert sent.timeout_seconds == 30
    (chunk,) = split_items(request.items)
    assert sent.payload == build_decisions_payload(chunk)


async def test_content_request_carries_the_caller_at_the_door() -> None:
    request = ContentTagClassificationRequest(
        job_id=uuid4(),
        items=(LabelingItem(item_id="q1", source_text="Analysera meningen."),),
        content_items=_CONTENT,
        caller=fixture_caller(),
    )
    seen: list[DoorSent] = []

    def respond(sent: DoorSent) -> DoorReply:
        seen.append(sent)
        return json_reply(
            {
                "answers": [
                    {
                        "type": "choice",
                        "name": "content_q1",
                        "choice": "c0",
                        "probabilities": [
                            {"value": "c0", "probability": 0.9},
                            {"value": "none", "probability": 0.1},
                        ],
                    }
                ],
                "usage": {"input_tokens": 11},
            }
        )

    result = await _labeler(RecordingDoor(respond)).classify_content(request=request)

    assert [choice.item_id for choice in result.results] == ["q1"]
    assert len(seen) == 1
    assert seen[0].operation is DoorOperation.DECISIONS
    assert seen[0].caller is request.caller


async def test_recorded_503_is_retried_once_at_the_door() -> None:
    fixture = load(CORPUS_24)
    door = RecordingDoor(
        lambda sent: (
            _recorded_reply()
            if len(door.sent) > 1
            else DoorReply(status_code=503, headers={}, body=b"{}")
        )
    )
    labeler = OpenAIDecisionsItemTypeLabeler(
        door=door, timeout_seconds=30, sleeper=RecordingSleeper(), max_attempts=3
    )

    labeling = await labeler.label(request=request_for(fixture))

    assert len(labeling.results) == len(fixture["items"])
    assert len(door.sent) == 2
    assert all(sent.operation is DoorOperation.DECISIONS for sent in door.sent)


async def test_limit_refusal_is_never_retried() -> None:
    door = RecordingDoor(limit_refusal(AiDailyLimit.POOL))

    with pytest.raises(AiDailyLimitReached):
        await _labeler(door).label(request=request_for(load(CORPUS_24)))

    assert len(door.sent) == 1


async def test_overage_cap_is_never_retried() -> None:
    door = RecordingDoor(lambda sent: _recorded_reply(), cap_usd_micros=0)
    caller = fixture_caller()
    caller.charge_overage(1)
    request = LabelingRequest(
        job_id=uuid4(),
        items=request_for(load(CORPUS_24)).items[:1],
        caller=caller,
    )

    with pytest.raises(AiJobOverageCapReached):
        await _labeler(door).label(request=request)

    assert door.sent == []


async def test_door_timeout_and_request_failure_map_to_typed_errors() -> None:
    from skriptoteket.protocols.llm_door import DoorRequestFailed, DoorTimeout

    async def timeout(_sent: DoorSent) -> DoorReply:
        raise DoorTimeout("slow")

    async def failed(_sent: DoorSent) -> DoorReply:
        raise DoorRequestFailed("down")

    with pytest.raises(ItemTypeLabelerError) as timed_out:
        await _labeler(RecordingDoor(timeout)).label(request=request_for(load(CORPUS_24)))
    assert timed_out.value.code == "timeout"

    with pytest.raises(ItemTypeLabelerError) as request_failed:
        await _labeler(RecordingDoor(failed)).label(request=request_for(load(CORPUS_24)))
    assert request_failed.value.code == "request_failed"


async def test_non_200_and_invalid_json_map_to_typed_errors() -> None:
    bad_status = RecordingDoor(lambda _sent: DoorReply(status_code=400, headers={}, body=b"{}"))
    with pytest.raises(ItemTypeLabelerError) as http_error:
        await _labeler(bad_status).label(request=request_for(load(CORPUS_24)))
    assert http_error.value.code == "http_error"
    assert http_error.value.status_code == 400

    bad_json = RecordingDoor(lambda _sent: DoorReply(status_code=200, headers={}, body=b"not json"))
    with pytest.raises(ItemTypeLabelerError) as invalid_json:
        await _labeler(bad_json).label(request=request_for(load(CORPUS_24)))
    assert invalid_json.value.code == "invalid_json"


async def test_persistent_503_raises_provider_unavailable() -> None:
    door = RecordingDoor(
        lambda _sent: DoorReply(status_code=503, headers={}, body=json.dumps({}).encode())
    )

    with pytest.raises(ItemTypeLabelerError) as exhausted:
        await _labeler(door).label(request=request_for(load(CORPUS_24)))

    assert exhausted.value.code == "provider_unavailable"
    assert len(door.sent) == 3
