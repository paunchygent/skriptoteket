"""Recorded-response support shared by the Decisions item-labeler adapter tests.

The recordings hold historical first-pass outputs; ``replay`` serves them to the
current first-pass requests at the provider-door seam and rejects any other request.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import NotRequired, TypedDict
from uuid import uuid4

from pydantic import JsonValue, TypeAdapter

from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    OpenAIDecisionsItemTypeLabeler,
    build_decisions_payload,
    split_items,
)
from skriptoteket.protocols.item_type_labeler import LabelingItem, LabelingRequest
from tests.unit.llm_door_fakes import (
    DoorReply,
    DoorResponder,
    DoorSent,
    RecordingDoor,
    fixture_caller,
)

FIXTURES = Path("tests/fixtures/item_type_labeler")
CORPUS_24 = "corpus_exam_24_questions.json"
CORPUS_204 = "corpus_three_exams_204_questions.json"
ACCEPT_BOUNDARY = 0.95

Responder = DoorResponder


class Probability(TypedDict):
    value: str
    probability: float


class Answer(TypedDict):
    """A recorded Decisions answer; a refusal carries only its type and name."""

    type: str
    name: str
    choice: NotRequired[str]
    probabilities: NotRequired[list[Probability]]
    confidence: NotRequired[float]


class Usage(TypedDict):
    input_tokens: int


class Body(TypedDict):
    model: str
    answers: NotRequired[list[Answer]]
    usage: Usage


class Choice(TypedDict):
    value: str
    description: str


class Question(TypedDict):
    type: str
    name: str
    instructions: str
    choices: list[Choice]


class Sent(TypedDict):
    model: str
    input: str | list[JsonValue]
    questions: list[Question]


_SENT_ADAPTER = TypeAdapter(Sent)


def sent_payload(sent: DoorSent) -> Sent:
    """The recorded request, validated into the Decisions request shape."""

    return _SENT_ADAPTER.validate_python(sent.payload)


class Exchange(TypedDict):
    request: Sent
    status_code: int
    headers: dict[str, str]
    body: Body


class Item(TypedDict):
    item_id: str
    source_text: str


class Recording(TypedDict):
    items: list[Item]
    exchanges: list[Exchange]


class Unavailable(TypedDict):
    status_code: int
    headers: dict[str, str]
    body: JsonValue


def load(name: str) -> Recording:
    recording: Recording = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return recording


def request_for(fixture: Recording) -> LabelingRequest:
    return LabelingRequest(
        job_id=uuid4(),
        caller=fixture_caller(),
        items=tuple(
            LabelingItem(
                item_id=item["item_id"],
                source_text=item["source_text"],
            )
            for item in fixture["items"]
        ),
    )


def unavailable(status_code: int) -> Unavailable:
    path = FIXTURES / "decisions_unavailable_responses.json"
    responses: list[Unavailable] = json.loads(path.read_text(encoding="utf-8"))["responses"]
    return next(r for r in responses if r["status_code"] == status_code)


def recorded_door_reply(recording: Exchange | Unavailable) -> DoorReply:
    body = recording["body"]
    raw = body.encode("utf-8") if isinstance(body, str) else json.dumps(body).encode("utf-8")
    return DoorReply(
        status_code=recording["status_code"],
        headers=dict(recording["headers"]),
        body=raw,
    )


def chosen_probability(answer: Answer) -> float:
    by_value = {entry["value"]: entry["probability"] for entry in answer["probabilities"]}
    return float(by_value[answer["choice"]])


def escalated_answers(fixture: Recording) -> list[Answer]:
    """The recorded first-pass answers the label thresholds send to a second pass."""

    return [
        answer
        for exchange in fixture["exchanges"]
        for answer in exchange["body"]["answers"]
        if answer["type"] != "choice" or chosen_probability(answer) < ACCEPT_BOUNDARY
    ]


class RecordingSleeper:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def sleep(self, seconds: float) -> None:
        self.delays.append(seconds)


class Harness:
    def __init__(self, responder: DoorResponder) -> None:
        self.door = RecordingDoor(responder)
        self.sleeper = RecordingSleeper()

    @property
    def requests(self) -> list[Sent]:
        return [sent_payload(sent) for sent in self.door.sent]

    @property
    def sent(self) -> list[DoorSent]:
        return self.door.sent

    def labeler(
        self,
        *,
        max_attempts: int = 3,
    ) -> OpenAIDecisionsItemTypeLabeler:
        return OpenAIDecisionsItemTypeLabeler(
            door=self.door,
            timeout_seconds=30,
            sleeper=self.sleeper,
            max_attempts=max_attempts,
        )


def replay(exchanges: list[Exchange], *, fixture: Recording | None = None) -> DoorResponder:
    # Historical outputs exercise the current request/parser boundary only.
    # Their old request bodies are not evidence of requests made by this adapter.
    fixture = load(CORPUS_24) if fixture is None else fixture
    items = request_for(fixture).items
    first_pass: list[tuple[JsonValue, Exchange]] = []
    for chunk in split_items(items):
        exchange = next(
            exchange
            for exchange in exchanges
            if len(exchange["request"]["questions"]) == len(chunk)
        )
        first_pass.append((build_decisions_payload(chunk), exchange))

    def respond(sent: DoorSent) -> DoorReply:
        matches = [exchange for payload, exchange in first_pass if payload == sent.payload]
        assert len(matches) == 1, "unexpected current-source request"
        return recorded_door_reply(matches[0])

    return respond


def sequence(*responders: DoorResponder) -> DoorResponder:
    remaining = list(responders)

    def respond(sent: DoorSent) -> DoorReply | Awaitable[DoorReply]:
        current = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        return current(sent)

    return respond


def always(recording: Exchange | Unavailable, status_code: int | None = None) -> DoorResponder:
    status = status_code if status_code is not None else recording["status_code"]
    body = recording["body"]
    raw = body.encode("utf-8") if isinstance(body, str) else json.dumps(body).encode("utf-8")
    reply = DoorReply(status_code=status, headers=dict(recording["headers"]), body=raw)
    return lambda _sent: reply


def with_mutated_body(mutate: Callable[[Body], None]) -> DoorResponder:
    exchange = copy.deepcopy(load(CORPUS_24)["exchanges"][0])
    mutate(exchange["body"])
    return replay([exchange])
