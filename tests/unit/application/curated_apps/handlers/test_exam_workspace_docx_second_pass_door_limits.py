"""Door limits across second-pass item-type labeling (TASK-SKRIPT-41-01-03 B3).

A refused second pass keeps the first pass's top label and reports the limit; the cap
reports pool.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.item_type_labeling import TwoPassItemTypeLabeler
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
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
