"""Daily token lease around the Decisions item-type labeler (TASK-SKRIPT-39-05-04).

The real adapter replays recorded Decisions exchanges; only the lease
repository, UoW and clock are stand-ins.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest

from skriptoteket.application.curated_apps.item_type_labeling import (
    LEASE_ITEM_ID,
    LeasedItemTypeLabeler,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLease,
    AnswerKeyTokenLeaseRefused,
    AnswerKeyTokenLeaseState,
)
from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    OpenAIDecisionsItemTypeLabeler,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import AnswerKeyTokenLeaseRepositoryProtocol
from skriptoteket.protocols.item_type_labeler import (
    ItemTypeLabelerError,
    LabelingItem,
    LabelingRequest,
    ThresholdPolicy,
)
from skriptoteket.protocols.sleeper import SleeperProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

pytestmark = pytest.mark.unit

_FIXTURES = Path("tests/fixtures/item_type_labeler")
_NOW = datetime(2026, 10, 11, 12, tzinfo=UTC)


def _fixture(name: str) -> dict[str, Any]:
    fixture: dict[str, Any] = json.loads((_FIXTURES / name).read_text())
    return fixture


class _Harness:
    def __init__(self, *responses: httpx.Response) -> None:
        self.events: list[str] = []
        self._responses = list(responses)
        self.leases = AsyncMock(spec=AnswerKeyTokenLeaseRepositoryProtocol)
        self.leases.reserve.side_effect = self._reserve
        self.uow = AsyncMock(spec=UnitOfWorkProtocol)
        clock = Mock(spec=ClockProtocol)
        clock.now.return_value = _NOW
        self.adapter = OpenAIDecisionsItemTypeLabeler(
            client=httpx.AsyncClient(transport=httpx.MockTransport(self._post)),
            base_url="https://example.test",
            api_key="fixture-key",
            timeout_seconds=30,
            sleeper=AsyncMock(spec=SleeperProtocol),
            policy=ThresholdPolicy(),
        )
        self.labeler = LeasedItemTypeLabeler(
            labeler=self.adapter, leases=self.leases, uow=self.uow, clock=clock
        )

    async def _reserve(self, **_: object) -> AnswerKeyTokenLease:
        self.events.append("reserve")
        return AnswerKeyTokenLease(
            lease_id=uuid4(),
            utc_day=_NOW.date(),
            reserved_tokens=1,
            state=AnswerKeyTokenLeaseState.RESERVED,
        )

    def _post(self, request: httpx.Request) -> httpx.Response:
        self.events.append("post")
        return self._responses.pop(0)


def _recorded_exam() -> tuple[LabelingRequest, dict[str, Any]]:
    fixture = _fixture("corpus_exam_24_questions.json")
    items = tuple(LabelingItem(**item) for item in fixture["items"])
    return LabelingRequest(job_id=uuid4(), items=items), fixture["exchanges"][0]


def _ok(exchange: dict[str, Any]) -> httpx.Response:
    return httpx.Response(exchange["status_code"], json=exchange["body"])


async def test_reserves_estimate_before_network_and_reconciles_measured_tokens() -> None:
    request, exchange = _recorded_exam()
    harness = _Harness(_ok(exchange))

    labeling = await harness.labeler.label(request=request)

    assert harness.events == ["reserve", "post"]
    reserve = harness.leases.reserve.await_args.kwargs
    assert reserve["requested_tokens"] == harness.adapter.estimate_input_tokens(request=request)
    assert reserve["job_id"] == request.job_id
    assert reserve["item_id"] == LEASE_ITEM_ID
    assert reserve["provider_profile_id"] == "openai-decisions-gpt-6-luna"
    measured = exchange["body"]["usage"]["input_tokens"]
    assert harness.leases.reconcile.await_args.kwargs["actual_tokens"] == measured
    assert labeling.usage.input_tokens == measured
    assert len(labeling.results) == len(request.items)


async def test_refused_lease_fails_closed_without_network() -> None:
    request, exchange = _recorded_exam()
    harness = _Harness(_ok(exchange))
    harness.leases.reserve.side_effect = AnswerKeyTokenLeaseRefused(
        utc_day=_NOW.date(), requested_tokens=10, available_tokens=0, resets_at=_NOW
    )

    with pytest.raises(ItemTypeLabelerError) as raised:
        await harness.labeler.label(request=request)

    assert raised.value.code == "lease_refused"
    assert "post" not in harness.events


async def test_unavailable_provider_keeps_reservation_charged() -> None:
    request, _ = _recorded_exam()
    failure = _fixture("decisions_unavailable_responses.json")["responses"][0]
    harness = _Harness(*(httpx.Response(503, json=failure["body"]) for _ in range(3)))

    with pytest.raises(ItemTypeLabelerError) as raised:
        await harness.labeler.label(request=request)

    assert raised.value.code == "provider_unavailable"
    harness.leases.reconcile.assert_not_awaited()


async def test_failed_reconciliation_still_returns_labels() -> None:
    request, exchange = _recorded_exam()
    harness = _Harness(_ok(exchange))
    harness.leases.reconcile.side_effect = RuntimeError("database unavailable")

    labeling = await harness.labeler.label(request=request)

    assert [result.item_id for result in labeling.results] == [
        item.item_id for item in request.items
    ]


async def test_empty_request_spends_nothing() -> None:
    harness = _Harness()

    labeling = await harness.labeler.label(request=LabelingRequest(job_id=uuid4(), items=()))

    assert labeling.results == ()
    assert harness.events == []
