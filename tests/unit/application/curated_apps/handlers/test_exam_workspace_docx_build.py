"""Batched failed-only retries, leases, measured usage and graceful fallbacks."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build import DocxAIConverter
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    AnswerKeyProviderRoute,
    StructuredLLMBackendFailureCode,
    StructuredLLMEndpointKind,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMResponse,
    StructuredLLMUsage,
    estimate_prompt_tokens,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLease,
    AnswerKeyTokenLeaseDayUsage,
    AnswerKeyTokenLeaseState,
    refuse_lease,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeItemReviewState,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyProviderSelectorProtocol,
    AnswerKeyStructuredProviderProtocol,
    AnswerKeyTokenLeaseRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.unit.domain.curated_apps.exam_workspace.test_docx_ai_build import (
    choice_entry,
    choice_source,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_NOW = datetime(2026, 10, 10, 18, tzinfo=UTC)


def response(
    entries,
    *,
    usage=StructuredLLMUsage(100, 50, 150),
    finish="completed",
    title=None,
    instructions=None,
):
    return StructuredLLMResponse(
        content={"title": title, "instructions": instructions or [], "items": entries},
        finish_reason=finish,
        usage=usage,
    )


def ports(*, enabled=True, context=128000):
    provider = AsyncMock(spec=AnswerKeyStructuredProviderProtocol)
    leases = AsyncMock(spec=AnswerKeyTokenLeaseRepositoryProtocol)
    leases.reserve.return_value = AnswerKeyTokenLease(
        lease_id=uuid4(),
        utc_day=_NOW.date(),
        reserved_tokens=20000,
        state=AnswerKeyTokenLeaseState.RESERVED,
    )
    uow = AsyncMock(spec=UnitOfWorkProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = _NOW
    primary = StructuredLLMProviderProfile(
        "primary", "model", StructuredLLMEndpointKind.RESPONSES, True, context, 4096
    )
    backup = StructuredLLMProviderProfile(
        "backup", "other", StructuredLLMEndpointKind.CHAT_COMPLETIONS, True, 128000, 4096
    )
    selector = Mock(spec=AnswerKeyProviderSelectorProtocol)
    selector.select_route.return_value = AnswerKeyProviderRoute(primary, backup)
    converter = DocxAIConverter(provider, selector, leases, uow, clock, enabled)
    return converter, provider, leases, uow, selector


async def convert(converter, chunks=None, **kwargs):
    return await converter.convert(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="test.docx",
        source_sha256="a" * 64,
        chunks=chunks or choice_source(),
        **kwargs,
    )


async def test_one_whole_exam_call_reserves_before_network_and_reconciles_measured_usage():
    converter, provider, leases, uow, selector = ports()
    source = (*choice_source(), *choice_source(2))

    async def complete(*, request, profile):
        assert leases.reserve.await_count == 1
        assert uow.__aexit__.await_count == 1
        assert len(json.loads(request.user_payload)["chunks"]) == 6
        assert profile.provider_id == "primary"
        assert profile.max_output_tokens == request.max_output_tokens == 16384
        assert request.estimated_input_tokens > estimate_prompt_tokens(request.user_payload)
        return response(
            [choice_entry().model_dump(mode="json"), choice_entry(2).model_dump(mode="json")]
        )

    provider.complete_structured.side_effect = complete
    result = await convert(converter, source)
    assert provider.complete_structured.await_count == 1
    assert len(result.document.items) == 2
    assert result.input_tokens == 100
    assert result.output_tokens == 50
    leases.reconcile.assert_awaited_once_with(
        lease_id=leases.reserve.return_value.lease_id, actual_tokens=150, now=_NOW
    )
    assert selector.select_route.return_value.primary.max_output_tokens == 4096
    reserve = leases.reserve.call_args.kwargs
    request = provider.complete_structured.call_args.kwargs["request"]
    assert reserve["requested_tokens"] == request.estimated_input_tokens + 16384


async def test_only_failed_items_and_chunks_are_retried_and_ids_are_source_ordered():
    converter, provider, leases, _, _ = ports()
    bad = choice_entry().model_dump(mode="json")
    bad["item"]["points"] = 9
    provider.complete_structured.side_effect = [
        response([choice_entry(2).model_dump(mode="json"), bad]),
        response([choice_entry().model_dump(mode="json")]),
    ]
    result = await convert(converter, (*choice_source(), *choice_source(2)))
    assert provider.complete_structured.await_count == 2
    second = json.loads(provider.complete_structured.call_args.kwargs["request"].user_payload)
    assert {c["anchor"] for c in second["chunks"]} == {"q1", "c1", "k1", "k2"}
    assert second["validation_errors"]
    assert [i.source_anchor for i in result.document.items] == ["q1", "q2"]
    assert [i.item_id for i in result.document.items] == ["item_001", "item_002"]
    assert leases.reserve.await_count == leases.reconcile.await_count == 2
    assert (result.input_tokens, result.output_tokens) == (200, 100)


async def test_three_round_bound_keeps_passed_item_and_every_failed_source_chunk():
    converter, provider, leases, _, _ = ports()
    bad = choice_entry(2).model_dump(mode="json")
    del bad["item"]["body"]
    provider.complete_structured.side_effect = [
        response([choice_entry().model_dump(mode="json"), bad]),
        response([bad]),
        response([bad]),
    ]
    result = await convert(converter, (*choice_source(), *choice_source(2)))
    assert provider.complete_structured.await_count == leases.reserve.await_count == 3
    assert result.document.items[0].review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert any(
        i.source_anchor == "q2" and i.review.state is NativeItemReviewState.REVIEW_REQUIRED
        for i in result.document.items
    )
    assert any("Correct answer" in note for note in result.notes)
    for call in provider.complete_structured.call_args_list[1:]:
        anchors = {c["anchor"] for c in json.loads(call.kwargs["request"].user_payload)["chunks"]}
        assert not anchors & {"q1", "c1"}
        assert {"k1", "k2"} <= anchors


def shared_key_source():
    return (
        *choice_source(1)[:2],
        *choice_source(2)[:2],
        DocxChunk("facit", "heading", "Answer key"),
        DocxChunk("keys", "paragraph", "1. B\n2. B"),
    )


def shared_key_entry(number):
    raw = choice_entry(number).model_dump(mode="json")
    raw["key_evidence"][0].update(anchor="keys", text=f"{number}. B")
    return raw


@pytest.mark.parametrize("key_in_source_anchors", [False, True])
async def test_shared_facit_paragraph_accepts_both_questions_in_one_batch(key_in_source_anchors):
    converter, provider, leases, _, _ = ports()
    entries = [shared_key_entry(1), shared_key_entry(2)]
    if key_in_source_anchors:
        for entry in entries:
            entry["source_anchors"].append("keys")
    provider.complete_structured.return_value = response(entries)
    result = await convert(converter, shared_key_source())
    assert provider.complete_structured.await_count == 1
    assert leases.reserve.await_count == leases.reconcile.await_count == 1
    assert [item.source_anchor for item in result.document.items] == ["q1", "q2"]
    assert all(
        item.review.state is NativeItemReviewState.REVIEW_COMPLETE for item in result.document.items
    )
    assert "1. B\n2. B" in result.notes


async def test_shared_facit_survives_failed_only_retry_and_accepted_question_is_frozen():
    converter, provider, leases, _, _ = ports()
    bad = shared_key_entry(2)
    bad["item"]["points"] = 9
    attempted_rewrite = shared_key_entry(1)
    attempted_rewrite["item"]["title"] = "Pick a colour."
    provider.complete_structured.side_effect = [
        response([shared_key_entry(1), bad]),
        response([attempted_rewrite, shared_key_entry(2)]),
    ]
    result = await convert(converter, shared_key_source())
    assert provider.complete_structured.await_count == 2
    assert leases.reserve.await_count == leases.reconcile.await_count == 2
    retry = json.loads(provider.complete_structured.call_args.kwargs["request"].user_payload)
    assert {chunk["anchor"] for chunk in retry["chunks"]} == {"q2", "c2", "facit", "keys"}
    assert next(chunk["text"] for chunk in retry["chunks"] if chunk["anchor"] == "keys") == (
        "1. B\n2. B"
    )
    assert retry["validation_errors"]
    assert [item.source_anchor for item in result.document.items] == ["q1", "q2"]
    assert [item.points for item in result.document.items] == [2, 2]
    assert result.document.items[0].title is None
    assert all(
        item.review.state is NativeItemReviewState.REVIEW_COMPLETE for item in result.document.items
    )
    assert (result.input_tokens, result.output_tokens) == (200, 100)


async def test_consumed_question_cannot_be_reused_by_another_entry_in_same_batch():
    converter, provider, _, _, _ = ports()
    duplicated = shared_key_entry(1)
    provider.complete_structured.side_effect = [
        response([duplicated, duplicated, shared_key_entry(2)])
    ]
    result = await convert(converter, shared_key_source())
    assert provider.complete_structured.await_count == 1
    assert [item.source_anchor for item in result.document.items] == ["q1", "q2"]


@pytest.mark.parametrize(
    "cause", ["disabled", "lease", "timeout", "refusal", "unavailable", "expired", "context"]
)
async def test_fallback_opens_and_keeps_all_chunks_for_each_failure(cause):
    converter, provider, leases, _, _ = ports(
        enabled=cause != "disabled", context=18000 if cause == "context" else 128000
    )
    kwargs = {}
    if cause == "lease":
        leases.reserve.side_effect = refuse_lease(
            usage=AnswerKeyTokenLeaseDayUsage(_NOW.date(), 10, 10), requested_tokens=20000
        )
    elif cause in {"timeout", "refusal"}:
        code = (
            StructuredLLMBackendFailureCode.PROVIDER_REFUSAL
            if cause == "refusal"
            else StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT
        )
        provider.complete_structured.side_effect = StructuredLLMProviderError(
            failure_code=code, message="failure", provider_id="primary"
        )
    elif cause == "unavailable":
        provider.complete_structured.side_effect = RuntimeError("unavailable")
    elif cause == "expired":
        kwargs["fallback_reason"] = "Arbetarens tidsgräns passerades."
    result = await convert(converter, **kwargs)
    assert result.document.revision == 1
    assert [i.plain_text_lines()[0] for i in result.document.items] == [
        c.text for c in choice_source()
    ]
    assert all(
        i.review.state is NativeItemReviewState.REVIEW_REQUIRED for i in result.document.items
    )
    assert all(i.review.reasons for i in result.document.items)
    assert result.input_tokens is result.output_tokens is None
    leases.reconcile.assert_not_awaited()
    assert provider.complete_structured.await_count == (
        1 if cause in {"timeout", "refusal", "unavailable"} else 0
    )


async def test_incomplete_response_is_not_admitted_or_refunded():
    converter, provider, leases, _, _ = ports()
    provider.complete_structured.return_value = response(
        [choice_entry().model_dump(mode="json")], finish="incomplete"
    )
    result = await convert(converter)
    assert all(
        i.review.state is NativeItemReviewState.REVIEW_REQUIRED for i in result.document.items
    )
    leases.reconcile.assert_not_awaited()
    assert "ofullständigt" in result.notes[-1]


async def test_missing_usage_never_reports_estimates_as_measured_tokens():
    converter, provider, leases, _, _ = ports()
    provider.complete_structured.return_value = response(
        [choice_entry().model_dump(mode="json")], usage=StructuredLLMUsage()
    )
    result = await convert(converter)
    assert result.input_tokens is result.output_tokens is None
    leases.reconcile.assert_not_awaited()


async def test_metadata_passes_are_excluded_from_retry_and_unclaimed_text_remains_reviewable():
    converter, provider, _, _, _ = ports()
    chunks = (
        DocxChunk("title", "heading", "Colour test"),
        *choice_source(),
        DocxChunk("unclaimed", "table", "Unparsed table"),
    )
    provider.complete_structured.side_effect = [
        response(
            [choice_entry().model_dump(mode="json")],
            title={"text": "Colour test", "source_anchors": ["title"]},
        ),
        response([]),
        response([]),
    ]
    result = await convert(converter, chunks)
    assert result.document.title == "Colour test"
    assert result.document.items[-1].plain_text_lines() == ("Unparsed table",)
    for call in provider.complete_structured.call_args_list[1:]:
        assert [c["anchor"] for c in json.loads(call.kwargs["request"].user_payload)["chunks"]] == [
            "k1",
            "unclaimed",
        ]


async def test_wrong_endpoint_never_calls_provider_or_reserves_lease():
    converter, provider, leases, _, selector = ports()
    route = selector.select_route.return_value
    selector.select_route.return_value = AnswerKeyProviderRoute(route.failover, route.primary)
    result = await convert(converter)
    assert all(
        i.review.state is NativeItemReviewState.REVIEW_REQUIRED for i in result.document.items
    )
    provider.complete_structured.assert_not_awaited()
    leases.reserve.assert_not_awaited()


async def test_quiz_recorded_response_all_items_pass_without_live_provider():
    from pathlib import Path

    from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
        exam_workspace_docx_chunker,
    )

    fixture = Path("tests/fixtures/exam_conversion")
    recorded = json.loads((fixture / "chapter_4_poetry_docx_build_response.json").read_text())
    chunks = exam_workspace_docx_chunker.PythonDocxExamChunker().chunk(
        content=(
            fixture / "docx_corpus/chapter_4_poetry_and_lyrics_quiz_med_facit.docx"
        ).read_bytes()
    )
    converter, provider, _, _, _ = ports()
    provider.complete_structured.return_value = StructuredLLMResponse(
        recorded, "completed", StructuredLLMUsage(900, 800, 1700)
    )
    result = await convert(converter, chunks)
    assert provider.complete_structured.await_count == 1
    assert len(result.document.items) == 28
    assert sum(item.points for item in result.document.items) == 28
    assert all(
        item.review.state is NativeItemReviewState.REVIEW_COMPLETE for item in result.document.items
    )
