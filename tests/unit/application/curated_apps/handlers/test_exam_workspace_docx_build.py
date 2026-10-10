"""Batched failed-only retries, leases, measured usage and graceful fallbacks."""

import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
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
    NativeExamItemKind,
    NativeItemReviewState,
    native_export_blockers,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyProviderSelectorProtocol,
    AnswerKeyStructuredProviderProtocol,
    AnswerKeyTokenLeaseRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.unit.domain.curated_apps.exam_workspace.test_docx_ai_build import (
    choice_item,
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
    answer_key_anchors=None,
):
    return StructuredLLMResponse(
        content={
            "title": title,
            "instructions": instructions or [],
            "answer_key_anchors": answer_key_anchors or [],
            "items": entries,
        },
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
        payload = json.loads(request.user_payload)
        assert [chunk["anchor"] for chunk in payload["chunks"]] == [c.anchor for c in source]
        assert payload["answer_key_chunks"] == []
        assert payload["validation_errors"] == []
        assert profile.provider_id == "primary"
        assert profile.max_output_tokens == request.max_output_tokens == 16384
        assert request.estimated_input_tokens > estimate_prompt_tokens(request.user_payload)
        return response([choice_item(), choice_item(2)], answer_key_anchors=["k1", "k2"])

    provider.complete_structured.side_effect = complete
    result = await convert(converter, source)
    assert provider.complete_structured.await_count == 1
    assert len(result.document.items) == 2
    assert (result.input_tokens, result.output_tokens) == (100, 50)
    assert result.events == ()
    leases.reconcile.assert_awaited_once_with(
        lease_id=leases.reserve.return_value.lease_id, actual_tokens=150, now=_NOW
    )
    assert selector.select_route.return_value.primary.max_output_tokens == 4096
    request = provider.complete_structured.call_args.kwargs["request"]
    assert (
        leases.reserve.call_args.kwargs["requested_tokens"]
        == request.estimated_input_tokens + 16384
    )


def invalid_choice(n=1):
    return choice_item(
        n, choices=[{"text": "red", "correct": True}, {"text": "blue", "correct": True}]
    )


async def test_only_failed_chunks_are_retried_and_accepted_item_is_frozen():
    converter, provider, leases, _, _ = ports()
    provider.complete_structured.side_effect = [
        response([choice_item(), invalid_choice(2)], answer_key_anchors=["k1", "k2"]),
        response([choice_item(title="Attempted replacement", points=9), choice_item(2)]),
    ]
    result = await convert(converter, (*choice_source(), *choice_source(2)))
    assert provider.complete_structured.await_count == 2
    retry = json.loads(provider.complete_structured.call_args.kwargs["request"].user_payload)
    assert [c["anchor"] for c in retry["chunks"]] == ["h2", "q2", "c2"]
    assert [c["anchor"] for c in retry["answer_key_chunks"]] == ["k1", "k2"]
    assert all("native_contract_invalid" in error for error in retry["validation_errors"])
    assert [i.source_anchor for i in result.document.items] == ["h1", "h2"]
    assert [i.item_id for i in result.document.items] == ["item_001", "item_002"]
    accepted = result.document.items[0]
    assert accepted.title == choice_item()["title"]
    assert accepted.plain_text_lines() == ("Pick a colour.",)
    assert accepted.answer_key.correct_choice_ids == ("choice_002",)
    assert accepted.points == 1
    assert any(e.code == "anchor_conflict" and e.round == 2 and e.item == 0 for e in result.events)
    assert all(
        i.review.state is NativeItemReviewState.REVIEW_COMPLETE for i in result.document.items
    )
    assert leases.reserve.await_count == leases.reconcile.await_count == 2
    assert (result.input_tokens, result.output_tokens) == (200, 100)


async def test_three_round_bound_preserves_invalid_source_with_safe_failure_details():
    fixture = Path("tests/fixtures/exam_conversion/chapter_4_poetry_docx_build_response.json")
    prompt = json.loads(fixture.read_text())["items"][0]["body"][0]["segments"][0]["text"]
    bad = invalid_choice()
    bad["body"][0]["segments"][0]["text"] = prompt
    source = (*choice_source()[:1], DocxChunk("q1", "paragraph", prompt), *choice_source()[2:])
    converter, provider, leases, _, _ = ports()
    provider.complete_structured.return_value = response([bad], answer_key_anchors=["k1"])
    result = await convert(converter, source)
    assert provider.complete_structured.await_count == leases.reserve.await_count == 3
    assert [i.source_anchor for i in result.document.items] == ["h1", "q1", "c1"]
    assert [i.plain_text_lines() for i in result.document.items] == [(c.text,) for c in source[:3]]
    assert all(i.kind is NativeExamItemKind.FREE_TEXT for i in result.document.items)
    assert all(
        i.review.state is NativeItemReviewState.REVIEW_REQUIRED for i in result.document.items
    )
    assert all(
        i.review.reasons[0].startswith("Frågan följer inte provformatet (")
        for i in result.document.items
    )
    failures = [e for e in result.events if e.code == "native_contract_invalid"]
    assert [e.round for e in failures] == [1, 2, 3]
    assert {e.code for e in result.events} == {
        "native_contract_invalid",
        "retries_exhausted",
        "review_item",
    }
    assert len([e for e in result.events if e.code == "review_item"]) == 3
    assert all(prompt not in event.detail for event in result.events)


async def test_model_review_is_final_and_preserves_source_text_and_reason():
    converter, provider, _, _, _ = ports()
    provider.complete_structured.return_value = response(
        [choice_item(outcome="review", review_reason="Alternativen är otydliga.")],
        answer_key_anchors=["k1"],
    )
    result = await convert(converter)
    assert provider.complete_structured.await_count == 1
    assert [i.plain_text_lines() for i in result.document.items] == [
        (c.text,) for c in choice_source()[:3]
    ]
    assert all(
        i.review.state is NativeItemReviewState.REVIEW_REQUIRED for i in result.document.items
    )
    assert all(
        i.review.reasons
        == ("AI-tolkningen markerade frågan för granskning: Alternativen är otydliga.",)
        for i in result.document.items
    )
    assert [e.code for e in result.events] == ["model_review"]


@pytest.mark.parametrize(
    "cause,code",
    [
        ("unknown", "anchor_unknown"),
        ("duplicate", "anchor_conflict"),
        ("answer_key", "anchor_conflict"),
    ],
)
async def test_anchor_bookkeeping_rejects_unknown_reused_and_answer_key_anchors(cause, code):
    converter, provider, _, _, _ = ports()
    if cause == "unknown":
        entries = [choice_item(source_anchors=["h1", "q1", "c1", "unknown"])]
        rejected_index = 0
    elif cause == "duplicate":
        entries = [choice_item(), choice_item()]
        rejected_index = 1
    else:
        entries = [choice_item(source_anchors=["h1", "q1", "c1", "k1"])]
        rejected_index = 0
    provider.complete_structured.return_value = response(entries, answer_key_anchors=["k1"])
    result = await convert(converter)
    failure = next(e for e in result.events if e.code == code)
    assert failure.round == 1
    assert failure.item == rejected_index
    if cause == "duplicate":
        assert provider.complete_structured.await_count == 1
        assert len(result.document.items) == 1
        assert result.document.items[0].review.state is NativeItemReviewState.REVIEW_COMPLETE
    else:
        assert provider.complete_structured.await_count == 3
        assert all(
            i.review.state is NativeItemReviewState.REVIEW_REQUIRED for i in result.document.items
        )


@pytest.mark.parametrize("field", ["title", "instructions", "answer_key_anchors", "items"])
async def test_missing_envelope_field_retries_all_pending_chunks(field):
    converter, provider, _, _, _ = ports()
    malformed = response([choice_item()], answer_key_anchors=["k1"])
    del malformed.content[field]
    provider.complete_structured.side_effect = [
        malformed,
        response([choice_item()], answer_key_anchors=["k1"]),
    ]
    result = await convert(converter)
    assert provider.complete_structured.await_count == 2
    calls = provider.complete_structured.call_args_list
    initial = json.loads(calls[0].kwargs["request"].user_payload)
    retry = json.loads(calls[1].kwargs["request"].user_payload)
    assert retry["chunks"] == initial["chunks"]
    assert retry["answer_key_chunks"] == []
    assert "envelope_invalid" in retry["validation_errors"][0]
    assert [e.code for e in result.events] == ["envelope_invalid"]
    assert len(result.document.items) == 1
    assert result.document.items[0].review.state is NativeItemReviewState.REVIEW_COMPLETE


async def test_unclaimed_chunk_retries_three_times_then_keeps_explicit_review_reason():
    converter, provider, _, _, _ = ports()
    provider.complete_structured.return_value = response([])
    chunk = DocxChunk("table", "table", "Unparsed table")
    result = await convert(converter, (chunk,))
    assert provider.complete_structured.await_count == 3
    for call in provider.complete_structured.call_args_list:
        payload = json.loads(call.kwargs["request"].user_payload)
        assert [c["anchor"] for c in payload["chunks"]] == ["table"]
    assert [e.round for e in result.events if e.code == "chunk_unclaimed"] == [1, 2, 3]
    assert all(e.anchors == ("table",) for e in result.events if e.code == "chunk_unclaimed")
    (item,) = result.document.items
    assert item.plain_text_lines() == (chunk.text,)
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.review.reasons == ("AI-tolkningen gav ingen fråga eller rubrik för källstycket.",)


@pytest.mark.parametrize(
    "cause,code,reason,detail",
    [
        ("disabled", "ai_disabled", "avstängd", "avstängd"),
        ("lease", "lease_refused", "AI-budget är förbrukad", "requested"),
        ("http", "provider_http_error", "provider_http_error", "status=500"),
        ("unavailable", "provider_unavailable", "inte tillgänglig", "RuntimeError"),
    ],
)
async def test_fallback_opens_document_and_names_failure_for_every_chunk(
    cause, code, reason, detail
):
    converter, provider, leases, _, _ = ports(enabled=cause != "disabled")
    if cause == "lease":
        leases.reserve.side_effect = refuse_lease(
            usage=AnswerKeyTokenLeaseDayUsage(_NOW.date(), 10, 10), requested_tokens=20000
        )
    elif cause == "http":
        provider.complete_structured.side_effect = StructuredLLMProviderError(
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR,
            message="failure",
            provider_id="primary",
            status_code=500,
        )
    elif cause == "unavailable":
        provider.complete_structured.side_effect = RuntimeError("unavailable")
    result = await convert(converter)
    assert result.document.revision == 1
    assert [i.plain_text_lines() for i in result.document.items] == [
        (c.text,) for c in choice_source()
    ]
    assert all(i.kind is NativeExamItemKind.FREE_TEXT for i in result.document.items)
    assert all(
        i.review.state is NativeItemReviewState.REVIEW_REQUIRED for i in result.document.items
    )
    assert all(reason in i.review.reasons[0] for i in result.document.items)
    failure = next(e for e in result.events if e.code == code)
    assert detail in failure.detail
    assert result.input_tokens is result.output_tokens is None
    leases.reconcile.assert_not_awaited()
    assert provider.complete_structured.await_count == (
        1 if cause in {"http", "unavailable"} else 0
    )


async def test_incomplete_response_is_not_admitted_or_reconciled():
    converter, provider, leases, _, _ = ports()
    provider.complete_structured.return_value = response(
        [choice_item()], answer_key_anchors=["k1"], finish="incomplete"
    )
    result = await convert(converter)
    assert provider.complete_structured.await_count == 1
    assert all(
        i.review.state is NativeItemReviewState.REVIEW_REQUIRED for i in result.document.items
    )
    assert len(result.document.items) == len(choice_source())
    leases.reconcile.assert_not_awaited()
    assert (
        next(e for e in result.events if e.code == "response_incomplete").detail
        == "status=incomplete"
    )


@pytest.mark.parametrize(
    "usage,expected",
    [
        (StructuredLLMUsage(), (None, None)),
        (StructuredLLMUsage(prompt_tokens=100), (100, None)),
        (StructuredLLMUsage(completion_tokens=50), (None, 50)),
    ],
)
async def test_missing_usage_never_reports_estimates_as_measured_tokens(usage, expected):
    converter, provider, leases, _, _ = ports()
    provider.complete_structured.return_value = response(
        [choice_item()], answer_key_anchors=["k1"], usage=usage
    )
    result = await convert(converter)
    assert (result.input_tokens, result.output_tokens) == expected
    leases.reconcile.assert_not_awaited()
    leases.reserve.assert_awaited_once()
    assert result.document.items[0].review.state is NativeItemReviewState.REVIEW_COMPLETE


async def test_wrong_endpoint_never_calls_provider_or_reserves_lease():
    converter, provider, leases, _, selector = ports()
    route = selector.select_route.return_value
    selector.select_route.return_value = AnswerKeyProviderRoute(route.failover, route.primary)
    result = await convert(converter)
    assert all(
        i.review.state is NativeItemReviewState.REVIEW_REQUIRED for i in result.document.items
    )
    assert any(e.code == "responses_profile_unavailable" for e in result.events)
    provider.complete_structured.assert_not_awaited()
    leases.reserve.assert_not_awaited()


async def test_metadata_is_admitted_and_answer_key_chunks_are_teacher_notes_only():
    converter, provider, _, _, _ = ports()
    source = (
        DocxChunk("title", "heading", "Colour test"),
        DocxChunk("instructions", "paragraph", "Select one answer."),
        *choice_source(),
    )
    provider.complete_structured.return_value = response(
        [choice_item()],
        answer_key_anchors=["k1"],
        title={"text": "Colour test", "source_anchors": ["title"]},
        instructions=[{"text": "Select one answer.", "source_anchors": ["instructions"]}],
    )
    result = await convert(converter, source)
    assert provider.complete_structured.await_count == 1
    assert result.document.title == "Colour test"
    assert result.document.instructions == ("Select one answer.",)
    assert len(result.document.items) == 1
    assert result.document.items[0].source_anchor == "h1"
    facit = choice_source()[-1].text
    assert result.notes == (facit,)
    assert result.events == ()
    assert native_export_blockers(result.document) == ()
    package, report = build_native_examnet_qti_package(
        result.document, package_name="probe", qti_writer=ExamNetQtiPackageWriter()
    )
    assert json.loads(report)["package_status"] == "passed"
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        assert not [name for name in archive.namelist() if facit.encode() in archive.read(name)]


async def test_recorded_quiz_two_rounds_builds_all_items_and_exports_qti():
    from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
        exam_workspace_docx_chunker,
    )

    fixture = Path("tests/fixtures/exam_conversion")
    chunks = exam_workspace_docx_chunker.PythonDocxExamChunker().chunk(
        content=(
            fixture / "docx_corpus/chapter_4_poetry_and_lyrics_quiz_med_facit.docx"
        ).read_bytes()
    )
    converter, provider, _, _, _ = ports()
    provider.complete_structured.side_effect = [
        StructuredLLMResponse(
            json.loads((fixture / name).read_text()),
            "completed",
            StructuredLLMUsage(900, 800, 1700),
        )
        for name in [
            "chapter_4_poetry_docx_build_response.json",
            "chapter_4_poetry_docx_build_retry_response.json",
        ]
    ]
    result = await convert(converter, chunks)
    assert provider.complete_structured.await_count == 2
    assert len(result.document.items) == 28
    assert sum(item.points for item in result.document.items) == 28
    assert [item.kind.value for item in result.document.items] == ["single_choice"] * 21 + [
        "gap_fill"
    ] * 7
    assert all(
        i.review.state is NativeItemReviewState.REVIEW_COMPLETE for i in result.document.items
    )
    assert [(e.code, e.round, e.anchors) for e in result.events] == [
        ("chunk_unclaimed", 1, ("body:0003",))
    ]
    assert native_export_blockers(result.document) == ()
    package, report = build_native_examnet_qti_package(
        result.document, package_name="probe", qti_writer=ExamNetQtiPackageWriter()
    )
    assert json.loads(report)["package_status"] == "passed"
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        assert "imsmanifest.xml" in archive.namelist()
