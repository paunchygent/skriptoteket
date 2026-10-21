"""Boundary tests for the Responses second-pass item-type labeler (pass B)."""

from __future__ import annotations

import json
from uuid import UUID

import pytest

from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    IMAGE_INPUT_TOKEN_ESTIMATE,
    SourceImage,
    StructuredLLMBackendFailureCode,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMReasoningEffort,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMTextVerbosity,
    StructuredLLMUsage,
    estimate_prompt_tokens,
)
from skriptoteket.domain.llm_door import AiDoorCaller
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    build_answer_key_responses_payload,
)
from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    LABEL_DESCRIPTIONS,
    render_items,
)
from skriptoteket.infrastructure.llm.openai.docx_conversion_profiles import (
    build_luna_item_label_profile,
)
from skriptoteket.infrastructure.llm.openai.responses_item_labeler import (
    ResponsesSecondPassItemTypeLabeler,
    build_second_pass_request,
)
from skriptoteket.protocols.item_type_labeler import (
    ItemTypeLabel,
    ItemTypeLabelerError,
    LabelingItem,
)
from tests.unit.llm_door_fakes import fixture_caller

JOB_ID = UUID("00000000-0000-0000-0000-0000000000aa")
ITEM = LabelingItem(item_id="q7", source_text="Fråga 7\nVälj ett alternativ.")


def _profile() -> StructuredLLMProviderProfile:
    return build_luna_item_label_profile(Settings(_env_file=None))


def _ok(content: dict, finish: str | None = "completed") -> StructuredLLMResponse:
    return StructuredLLMResponse(
        content=content,
        finish_reason=finish,
        usage=StructuredLLMUsage(prompt_tokens=120, completion_tokens=9),
    )


def _error(code: StructuredLLMBackendFailureCode, status: int | None = None):
    return StructuredLLMProviderError(
        failure_code=code, message="x", provider_id="p", status_code=status
    )


class FakeProvider:
    def __init__(self, *outcomes: StructuredLLMResponse | Exception) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[StructuredLLMRequest] = []

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
        caller: AiDoorCaller,
    ) -> StructuredLLMResponse:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class RecordingSleeper:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def sleep(self, seconds: float) -> None:
        self.delays.append(seconds)


def _labeler(provider: FakeProvider, sleeper: RecordingSleeper):
    return ResponsesSecondPassItemTypeLabeler(
        provider=provider, profile=_profile(), sleeper=sleeper
    )


def test_profile_matches_measured_pass_b() -> None:
    profile = _profile()
    assert profile.reasoning_effort is StructuredLLMReasoningEffort.LOW
    assert profile.text_verbosity is StructuredLLMTextVerbosity.LOW
    assert profile.max_output_tokens == 4000


def test_request_fields_and_schema() -> None:
    profile = _profile()
    request = build_second_pass_request(job_id=JOB_ID, item=ITEM, profile=profile)
    assert request.job_id == str(JOB_ID)
    assert request.item_id == "label_b:q7"
    assert request.item_type == "item_type_label"
    assert request.prompt_template_version == "item_type_label_b_v1"
    assert request.system_prompt == (
        "Select exactly one supported label for the target question. Return only the schema object."
    )
    assert request.user_payload == render_items((ITEM,))
    assert request.user_images == ()
    assert request.max_output_tokens == profile.max_output_tokens
    spec = request.output_spec
    assert (spec.schema_name, spec.schema_version) == ("item_type_label", "1")
    schema = spec.json_schema
    assert schema["required"] == ["label"]
    assert schema["additionalProperties"] is False
    properties = schema["properties"]
    assert isinstance(properties, dict)
    label_property = properties["label"]
    assert isinstance(label_property, dict)
    assert label_property["enum"] == [label.value for label in ItemTypeLabel]
    description = label_property["description"]
    assert isinstance(description, str)
    for label in ItemTypeLabel:
        assert f"{label.value}: {LABEL_DESCRIPTIONS[label]}" in description
    assert request.estimated_input_tokens == estimate_prompt_tokens(
        request.system_prompt + request.user_payload + json.dumps(schema)
    )


def test_estimate_tokens_adds_output_allowance() -> None:
    labeler = _labeler(FakeProvider(), RecordingSleeper())
    request = build_second_pass_request(job_id=JOB_ID, item=ITEM, profile=_profile())
    assert labeler.estimate_tokens(item=ITEM) == request.estimated_input_tokens + 4000
    assert labeler.provider_profile_id == _profile().provider_id


@pytest.mark.asyncio
async def test_label_returned_with_usage() -> None:
    provider = FakeProvider(_ok({"label": "gap_fill"}))
    result = await _labeler(provider, RecordingSleeper()).label_one(
        job_id=JOB_ID, item=ITEM, caller=fixture_caller()
    )
    assert result.label is ItemTypeLabel.GAP_FILL
    assert (result.input_tokens, result.output_tokens, result.refused) == (120, 9, False)


@pytest.mark.asyncio
async def test_transient_error_retries_once_and_sleeps() -> None:
    provider = FakeProvider(
        _error(StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR, 503),
        _ok({"label": "matching"}),
    )
    sleeper = RecordingSleeper()
    result = await _labeler(provider, sleeper).label_one(
        job_id=JOB_ID, item=ITEM, caller=fixture_caller()
    )
    assert result.label is ItemTypeLabel.MATCHING
    assert sleeper.delays == [1.0]
    assert len(provider.requests) == 2


@pytest.mark.asyncio
async def test_transient_error_exhausts_attempts() -> None:
    provider = FakeProvider(*[_error(StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT)] * 3)
    sleeper = RecordingSleeper()
    with pytest.raises(ItemTypeLabelerError) as caught:
        await _labeler(provider, sleeper).label_one(
            job_id=JOB_ID, item=ITEM, caller=fixture_caller()
        )
    assert caught.value.code == "provider_timeout"
    assert sleeper.delays == [1.0, 2.0]


@pytest.mark.asyncio
async def test_refusal_maps_to_unresolved_refused() -> None:
    provider = FakeProvider(_error(StructuredLLMBackendFailureCode.PROVIDER_REFUSAL))
    result = await _labeler(provider, RecordingSleeper()).label_one(
        job_id=JOB_ID, item=ITEM, caller=fixture_caller()
    )
    assert result.label is ItemTypeLabel.UNRESOLVED
    assert result.refused is True
    assert result.input_tokens is None and result.output_tokens is None


@pytest.mark.asyncio
async def test_non_transient_error_raises_without_retry() -> None:
    provider = FakeProvider(_error(StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR, 400))
    sleeper = RecordingSleeper()
    with pytest.raises(ItemTypeLabelerError) as caught:
        await _labeler(provider, sleeper).label_one(
            job_id=JOB_ID, item=ITEM, caller=fixture_caller()
        )
    assert (caught.value.code, caught.value.status_code) == ("provider_http_error", 400)
    assert sleeper.delays == []
    assert len(provider.requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "code"),
    [
        (_ok({"label": "gap_fill"}, finish="incomplete"), "incomplete"),
        (_ok({"label": "gap_fill", "extra": 1}), "schema_mismatch"),
        (_ok({"label": "essay"}), "schema_mismatch"),
        (_ok({}), "schema_mismatch"),
    ],
)
async def test_invalid_responses_raise(response: StructuredLLMResponse, code: str) -> None:
    with pytest.raises(ItemTypeLabelerError) as caught:
        await _labeler(FakeProvider(response), RecordingSleeper()).label_one(
            job_id=JOB_ID, item=ITEM, caller=fixture_caller()
        )
    assert caught.value.code == code


def test_a_source_image_stands_at_its_place_in_the_responses_input() -> None:
    png = b"\x89PNG\r\n\x1a\nfixture"
    item = LabelingItem(
        item_id="q8",
        source_text="Fråga 8\nPara ihop orden.",
        images=(SourceImage(png, len("Fråga 8")),),
    )
    profile = _profile()
    request = build_second_pass_request(job_id=JOB_ID, item=item, profile=profile)
    text_only = build_second_pass_request(
        job_id=JOB_ID,
        item=LabelingItem(item_id="q8", source_text=item.source_text),
        profile=profile,
    )

    content = build_answer_key_responses_payload(profile=profile, request=request)["input"]
    assert isinstance(content, list) and isinstance(content[0], dict)
    parts = content[0]["content"]
    assert parts == [
        {"type": "input_text", "text": request.user_payload.removesuffix("\nPara ihop orden.")},
        {"type": "input_image", "image_url": SourceImage(png, 0).data_url},
        {"type": "input_text", "text": "\nPara ihop orden."},
    ]
    assert request.estimated_input_tokens == (
        text_only.estimated_input_tokens + IMAGE_INPUT_TOKEN_ESTIMATE
    )
