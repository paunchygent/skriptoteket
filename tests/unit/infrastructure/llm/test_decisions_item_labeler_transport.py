from __future__ import annotations

import pytest

from skriptoteket.protocols.item_type_labeler import ItemTypeLabelerError
from skriptoteket.protocols.llm_door import DoorReply
from tests.unit.infrastructure.llm.decisions_item_labeler_support import (
    CORPUS_24,
    Harness,
    always,
    load,
    replay,
    request_for,
    sequence,
    unavailable,
)

pytestmark = pytest.mark.unit


async def test_recorded_503_then_success_retries_once_after_base_delay() -> None:
    fixture = load(CORPUS_24)
    harness = Harness(sequence(always(unavailable(503)), replay(fixture["exchanges"])))

    labeling = await harness.labeler().label(request=request_for(fixture))

    assert len(labeling.results) == len(fixture["items"])
    assert labeling.usage.requests == 1
    assert labeling.usage.attempts == 2
    assert harness.sleeper.delays == [1.0]


async def test_recorded_504_retry_after_is_capped() -> None:
    fixture = load(CORPUS_24)
    gateway_timeout = unavailable(504)
    assert gateway_timeout["headers"]["retry-after"] == "120"
    harness = Harness(sequence(always(gateway_timeout), replay(fixture["exchanges"])))

    labeling = await harness.labeler().label(request=request_for(fixture))

    assert len(labeling.results) == len(fixture["items"])
    assert harness.sleeper.delays == [8.0]


async def test_persistent_503_raises_provider_unavailable_after_three_attempts() -> None:
    harness = Harness(always(unavailable(503)))

    with pytest.raises(ItemTypeLabelerError) as caught:
        await harness.labeler().label(request=request_for(load(CORPUS_24)))

    assert caught.value.code == "provider_unavailable"
    assert caught.value.status_code == 503
    assert len(harness.requests) == 3
    assert harness.sleeper.delays == [1.0, 2.0]


async def test_persistent_504_honours_max_attempts() -> None:
    harness = Harness(always(unavailable(504)))

    with pytest.raises(ItemTypeLabelerError) as caught:
        await harness.labeler(max_attempts=2).label(request=request_for(load(CORPUS_24)))

    assert caught.value.code == "provider_unavailable"
    assert caught.value.status_code == 504
    assert len(harness.requests) == 2


async def test_non_retryable_status_fails_without_retry() -> None:
    harness = Harness(always(unavailable(503), status_code=400))

    with pytest.raises(ItemTypeLabelerError) as caught:
        await harness.labeler().label(request=request_for(load(CORPUS_24)))

    assert caught.value.code == "http_error"
    assert caught.value.status_code == 400
    assert len(harness.requests) == 1
    assert harness.sleeper.delays == []


async def test_non_json_success_body_raises_invalid_json() -> None:
    gateway_page = unavailable(504)["body"]
    assert isinstance(gateway_page, str)
    harness = Harness(
        lambda _sent: DoorReply(status_code=200, headers={}, body=gateway_page.encode("utf-8"))
    )

    with pytest.raises(ItemTypeLabelerError) as caught:
        await harness.labeler().label(request=request_for(load(CORPUS_24)))

    assert caught.value.code == "invalid_json"
