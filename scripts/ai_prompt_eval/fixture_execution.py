"""Run one prompt-eval fixture against the live backend and describe the result."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx

from scripts.ai_prompt_eval.fixture_bank import PromptEvalFixture
from scripts.ai_prompt_eval.fixture_requests import build_request
from scripts.ai_prompt_eval.interpretation import (
    EvalMeta,
    parse_error_meta,
    read_eval_meta_headers,
    read_outcome,
    summarize_body,
)
from skriptoteket.protocols.llm import PromptEvalOutcome


@dataclass(frozen=True)
class CaseResult:
    fixture: PromptEvalFixture
    http_status: int | None
    enabled: bool | None
    response_chars: int | None
    latency_ms: int
    outcome: PromptEvalOutcome
    meta: EvalMeta = field(default_factory=EvalMeta)
    error_kind: str | None = None
    error_meta: dict[str, object] = field(default_factory=dict)

    @property
    def unexpected_outcome(self) -> bool:
        allowed = self.fixture.allowed_outcomes
        return allowed is not None and self.outcome not in allowed


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _answered(
    *, fixture: PromptEvalFixture, response: httpx.Response, latency_ms: int
) -> CaseResult:
    meta = read_eval_meta_headers(response.headers)
    enabled: bool | None = None
    response_chars: int | None = None
    error_kind: str | None = None
    error_meta: dict[str, object] = {}

    if response.status_code != 200:
        error_kind = "http_status"
        error_meta = parse_error_meta(response)
    else:
        summary = summarize_body(fixture=fixture, response=response)
        if summary is None:
            error_kind = "invalid_response"
        else:
            enabled = summary.enabled
            response_chars = summary.output_chars

    return CaseResult(
        fixture=fixture,
        http_status=response.status_code,
        enabled=enabled,
        response_chars=response_chars,
        latency_ms=latency_ms,
        outcome=read_outcome(
            meta=meta, response_chars=response_chars or 0, status_code=response.status_code
        ),
        meta=meta,
        error_kind=error_kind,
        error_meta=error_meta,
    )


def execute_fixture(
    *, client: httpx.Client, fixture: PromptEvalFixture, headers: dict[str, str]
) -> CaseResult:
    request = build_request(fixture)
    start = time.perf_counter()
    try:
        response = client.post(
            request.path,
            content=request.json_body,
            headers={**headers, "Content-Type": "application/json"},
        )
    except httpx.TimeoutException:
        return CaseResult(
            fixture=fixture,
            http_status=None,
            enabled=None,
            response_chars=None,
            latency_ms=_elapsed_ms(start),
            outcome="timeout",
            error_kind="timeout",
        )
    except httpx.RequestError:
        return CaseResult(
            fixture=fixture,
            http_status=None,
            enabled=None,
            response_chars=None,
            latency_ms=_elapsed_ms(start),
            outcome="error",
            error_kind="request_error",
        )
    return _answered(fixture=fixture, response=response, latency_ms=_elapsed_ms(start))
