"""Exercise streamed observation alongside the unchanged terminal admission path."""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build import convert_batch
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxBuildExchangeProtocol,
    DocxBuildRoundExchange,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import (
    ConversionBatch,
    QuestionFamily,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.llm_door import AiDoorCaller
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyStructuredProviderProtocol,
    StructuredLLMTextObserver,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_one_item_test_support import (
    _item,
    _state,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import PROFILE
from tests.unit.llm_door_fakes import fixture_caller

pytestmark = pytest.mark.asyncio


class FragmentedProvider:
    """Synthetic streamed text followed by an independently supplied terminal response."""

    def __init__(
        self,
        fragments: tuple[str, ...],
        content: dict[str, JsonValue],
        *,
        failure: Exception | None = None,
    ) -> None:
        self.fragments = fragments
        self.response = StructuredLLMResponse(
            content=content,
            finish_reason="completed",
            usage=StructuredLLMUsage(prompt_tokens=12, completion_tokens=34),
        )
        self.failure = failure
        self.observed = asyncio.Event()
        self.release = asyncio.Event()
        self.calls = 0

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
        caller: AiDoorCaller,
        on_text: StructuredLLMTextObserver | None = None,
    ) -> StructuredLLMResponse:
        self.calls += 1
        if on_text is not None:
            for fragment in self.fragments:
                await on_text(fragment)
        self.observed.set()
        await self.release.wait()
        if self.failure is not None:
            raise self.failure
        return self.response


def batch_inputs():
    state = _state(
        (("paragraph", "1. Förklara ett subjekt. (2 p)"),),
        (("paragraph", "2. Förklara ett predikat. (2 p)"),),
    )
    families = {
        f"q{index}": QuestionFamily(f"q{index}", index, anchors, frozenset(anchors), frozenset())
        for index, anchors in enumerate(state.questions, 1)
    }
    batch = ConversionBatch(
        "test", frozenset({NativeExamItemKind.FREE_TEXT}), tuple(families), state.owned, frozenset()
    )
    return state, families, batch


def final_content() -> dict[str, JsonValue]:
    # This merged item must still pass through the ordinary one-question admission rule.
    return {
        "title": None,
        "instructions": [],
        "answer_key_anchors": [],
        "items": [_item(["body:0001", "body:0002"], "Två frågor", "1.")],
    }


async def test_receipt_precedes_final_and_final_still_gets_ordinary_admission():
    state, families, batch = batch_inputs()
    ordinary = state.snapshot()
    admit_batch(final_content(), ordinary)
    provider: AnswerKeyStructuredProviderProtocol = FragmentedProvider(
        ('{"items":[{"outcome":"review","source_anchors":["body:0001"]}',),
        final_content(),
    )
    assert isinstance(provider, FragmentedProvider)
    exchange: DocxBuildExchangeProtocol = DocxBuildRoundExchange(provider)
    received = AsyncMock()
    conversion = asyncio.create_task(
        convert_batch(
            state=state,
            batch=batch,
            families=families,
            exchange=exchange,
            profile=PROFILE,
            caller=fixture_caller(),
            on_received=received,
        )
    )
    await asyncio.wait_for(provider.observed.wait(), timeout=2)
    received.assert_awaited_once_with(("q1",))
    assert state.accepted == []
    assert not conversion.done(), "receipt must not wait for the terminal response"
    provider.release.set()
    outcome = await asyncio.wait_for(conversion, timeout=2)
    assert provider.calls == 1
    assert outcome.state.accepted == ordinary.accepted
    assert outcome.state.claimed == ordinary.claimed
    assert outcome.state.events == ordinary.events
    assert outcome.state.input_tokens == 12
    assert outcome.state.output_tokens == 34


@pytest.mark.parametrize("tail", [',{"source_anchors":[', ",broken JSON"])
async def test_observer_tail_neither_changes_final_admission_nor_adds_a_retry(tail: str):
    state, families, batch = batch_inputs()
    ordinary = state.snapshot()
    admit_batch(final_content(), ordinary)
    provider = FragmentedProvider(
        ('{"items":[{"source_anchors":["body:0001"]}' + tail,), final_content()
    )
    provider.release.set()
    received = AsyncMock()
    outcome = await convert_batch(
        state=state,
        batch=batch,
        families=families,
        exchange=DocxBuildRoundExchange(provider),
        profile=PROFILE,
        caller=fixture_caller(),
        on_received=received,
    )
    received.assert_awaited_once_with(("q1",))
    assert provider.calls == 1
    assert outcome.state.accepted == ordinary.accepted
    assert outcome.state.events == ordinary.events


async def test_prior_receipt_remains_when_stream_later_fails():
    state, families, batch = batch_inputs()
    provider = FragmentedProvider(
        ('{"items":[' + json.dumps({"source_anchors": ["body:0001"]}),),
        final_content(),
        failure=OSError("stream disconnected"),
    )
    provider.release.set()
    received = AsyncMock()
    outcome = await convert_batch(
        state=state,
        batch=batch,
        families=families,
        exchange=DocxBuildRoundExchange(provider),
        profile=PROFILE,
        caller=fixture_caller(),
        on_received=received,
    )
    received.assert_awaited_once_with(("q1",))
    assert any(event.code == "provider_unavailable" for event in outcome.state.events)
    assert provider.calls == 1
