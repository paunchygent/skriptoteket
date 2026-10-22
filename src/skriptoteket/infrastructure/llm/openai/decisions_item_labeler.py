"""Door-backed OpenAI Decisions adapter for item-type labeling (TASK-SKRIPT-41-01-03).

Purpose:
    Ask one ``choice`` question per item on ``POST /v1/decisions`` and route
    each answer through the label thresholds. Requests hold at most 200
    questions; larger inputs split into concurrent requests that each carry
    only their own items. This is the batched first pass; an escalated
    question is decided by the Responses second pass (D23). 503 and 504
    retry with bounded backoff.

Relationships:
    Implements ``protocols.item_type_labeler.MeteredItemTypeLabelerProtocol``.
    Label descriptions define gap and free text by how the answer is scored
    (D15), generated from the one definition in ``item_kind_boundary`` that also
    generates the converter's kind rule (TASK-SKRIPT-39-05-08); the instruction
    and descriptions are sent in both passes
    (D23), and each question retains its source text and inline keys
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

from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    IMAGE_INPUT_TOKEN_ESTIMATE,
    SourceImage,
    estimate_prompt_tokens,
    input_content,
)
from skriptoteket.domain.curated_apps.exam_workspace.item_kind_boundary import (
    FREE_TEXT_DEFINITION,
    GAP_FILL_DEFINITION,
    labeler_boundary_sentences,
)
from skriptoteket.domain.llm_door import AiDoorBusy, AiDoorCaller
from skriptoteket.infrastructure.llm.openai.decisions_content_tags import (
    build_content_decisions_payload,
    parse_content_decisions_answers,
)
from skriptoteket.protocols.item_type_labeler import (
    ACCEPT_THRESHOLD,
    ContentTagChoice,
    ContentTagClassification,
    ContentTagClassificationRequest,
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
from skriptoteket.protocols.llm_door import (
    DoorOperation,
    DoorReply,
    DoorRequestFailed,
    DoorTimeout,
    LlmDoorClientProtocol,
)
from skriptoteket.protocols.sleeper import SleeperProtocol

_JsonObject = dict[str, JsonValue]
_ChunkOutcome = tuple[list[ItemTypeLabelResult], int | None, int]

DECISIONS_MODEL = "gpt-6-luna"
MAX_QUESTIONS_PER_REQUEST = 200  # The API answers 400 array_above_max_length above 200.
RETRYABLE_STATUS_CODES = frozenset({503, 504})

CLASSIFICATION_INSTRUCTION = (
    "Classify the response action the student performs and how that response is scored. "
    "Read the question as the teacher wrote it, including its instructions, inline answers "
    "and key labels. A type name the teacher writes for the question, as listed under each "
    "label, settles the label, and a key that marks more than one option as correct settles "
    "multiple_response. For single_choice the student selects exactly one printed option; "
    "for multiple_response the student selects several. "
    f"{labeler_boundary_sentences()} Matching pairs "
    "entries from two supplied sets. Unsupported means the required interaction falls "
    "outside those supported types; unresolved means the source does not establish a "
    "reliable choice."
)

# Flervalsfråga names both choice labels; the number of options to choose decides (D23).
_MULTIPLE_CHOICE_NAME = (
    "Flervalsfråga (multiple choice) names both single_choice and multiple_response; "
    "the number of options the student must choose decides between them."
)

LABEL_DESCRIPTIONS: dict[ItemTypeLabel, str] = {
    ItemTypeLabel.SINGLE_CHOICE: (
        "The student chooses exactly one of the listed options, also when asked to write "
        "the option's letter or number. Type names: välj ett alternativ (choose one option), "
        "ett rätt svar (one correct answer), sant eller falskt / rätt eller fel (true or "
        f"false). {_MULTIPLE_CHOICE_NAME}"
    ),
    ItemTypeLabel.MULTIPLE_RESPONSE: (
        "The student chooses several of the listed options, as the question's response "
        "instruction asks. Type names: flera rätt (more than one correct), välj alla som "
        "stämmer (select all that apply). A key that marks more than one option as correct "
        f"settles this label. {_MULTIPLE_CHOICE_NAME}"
    ),
    ItemTypeLabel.GAP_FILL: (
        f"{GAP_FILL_DEFINITION} Type names: lucktext (gap text, cloze), "
        "fyll i luckan / luckorna (fill in the gap / gaps)."
    ),
    ItemTypeLabel.FREE_TEXT: (
        f"{FREE_TEXT_DEFINITION} Type names: fritt svar (open answer), öppen fråga (open question)."
    ),
    ItemTypeLabel.MATCHING: (
        "The student pairs entries of one supplied set with entries of another supplied set. "
        "Type names: para ihop (pair up), matchning (matching)."
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
    """Decisions adapter through the provider door; holds no key and logs no content."""

    def __init__(
        self,
        *,
        door: LlmDoorClientProtocol,
        timeout_seconds: float,
        sleeper: SleeperProtocol,
        max_attempts: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 8.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Decisions labeler timeout_seconds must be positive.")
        if max_attempts < 1:
            raise ValueError("Decisions labeler max_attempts must be at least 1.")
        self._door = door
        self._timeout_seconds = timeout_seconds
        self._sleeper = sleeper
        self._max_attempts = max_attempts
        self._base_delay_seconds = base_delay_seconds
        self._max_delay_seconds = max_delay_seconds

    @property
    def provider_profile_id(self) -> str:
        return f"openai-decisions-{DECISIONS_MODEL}"

    def estimate_input_tokens(self, *, request: LabelingRequest) -> int:
        return sum(
            estimate_prompt_tokens(json.dumps(_payload(render_items(chunk), (), len(chunk))))
            + IMAGE_INPUT_TOKEN_ESTIMATE * sum(len(item.images) for item in chunk)
            for chunk in split_items(request.items)
        )

    async def label(self, *, request: LabelingRequest) -> ItemTypeLabeling:
        if not request.items:
            return ItemTypeLabeling(results=())
        outcomes = await _gather_chunks(
            self._label_chunk(build_decisions_payload(chunk), chunk, request.caller)
            for chunk in split_items(request.items)
        )
        results = [result for outcome in outcomes for result in outcome[0]]
        tokens = [outcome[1] for outcome in outcomes]
        return ItemTypeLabeling(
            results=tuple(results),
            usage=LabelingUsage(
                input_tokens=None if None in tokens else sum(t or 0 for t in tokens),
                requests=len(outcomes),
                attempts=sum(outcome[2] for outcome in outcomes),
            ),
        )

    def estimate_content_tokens(self, *, request: ContentTagClassificationRequest) -> int:
        total = 0
        for chunk in split_items(request.items):
            payload = build_content_decisions_payload(
                chunk, request.content_items, model=DECISIONS_MODEL
            )
            if any(item.images for item in chunk):
                text_only = tuple(LabelingItem(item.item_id, item.source_text) for item in chunk)
                payload = build_content_decisions_payload(
                    text_only, request.content_items, model=DECISIONS_MODEL
                )
            total += estimate_prompt_tokens(json.dumps(payload))
            total += IMAGE_INPUT_TOKEN_ESTIMATE * sum(len(item.images) for item in chunk)
        return total

    async def classify_content(
        self, *, request: ContentTagClassificationRequest
    ) -> ContentTagClassification:
        if not request.items or not request.content_items:
            return ContentTagClassification(results=())

        async def classify(
            chunk: Sequence[LabelingItem],
        ) -> tuple[list[ContentTagChoice], int | None, int]:
            body, attempts = await self._post(
                build_content_decisions_payload(
                    chunk, request.content_items, model=DECISIONS_MODEL
                ),
                request.caller,
            )
            results, tokens = parse_content_decisions_answers(body, chunk, request.content_items)
            return results, tokens, attempts

        outcomes = await _gather_chunks(classify(chunk) for chunk in split_items(request.items))
        tokens = [outcome[1] for outcome in outcomes]
        return ContentTagClassification(
            results=tuple(result for outcome in outcomes for result in outcome[0]),
            usage=LabelingUsage(
                input_tokens=None if None in tokens else sum(token or 0 for token in tokens),
                requests=len(outcomes),
                attempts=sum(outcome[2] for outcome in outcomes),
            ),
        )

    async def _label_chunk(
        self, payload: _JsonObject, items: Sequence[LabelingItem], caller: AiDoorCaller
    ) -> _ChunkOutcome:
        body, attempts = await self._post(payload, caller)
        results, input_tokens = parse_decisions_answers(body, items)
        return results, input_tokens, attempts

    async def _post(self, payload: _JsonObject, caller: AiDoorCaller) -> tuple[JsonValue, int]:
        attempt = 0
        while True:
            attempt += 1
            response = await self._send(payload, caller)
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
                return json.loads(response.body), attempt
            except ValueError as exc:
                raise ItemTypeLabelerError(
                    code="invalid_json", message="Decisions response body was not valid JSON."
                ) from exc

    async def _send(self, payload: _JsonObject, caller: AiDoorCaller) -> DoorReply:
        try:
            return await self._door.send(
                operation=DoorOperation.DECISIONS,
                payload=payload,
                caller=caller,
                timeout_seconds=self._timeout_seconds,
            )
        except DoorTimeout as exc:
            raise ItemTypeLabelerError(
                code="timeout", message="Decisions request timed out."
            ) from exc
        except DoorRequestFailed as exc:
            raise ItemTypeLabelerError(
                code="request_failed",
                message="Decisions request failed before a response was received.",
            ) from exc

    def _retry_delay(self, response: DoorReply, attempt: int) -> float:
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


async def _gather_chunks[T](calls: Iterable[Coroutine[None, None, T]]) -> list[T]:
    """Run chunk calls as tasks, results in call order.

    A busy door ends the action: the first ``AiDoorBusy`` cancels and joins the
    unfinished siblings and is raised. Any other failure lets every call run to
    completion (a daily limit is never cut short), then raises the first failure in
    call order. A cancelled caller cancels and joins every chunk before it unwinds.
    """

    tasks = [asyncio.ensure_future(call) for call in calls]
    pending = set(tasks)
    try:
        while pending:
            finished, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_EXCEPTION)
            busy = next(
                (
                    error
                    for task in tasks
                    if task in finished and not task.cancelled()
                    for error in [task.exception()]
                    if isinstance(error, AiDoorBusy)
                ),
                None,
            )
            if busy is not None:
                await _cancel_and_join(tasks)
                raise busy
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        await _cancel_and_join(tasks)
        raise
    for outcome in outcomes:
        if isinstance(outcome, BaseException):
            raise outcome
    return [outcome for outcome in outcomes if not isinstance(outcome, BaseException)]


async def _cancel_and_join[T](tasks: Sequence[asyncio.Task[T]]) -> None:
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


def split_items(items: Sequence[LabelingItem]) -> list[Sequence[LabelingItem]]:
    return [
        items[start : start + MAX_QUESTIONS_PER_REQUEST]
        for start in range(0, len(items), MAX_QUESTIONS_PER_REQUEST)
    ]


def _question_id(index: int) -> str:
    return f"q{index + 1}"


def layout_items(items: Sequence[LabelingItem]) -> tuple[str, tuple[SourceImage, ...]]:
    """Each question's faithful source under a routing heading, nothing else; each source
    image stands at its own place in the rendered text."""

    text = CLASSIFICATION_INSTRUCTION
    images: list[SourceImage] = []
    for index, item in enumerate(items):
        text += f"\n\n### Question {_question_id(index)}\n"
        images.extend(SourceImage(image.png, len(text) + image.offset) for image in item.images)
        text += item.source_text
    return text, tuple(images)


def render_items(items: Sequence[LabelingItem]) -> str:
    return layout_items(items)[0]


def _payload(rendered: str, images: tuple[SourceImage, ...], count: int) -> _JsonObject:
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
    source: JsonValue = (
        [{"role": "user", "content": input_content(rendered, images)}] if images else rendered
    )
    return {"model": DECISIONS_MODEL, "input": source, "questions": questions}


def build_decisions_payload(items: Sequence[LabelingItem]) -> _JsonObject:
    text, images = layout_items(items)
    return _payload(text, images, len(items))


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
