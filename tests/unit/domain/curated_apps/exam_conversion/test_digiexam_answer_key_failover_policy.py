"""Failover eligibility rules for answer-key provider errors.

Purpose:
    Pin the sircon D12 failover gate: only transient outages (timeout,
    pre-response failure, HTTP 408/5xx) may trigger the single failover
    attempt; every other provider failure is terminal, and a route must
    pair two distinct provider profiles.
"""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    AnswerKeyProviderRoute,
    StructuredLLMBackendFailureCode,
    StructuredLLMEndpointKind,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    allows_answer_key_provider_failover,
)

pytestmark = pytest.mark.unit


def _error(
    failure_code: StructuredLLMBackendFailureCode,
    *,
    status_code: int | None = None,
) -> StructuredLLMProviderError:
    return StructuredLLMProviderError(
        failure_code=failure_code,
        message="test failure",
        provider_id="openai-gpt-5.6-luna",
        status_code=status_code,
    )


def _profile(provider_id: str) -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id=provider_id,
        model="test-model",
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        is_remote=True,
        context_window_tokens=32_768,
        max_output_tokens=4_096,
    )


@pytest.mark.parametrize(
    "error",
    [
        _error(StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT),
        _error(StructuredLLMBackendFailureCode.PROVIDER_REQUEST_FAILED),
        _error(StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR, status_code=408),
        _error(StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR, status_code=500),
        _error(StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR, status_code=599),
    ],
)
def test_transient_outages_allow_failover(error: StructuredLLMProviderError) -> None:
    assert allows_answer_key_provider_failover(error) is True


@pytest.mark.parametrize(
    "error",
    [
        _error(StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR, status_code=400),
        _error(StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR, status_code=429),
        _error(StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR, status_code=None),
        _error(StructuredLLMBackendFailureCode.PROVIDER_CONFIG_MISSING),
        _error(StructuredLLMBackendFailureCode.PROVIDER_INVALID_JSON),
        _error(StructuredLLMBackendFailureCode.PROVIDER_RESPONSE_NOT_OBJECT),
        _error(StructuredLLMBackendFailureCode.PROVIDER_EMPTY_CONTENT),
        _error(StructuredLLMBackendFailureCode.PROVIDER_CONTENT_NOT_JSON),
        _error(StructuredLLMBackendFailureCode.PROVIDER_SCHEMA_MISMATCH),
        _error(StructuredLLMBackendFailureCode.PROVIDER_REFUSAL),
    ],
)
def test_non_transient_failures_never_allow_failover(error: StructuredLLMProviderError) -> None:
    assert allows_answer_key_provider_failover(error) is False


def test_route_requires_distinct_provider_profiles() -> None:
    with pytest.raises(ValueError, match="must differ"):
        AnswerKeyProviderRoute(primary=_profile("same-id"), failover=_profile("same-id"))


def test_route_holds_the_ordered_profiles() -> None:
    route = AnswerKeyProviderRoute(primary=_profile("primary"), failover=_profile("backup"))
    assert route.primary.provider_id == "primary"
    assert route.failover.provider_id == "backup"
