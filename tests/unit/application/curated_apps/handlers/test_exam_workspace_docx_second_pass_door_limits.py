"""Door limits across second-pass item-type labeling (TASK-SKRIPT-41-01-03 B3).

A refused second pass keeps the first pass's top label and reports the limit; the cap
reports pool. A busy door is no per-question failure: it propagates out of the labeler and
the other questions' pending second-pass calls are cancelled.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.item_type_labeling import TwoPassItemTypeLabeler
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorBusy,
    AiJobOverageCapReached,
)
from skriptoteket.protocols.item_type_labeler import (
    ItemTypeLabel,
    ItemTypeLabeling,
    ItemTypeLabelResult,
    LabelingItem,
    LabelingRequest,
    LabelingUsage,
    LabelRoute,
    MeteredItemTypeLabelerProtocol,
    SecondPassItemTypeLabelerProtocol,
    SecondPassLabel,
)
from tests.unit.llm_door_fakes import fixture_caller

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class _ScriptedFirstPass(MeteredItemTypeLabelerProtocol):
    provider_profile_id = "scripted-first"

    def __init__(self, result: ItemTypeLabelResult) -> None:
        self._result = result

    def estimate_input_tokens(self, *, request: LabelingRequest) -> int:
        return 1

    async def label(self, *, request: LabelingRequest) -> ItemTypeLabeling:
        return ItemTypeLabeling(results=(self._result,), usage=LabelingUsage(input_tokens=1))


class _RefusedSecondPass(SecondPassItemTypeLabelerProtocol):
    provider_profile_id = "scripted-second"

    def __init__(self, error: Exception) -> None:
        self._error = error

    def estimate_tokens(self, *, item: LabelingItem) -> int:
        return 1

    async def label_one(self, *, job_id, item, caller) -> SecondPassLabel:
        raise self._error


def _escalated(item_id: str = "q1") -> ItemTypeLabelResult:
    return ItemTypeLabelResult(
        item_id=item_id,
        label=ItemTypeLabel.UNRESOLVED,
        probabilities={ItemTypeLabel.SINGLE_CHOICE: 0.5, ItemTypeLabel.UNRESOLVED: 0.4},
        probability=0.5,
        threshold=0.95,
        route=LabelRoute.ESCALATE,
    )


async def test_second_pass_limit_keeps_first_pass_top_label_and_reports() -> None:
    refusal = AiDailyLimitReached(limit=AiDailyLimit.USER_SHARE)
    labeler = TwoPassItemTypeLabeler(
        first_pass=_ScriptedFirstPass(_escalated()),
        second_pass=_RefusedSecondPass(refusal),
    )
    seen: list[AiDailyLimitReached | AiJobOverageCapReached] = []
    request = LabelingRequest(
        job_id=uuid4(),
        items=(LabelingItem(item_id="q1", source_text="text"),),
        caller=fixture_caller(),
    )

    labeling = await labeler.label(request=request, on_limit=seen.append)

    (result,) = labeling.results
    assert result.label is ItemTypeLabel.SINGLE_CHOICE
    assert result.failure_code == "ai_daily_limit"
    assert seen == [refusal]


async def test_second_pass_overage_cap_reports_pool() -> None:
    refusal = AiJobOverageCapReached(overage_usd_micros=2_000_000, cap_usd_micros=1_000_000)
    labeler = TwoPassItemTypeLabeler(
        first_pass=_ScriptedFirstPass(_escalated()),
        second_pass=_RefusedSecondPass(refusal),
    )
    seen: list[AiDailyLimitReached | AiJobOverageCapReached] = []
    request = LabelingRequest(
        job_id=uuid4(),
        items=(LabelingItem(item_id="q1", source_text="text"),),
        caller=fixture_caller(),
    )

    labeling = await labeler.label(request=request, on_limit=seen.append)

    (result,) = labeling.results
    assert result.label is ItemTypeLabel.SINGLE_CHOICE
    assert result.failure_code == "ai_overage_cap"
    assert seen == [refusal]


class _BusyThenSlowSecondPass(SecondPassItemTypeLabelerProtocol):
    """The first question's call meets a busy door; the others wait until cancelled."""

    provider_profile_id = "scripted-second"

    def __init__(self) -> None:
        self.started: list[str] = []
        self.cancelled: list[str] = []

    def estimate_tokens(self, *, item: LabelingItem) -> int:
        return 1

    async def label_one(self, *, job_id, item, caller) -> SecondPassLabel:
        self.started.append(item.item_id)
        if item.item_id == "q1":
            raise AiDoorBusy(retry_after_seconds=2)
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            self.cancelled.append(item.item_id)
            raise
        raise AssertionError("a pending second-pass call outlived the busy door")


class _ScriptedManyFirstPass(MeteredItemTypeLabelerProtocol):
    provider_profile_id = "scripted-first"

    def estimate_input_tokens(self, *, request: LabelingRequest) -> int:
        return 1

    async def label(self, *, request: LabelingRequest) -> ItemTypeLabeling:
        return ItemTypeLabeling(
            results=tuple(_escalated(item.item_id) for item in request.items),
            usage=LabelingUsage(input_tokens=1),
        )


async def test_second_pass_busy_door_propagates_and_cancels_the_other_questions() -> None:
    second = _BusyThenSlowSecondPass()
    labeler = TwoPassItemTypeLabeler(first_pass=_ScriptedManyFirstPass(), second_pass=second)
    seen: list[AiDailyLimitReached | AiJobOverageCapReached] = []
    request = LabelingRequest(
        job_id=uuid4(),
        items=(
            LabelingItem(item_id="q1", source_text="text"),
            LabelingItem(item_id="q2", source_text="text"),
            LabelingItem(item_id="q3", source_text="text"),
        ),
        caller=fixture_caller(),
    )

    with pytest.raises(AiDoorBusy) as caught:
        await labeler.label(request=request, on_limit=seen.append)

    assert caught.value.retry_after_seconds == 2
    assert seen == [], "a busy door is not a limit"
    assert sorted(second.started) == ["q1", "q2", "q3"]
    assert sorted(second.cancelled) == ["q2", "q3"]
