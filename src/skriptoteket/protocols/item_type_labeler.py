"""Item-type classifier port for type-focused conversion batching (TASK-SKRIPT-39-05-04).

Purpose:
    Give each question one label from a closed set, the per-label
    probabilities, the threshold of the chosen label, and a route. Any
    classifier (rules, fuzzy matching, a Decisions model) implements the same
    port, so batching reads labels the same way whatever produced them.

Relationships:
    ``infrastructure.llm.openai.decisions_item_labeler`` implements the
    metered model port; ``application.curated_apps.item_type_labeling`` wraps
    it with the daily token lease.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol
from uuid import UUID


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


DEFAULT_ACCEPT_THRESHOLD = 0.95


@dataclass(frozen=True)
class ThresholdPolicy:
    """Per-label acceptance thresholds; a label without an entry uses the default."""

    default: float = DEFAULT_ACCEPT_THRESHOLD
    per_label: Mapping[ItemTypeLabel, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value in (self.default, *self.per_label.values()):
            if not 0.0 <= value <= 1.0:
                raise ValueError("Label thresholds must lie in [0, 1].")

    def threshold_for(self, label: ItemTypeLabel) -> float:
        return self.per_label.get(label, self.default)

    def route(self, label: ItemTypeLabel, probability: float) -> LabelRoute:
        """Accept at or above the label's threshold; escalate below it."""

        return (
            LabelRoute.ACCEPT if probability >= self.threshold_for(label) else LabelRoute.ESCALATE
        )


@dataclass(frozen=True)
class LabelingItem:
    """One question's source text; a child carries its parent instruction as read-only context."""

    item_id: str
    source_text: str
    parent_instruction: str | None = None


@dataclass(frozen=True)
class LabelingRequest:
    """Questions of one conversion job; ``job_id`` keys the token lease."""

    job_id: UUID
    items: tuple[LabelingItem, ...]

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


class ItemTypeLabelerProtocol(Protocol):
    """Label every item of a request, in request order."""

    async def label(self, *, request: LabelingRequest) -> ItemTypeLabeling: ...


class MeteredItemTypeLabelerProtocol(ItemTypeLabelerProtocol, Protocol):
    """A labeler that spends provider tokens and estimates them before any network call."""

    @property
    def provider_profile_id(self) -> str: ...

    def estimate_input_tokens(self, *, request: LabelingRequest) -> int: ...
