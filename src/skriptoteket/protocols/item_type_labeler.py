"""Item-type classifier port for type-focused conversion batching (TASK-SKRIPT-39-05-04).

Purpose:
    Give each question one label from a closed set, the per-label
    probabilities, the threshold of the chosen label, and a route. Any
    classifier (rules, fuzzy matching, a Decisions model) implements the same
    port, so batching reads labels the same way whatever produced them.

Relationships:
    ``infrastructure.llm.openai.decisions_item_labeler`` implements the
    metered first pass, ``infrastructure.llm.openai.responses_item_labeler``
    the single-question second pass (D23 pass B), and
    ``application.curated_apps.item_type_labeling`` composes both behind the
    daily token lease.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    SourceImage,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import ExamContentItem
from skriptoteket.domain.llm_door import AiDoorCaller


class ItemTypeLabel(StrEnum):
    """Closed label set; declaration order is the order sent to a model."""

    SINGLE_CHOICE = "single_choice"
    MULTIPLE_RESPONSE = "multiple_response"
    GAP_FILL = "gap_fill"
    FREE_TEXT = "free_text"
    MATCHING = "matching"
    UNSUPPORTED = "unsupported"
    UNRESOLVED = "unresolved"


class LabelRoute(StrEnum):
    """What the consumer does with a label."""

    ACCEPT = "accept"
    ESCALATE = "escalate"


class LabelPass(StrEnum):
    """Which pass settled a label: the batched first pass, or the single-question second pass."""

    FIRST = "first"
    SECOND = "second"


# The decided acceptance threshold for every label (TASK-SKRIPT-39-05-04 D10).
ACCEPT_THRESHOLD = 0.95


def label_route(probability: float) -> LabelRoute:
    """Accept a label at or above the acceptance threshold; escalate it below."""

    return LabelRoute.ACCEPT if probability >= ACCEPT_THRESHOLD else LabelRoute.ESCALATE


@dataclass(frozen=True)
class LabelingItem:
    """One question's own source text as markdown, with inline answers, key labels,
    governing instructions and section heading where they stand (D14). A source part
    markdown cannot carry is an image standing at its offset in ``source_text``.
    """

    item_id: str
    source_text: str
    images: tuple[SourceImage, ...] = ()


@dataclass(frozen=True)
class LabelingRequest:
    """Questions of one conversion job and the door caller its calls run as."""

    job_id: UUID
    items: tuple[LabelingItem, ...]
    caller: AiDoorCaller

    def __post_init__(self) -> None:
        ids = [item.item_id for item in self.items]
        if len(set(ids)) != len(ids):
            raise ValueError("Labeling item ids must be unique within one request.")


@dataclass(frozen=True)
class ItemTypeLabelResult:
    """One question's label, the label probabilities, and the routing decision."""

    item_id: str
    label: ItemTypeLabel
    probabilities: Mapping[ItemTypeLabel, float]
    probability: float
    threshold: float
    route: LabelRoute
    refused: bool = False
    first_pass: ItemTypeLabelResult | None = None
    """The batched answer this result replaces after a second pass; None on a first pass."""
    decided_by: LabelPass = LabelPass.FIRST
    failure_code: str | None = None
    """Set when the second pass failed; the label is then the first pass's top label."""


@dataclass(frozen=True)
class LabelingUsage:
    """Measured provider usage; ``input_tokens`` is None when no request reported it."""

    input_tokens: int | None = None
    requests: int = 0
    attempts: int = 0


@dataclass(frozen=True)
class ItemTypeLabeling:
    """Results in request order plus the usage that produced them."""

    results: tuple[ItemTypeLabelResult, ...]
    usage: LabelingUsage = LabelingUsage()


class ItemTypeLabelerError(Exception):
    """Typed labeler failure; ``code`` is stable for routing and telemetry."""

    def __init__(self, *, code: str, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


LabelSink = Callable[[tuple[ItemTypeLabelResult, ...]], None]
"""Receives settled labels as they arrive: the accepted first-pass labels at once, then each
second-pass label as its call returns."""


class ItemTypeLabelerProtocol(Protocol):
    """Label every item of a request, in request order.

    ``on_results`` receives each settled label once, as soon as it is settled.
    """

    async def label(
        self, *, request: LabelingRequest, on_results: LabelSink | None = None
    ) -> ItemTypeLabeling: ...


class MeteredItemTypeLabelerProtocol(Protocol):
    """The batched first pass: spends provider tokens and estimates them before any call."""

    @property
    def provider_profile_id(self) -> str: ...

    async def label(self, *, request: LabelingRequest) -> ItemTypeLabeling: ...

    def estimate_input_tokens(self, *, request: LabelingRequest) -> int: ...


@dataclass(frozen=True)
class SecondPassLabel:
    """One label decided alone by the second pass, with its measured provider usage."""

    label: ItemTypeLabel
    input_tokens: int | None
    output_tokens: int | None
    refused: bool = False


@dataclass(frozen=True)
class ContentTagClassificationRequest:
    """The same faithful question sources, with one course's complete choice set."""

    job_id: UUID
    items: tuple[LabelingItem, ...]
    content_items: tuple[ExamContentItem, ...]

    def __post_init__(self) -> None:
        if len({item.item_id for item in self.items}) != len(self.items):
            raise ValueError("Content classification question ids must be unique.")
        if len({item.id for item in self.content_items}) != len(self.content_items):
            raise ValueError("Content choice ids must be unique.")


@dataclass(frozen=True)
class ContentTagChoice:
    item_id: str
    content_id: str | None
    probability: float


@dataclass(frozen=True)
class ContentTagClassification:
    results: tuple[ContentTagChoice, ...]
    usage: LabelingUsage = LabelingUsage()


class ExamContentTagClassifierProtocol(Protocol):
    @property
    def provider_profile_id(self) -> str: ...

    def estimate_content_tokens(self, *, request: ContentTagClassificationRequest) -> int: ...

    async def classify_content(
        self, *, request: ContentTagClassificationRequest
    ) -> ContentTagClassification: ...


class SecondPassItemTypeLabelerProtocol(Protocol):
    """Decide one question's label alone (D23 pass B); spends input and output tokens."""

    @property
    def provider_profile_id(self) -> str: ...

    def estimate_tokens(self, *, item: LabelingItem) -> int:
        """Estimated input tokens plus the output allowance of one call."""
        ...

    async def label_one(
        self, *, job_id: UUID, item: LabelingItem, caller: AiDoorCaller
    ) -> SecondPassLabel: ...
