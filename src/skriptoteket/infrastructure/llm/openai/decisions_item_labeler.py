"""httpx OpenAI Decisions adapter for item-type labeling (TASK-SKRIPT-39-05-04).

Purpose:
    Ask one ``choice`` question per item on ``POST /v1/decisions`` and route
    each answer through the label thresholds. Requests hold at most 200
    questions; larger inputs split into concurrent requests that each carry
    only their own items. Every escalated question is then re-asked alone
    with its own context (second pass, D16), all such questions
    concurrently. 503 and 504 retry with bounded backoff.

Relationships:
    Implements ``protocols.item_type_labeler.MeteredItemTypeLabelerProtocol``.
    Label descriptions define gap and free text by how the answer is scored
    (D15), and each question retains its source text and inline keys
    (amended D14); a new measurement is required after the input repair and
    a rewording invalidates that measurement. Request and answer shapes follow
    the official Decisions guide (developers.openai.com/api/docs/guides/decisions,
    read 2026-10-11) and the recorded responses.
"""

from __future__ import annotations

import asyncio
import json
import math
from collections.abc import Coroutine, Iterable, Sequence
from dataclasses import replace

import httpx
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    estimate_prompt_tokens,
)
from skriptoteket.protocols.item_type_labeler import (
    ACCEPT_THRESHOLD,
    ItemTypeLabel,
    ItemTypeLabelerError,
    ItemTypeLabeling,
    ItemTypeLabelResult,
    LabelingItem,
    LabelingRequest,
    LabelingUsage,
    LabelRoute,
    MeteredItemTypeLabelerProtocol,
    label_route,
)
from skriptoteket.protocols.sleeper import SleeperProtocol

_JsonObject = dict[str, JsonValue]
_ChunkOutcome = tuple[list[ItemTypeLabelResult], int | None, int]

DECISIONS_MODEL = "gpt-6-luna"
MAX_QUESTIONS_PER_REQUEST = 200  # The API answers 400 array_above_max_length above 200.
RETRYABLE_STATUS_CODES = frozenset({503, 504})

CLASSIFICATION_INSTRUCTION = (
    "Classify the response action the student performs and how that response is scored. "
    "Read the target question's student view, answer key, governing instruction and section "
    "heading together. For single_choice the student selects exactly one printed option; "
    "for multiple_response the student selects several. For gap_fill each response slot is "
    "checked against one or more accepted strings, including a whole sentence or a word "
    "from a supplied bank. For free_text the teacher judges a written response using a "
    "sample answer, analysis or grading guidance rather than exact accepted strings for "
    "each slot. Response length alone does not distinguish these labels. Matching pairs "
    "entries from two supplied sets. Unsupported means the required interaction falls "
    "outside those supported types; unresolved means the source does not establish a "
    "reliable choice."
)

LABEL_DESCRIPTIONS: dict[ItemTypeLabel, str] = {
    ItemTypeLabel.SINGLE_CHOICE: "The student chooses exactly one of the listed options.",
    ItemTypeLabel.MULTIPLE_RESPONSE: (
        "The student chooses several of the listed options, "
        "as the question's response instruction asks."
    ),
    ItemTypeLabel.GAP_FILL: (
        "Each response slot (a blank, a blank line or a labelled field) is keyed by one or "
        "more accepted strings of any length, including slots filled from a word bank or "
        "label list."
    ),
    ItemTypeLabel.FREE_TEXT: (
        "The student writes a response whose key is a sample answer, an analysis or "
        "grading guidance."
    ),
    ItemTypeLabel.MATCHING: (
        "The student pairs entries of one supplied set with entries of another supplied set."
    ),
    ItemTypeLabel.UNSUPPORTED: (
        "The required interaction cannot be represented by any kind above without changing "
        "how the student answers."
    ),
    ItemTypeLabel.UNRESOLVED: (
        "The source is insufficient or contradictory for a reliable choice."
    ),
}


class OpenAIDecisionsItemTypeLabeler(MeteredItemTypeLabelerProtocol):
    """Async Decisions adapter; holds no lease and logs no request content."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        base_url: str,
        api_key: str,
        timeout_seconds: float,
        sleeper: SleeperProtocol,
        max_attempts: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 8.0,
    ) -> None:
        if not base_url.strip():
            raise ValueError("Decisions labeler base_url must be non-empty.")
        if timeout_seconds <= 0:
            raise ValueError("Decisions labeler timeout_seconds must be positive.")
        if max_attempts < 1:
            raise ValueError("Decisions labeler max_attempts must be at least 1.")
        self._client = client
        self._base_url = base_url.strip().rstrip("/")
        self._api_key = api_key.strip()
        self._timeout_seconds = timeout_seconds
        self._sleeper = sleeper
        self._max_attempts = max_attempts
        self._base_delay_seconds = base_delay_seconds
        self._max_delay_seconds = max_delay_seconds

    @property
    def provider_profile_id(self) -> str:
        return f"openai-decisions-{DECISIONS_MODEL}"

    def estimate_input_tokens(self, *, request: LabelingRequest) -> int:
        """First-pass requests plus one possible single-question call for every item."""

        first = sum(
            estimate_prompt_tokens(json.dumps(build_decisions_payload(chunk)))
            for chunk in split_items(request.items)
        )
        return first + sum(
            estimate_prompt_tokens(json.dumps(build_second_pass_payload(item)))
            for item in request.items
        )

    async def label(self, *, request: LabelingRequest) -> ItemTypeLabeling:
        if not request.items:
            return ItemTypeLabeling(results=())
        if not self._api_key:
            raise ItemTypeLabelerError(
                code="config_missing", message="Decisions labeler API key is not configured."
            )
        first = await self._gather(
            self._label_chunk(build_decisions_payload(chunk), chunk)
            for chunk in split_items(request.items)
        )
        results = [result for outcome in first for result in outcome[0]]
        again = [
            (index, item)
            for index, (item, result) in enumerate(zip(request.items, results, strict=True))
            if result.route is LabelRoute.ESCALATE
        ]
        second = await self._gather(
            self._label_chunk(build_second_pass_payload(item), (item,)) for _, item in again
        )
        for (index, _), (relabeled, _, _) in zip(again, second, strict=True):
            results[index] = replace(relabeled[0], first_pass=results[index])
        outcomes = first + second
        tokens = [outcome[1] for outcome in outcomes]
        return ItemTypeLabeling(
            results=tuple(results),
            usage=LabelingUsage(
                input_tokens=None if None in tokens else sum(t or 0 for t in tokens),
                requests=len(outcomes),
                attempts=sum(outcome[2] for outcome in outcomes),
            ),
        )

    @staticmethod
    async def _gather(
        calls: Iterable[Coroutine[None, None, _ChunkOutcome]],
    ) -> list[_ChunkOutcome]:
        """Run every call to completion, then raise the first failure in call order."""

        outcomes = await asyncio.gather(*calls, return_exceptions=True)
        for outcome in outcomes:
            if isinstance(outcome, BaseException):
                raise outcome
        return [outcome for outcome in outcomes if not isinstance(outcome, BaseException)]

    async def _label_chunk(
        self, payload: _JsonObject, items: Sequence[LabelingItem]
    ) -> _ChunkOutcome:
        body, attempts = await self._post(payload)
        results, input_tokens = parse_decisions_answers(body, items)
        return results, input_tokens, attempts

    async def _post(self, payload: _JsonObject) -> tuple[JsonValue, int]:
        attempt = 0
        while True:
            attempt += 1
            response = await self._send(payload)
            if response.status_code in RETRYABLE_STATUS_CODES and attempt < self._max_attempts:
                await self._sleeper.sleep(self._retry_delay(response, attempt))
                continue
            if response.status_code in RETRYABLE_STATUS_CODES:
                raise ItemTypeLabelerError(
                    code="provider_unavailable",
                    message=f"Decisions stayed unavailable after {attempt} attempts.",
                    status_code=response.status_code,
                )
            if response.status_code != 200:
                raise ItemTypeLabelerError(
                    code="http_error",
                    message="Decisions returned an unsuccessful HTTP status.",
                    status_code=response.status_code,
                )
            try:
                return response.json(), attempt
            except ValueError as exc:
                raise ItemTypeLabelerError(
                    code="invalid_json", message="Decisions response body was not valid JSON."
                ) from exc

    async def _send(self, payload: _JsonObject) -> httpx.Response:
        try:
            return await self._client.post(
                f"{self._normalized_base_url}/decisions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
                timeout=self._timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise ItemTypeLabelerError(
                code="timeout", message="Decisions request timed out."
            ) from exc
        except httpx.RequestError as exc:
            raise ItemTypeLabelerError(
                code="request_failed",
                message="Decisions request failed before a response was received.",
            ) from exc

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        """Exponential backoff, or the server's retry-after, never above the cap."""

        delay = self._base_delay_seconds * 2 ** (attempt - 1)
        retry_after = response.headers.get("retry-after")
        if retry_after is not None:
            try:
                parsed = float(retry_after)
            except ValueError:
                parsed = math.nan
            if math.isfinite(parsed) and parsed >= 0:
                delay = parsed
        return float(min(delay, self._max_delay_seconds))

    @property
    def _normalized_base_url(self) -> str:
        if self._base_url.endswith("/v1"):
            return self._base_url
        return f"{self._base_url}/v1"


def split_items(items: Sequence[LabelingItem]) -> list[Sequence[LabelingItem]]:
    return [
        items[start : start + MAX_QUESTIONS_PER_REQUEST]
        for start in range(0, len(items), MAX_QUESTIONS_PER_REQUEST)
    ]


def _question_id(index: int) -> str:
    return f"q{index + 1}"


def render_items(items: Sequence[LabelingItem]) -> str:
    """Send each question's faithful source text under a routing heading, nothing else."""

    blocks = [CLASSIFICATION_INSTRUCTION]
    blocks.extend(
        f"### Question {_question_id(index)}\n{item.source_text}"
        for index, item in enumerate(items)
    )
    return "\n\n".join(blocks)


def _payload(rendered: str, count: int) -> _JsonObject:
    choices: list[JsonValue] = [
        {"value": label.value, "description": LABEL_DESCRIPTIONS[label]} for label in ItemTypeLabel
    ]
    questions: list[JsonValue] = [
        {
            "type": "choice",
            "name": f"kind_{_question_id(index)}",
            "instructions": (
                f"Which response action does question {_question_id(index)} ask the student "
                "to perform, and how is that answer scored?"
            ),
            "choices": choices,
        }
        for index in range(count)
    ]
    return {"model": DECISIONS_MODEL, "input": rendered, "questions": questions}


def build_decisions_payload(items: Sequence[LabelingItem]) -> _JsonObject:
    return _payload(render_items(items), len(items))


def build_second_pass_payload(item: LabelingItem) -> _JsonObject:
    """Re-ask one escalated question alone with its own source text."""

    return _payload(render_items((item,)), 1)


def parse_decisions_answers(
    body: JsonValue, items: Sequence[LabelingItem]
) -> tuple[list[ItemTypeLabelResult], int | None]:
    """Map answers back to items by name; any missing, extra or unknown answer fails the request."""

    listed = body.get("answers") if isinstance(body, dict) else None
    if not isinstance(body, dict) or not isinstance(listed, list):
        raise _malformed("Decisions response has no answers list.")
    answers: dict[str, _JsonObject] = {}
    for answer in listed:
        if not isinstance(answer, dict) or not isinstance(answer.get("name"), str):
            raise _malformed("Decisions answer has no name.")
        name = str(answer["name"])
        if name in answers:
            raise _malformed(f"Decisions answered {name} twice.")
        answers[name] = answer
    expected = {f"kind_{_question_id(index)}": item for index, item in enumerate(items)}
    if set(answers) != set(expected):
        raise _malformed("Decisions answers do not match the questions asked.")
    results = [_result(item, answers[name]) for name, item in expected.items()]
    return results, _input_tokens(body)


def _result(item: LabelingItem, answer: _JsonObject) -> ItemTypeLabelResult:
    if answer.get("type") == "refusal":
        return ItemTypeLabelResult(
            item_id=item.item_id,
            label=ItemTypeLabel.UNRESOLVED,
            probabilities={},
            probability=0.0,
            threshold=ACCEPT_THRESHOLD,
            route=LabelRoute.ESCALATE,
            refused=True,
        )
    if answer.get("type") != "choice":
        raise _malformed("Decisions answer is neither a choice nor a refusal.")
    label = _known_label(answer.get("choice"))
    probabilities = _probabilities(answer.get("probabilities"))
    probability = probabilities[label]
    return ItemTypeLabelResult(
        item_id=item.item_id,
        label=label,
        probabilities=probabilities,
        probability=probability,
        threshold=ACCEPT_THRESHOLD,
        route=label_route(probability),
    )


_LABELS_BY_VALUE = {label.value: label for label in ItemTypeLabel}


def _known_label(value: JsonValue | None) -> ItemTypeLabel:
    label = _LABELS_BY_VALUE.get(value) if isinstance(value, str) else None
    if label is None:
        raise ItemTypeLabelerError(
            code="unknown_label", message="Decisions returned a label outside the closed set."
        )
    return label


def _probabilities(value: JsonValue | None) -> dict[ItemTypeLabel, float]:
    if not isinstance(value, list) or not value:
        raise _malformed("Decisions choice answer has no probabilities.")
    probabilities = dict.fromkeys(ItemTypeLabel, 0.0)
    for entry in value:
        if not isinstance(entry, dict):
            raise _malformed("Decisions probability entry is not an object.")
        label = _known_label(entry.get("value"))
        probability = entry.get("probability")
        if (
            isinstance(probability, bool)
            or not isinstance(probability, int | float)
            or not 0.0 <= probability <= 1.0
        ):
            raise _malformed("Decisions probability is not a number in [0, 1].")
        probabilities[label] = float(probability)
    return probabilities


def _input_tokens(body: _JsonObject) -> int | None:
    usage = body.get("usage")
    tokens = usage.get("input_tokens") if isinstance(usage, dict) else None
    return tokens if isinstance(tokens, int) and not isinstance(tokens, bool) else None


def _malformed(message: str) -> ItemTypeLabelerError:
    return ItemTypeLabelerError(code="malformed_response", message=message)
