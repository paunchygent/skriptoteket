"""Two-pass item-type classifier (TASK-SKRIPT-39-05-04 D23).

Purpose:
    The batched first pass labels every question. A label other than unresolved at or
    above the acceptance threshold is settled at once; every other question is decided
    alone by the second pass (B), all such questions concurrently. A question B leaves
    unresolved, by its answer, a refusal or a failure, takes the first pass's top label,
    and the converter's type_conflict resend corrects a wrong one (D23). Only a question
    neither pass gave any label stays unresolved.

Relationships:
    Implements ``protocols.item_type_labeler.ItemTypeLabelerProtocol`` over a
    ``MeteredItemTypeLabelerProtocol`` first pass and a ``SecondPassItemTypeLabelerProtocol``
    second pass.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

import structlog

from skriptoteket.domain.llm_door import AiDoorCaller
from skriptoteket.protocols.item_type_labeler import (
    ACCEPT_THRESHOLD,
    ItemTypeLabel,
    ItemTypeLabelerError,
    ItemTypeLabelerProtocol,
    ItemTypeLabeling,
    ItemTypeLabelResult,
    LabelingItem,
    LabelingRequest,
    LabelingUsage,
    LabelPass,
    LabelRoute,
    LabelSink,
    MeteredItemTypeLabelerProtocol,
    SecondPassItemTypeLabelerProtocol,
    SecondPassLabel,
)

logger = structlog.get_logger(__name__)


def _first_pass_failed(item: LabelingItem, code: str) -> ItemTypeLabelResult:
    """A question the first pass could not label goes to the second pass."""
    return ItemTypeLabelResult(
        item_id=item.item_id,
        label=ItemTypeLabel.UNRESOLVED,
        probabilities={},
        probability=0.0,
        threshold=ACCEPT_THRESHOLD,
        route=LabelRoute.ESCALATE,
        failure_code=code,
    )


def _settled(result: ItemTypeLabelResult) -> bool:
    """A first-pass label is settled at once when accepted and not unresolved."""
    return result.route is LabelRoute.ACCEPT and result.label is not ItemTypeLabel.UNRESOLVED


def _top_label(first: ItemTypeLabelResult) -> ItemTypeLabel:
    """The first pass's most probable label other than unresolved; unresolved when the
    first pass gave no probabilities."""
    ranked = {
        label: probability
        for label, probability in first.probabilities.items()
        if label is not ItemTypeLabel.UNRESOLVED
    }
    return max(ranked, key=ranked.__getitem__, default=ItemTypeLabel.UNRESOLVED)


def _decided(
    first: ItemTypeLabelResult,
    answer: ItemTypeLabel,
    *,
    refused: bool,
    failure: str | None,
) -> ItemTypeLabelResult:
    """The second pass decides alone; a question it leaves unresolved takes the first pass's
    top label (D23). The first-pass probability of the label is kept."""
    label = _top_label(first) if answer is ItemTypeLabel.UNRESOLVED else answer
    return ItemTypeLabelResult(
        item_id=first.item_id,
        label=label,
        probabilities=first.probabilities,
        probability=first.probabilities.get(label, 0.0),
        threshold=ACCEPT_THRESHOLD,
        route=LabelRoute.ACCEPT,
        refused=refused,
        first_pass=first,
        decided_by=LabelPass.SECOND,
        failure_code=failure,
    )


class TwoPassItemTypeLabeler(ItemTypeLabelerProtocol):
    """Settle every question over its two labeling passes."""

    def __init__(
        self,
        *,
        first_pass: MeteredItemTypeLabelerProtocol,
        second_pass: SecondPassItemTypeLabelerProtocol,
    ) -> None:
        self._first = first_pass
        self._second = second_pass

    async def label(
        self, *, request: LabelingRequest, on_results: LabelSink | None = None
    ) -> ItemTypeLabeling:
        if not request.items:
            return ItemTypeLabeling(results=())
        first, first_tokens = await self._first_pass(request)
        accepted = tuple(r for r in first if _settled(r))
        if on_results is not None and accepted:
            on_results(accepted)
        escalated = [
            (index, item)
            for index, (item, result) in enumerate(zip(request.items, first, strict=True))
            if not _settled(result)
        ]
        decided = await asyncio.gather(
            *(
                self._second_pass(request.job_id, item, first[index], on_results, request.caller)
                for index, item in escalated
            )
        )
        results = list(first)
        tokens = [first_tokens]
        for (index, _), (result, input_tokens) in zip(escalated, decided, strict=True):
            results[index] = result
            tokens.append(input_tokens)
        return ItemTypeLabeling(
            results=tuple(results),
            usage=LabelingUsage(
                input_tokens=None if None in tokens else sum(t or 0 for t in tokens),
                requests=len(tokens),
                attempts=len(tokens),
            ),
        )

    async def _first_pass(
        self, request: LabelingRequest
    ) -> tuple[tuple[ItemTypeLabelResult, ...], int | None]:
        """A failed first pass sends every question to the second pass."""
        try:
            labeling = await self._first.label(request=request)
        except ItemTypeLabelerError as error:
            logger.warning(
                "Item-type first pass failed; every question goes to the second pass",
                job_id=str(request.job_id),
                code=error.code,
                status_code=error.status_code,
            )
            return tuple(_first_pass_failed(item, error.code) for item in request.items), None
        return labeling.results, labeling.usage.input_tokens

    async def _second_pass(
        self,
        job_id: UUID,
        item: LabelingItem,
        first: ItemTypeLabelResult,
        on_results: LabelSink | None,
        caller: AiDoorCaller,
    ) -> tuple[ItemTypeLabelResult, int | None]:
        decided: SecondPassLabel | None = None
        failure: str | None = None
        try:
            decided = await self._second.label_one(job_id=job_id, item=item, caller=caller)
        except ItemTypeLabelerError as error:
            failure = error.code
            logger.warning(
                "Item-type second pass failed; the question takes the first pass's top label",
                job_id=str(job_id),
                code=error.code,
                status_code=error.status_code,
            )
        result = _decided(
            first,
            decided.label if decided is not None else ItemTypeLabel.UNRESOLVED,
            refused=decided is not None and decided.refused,
            failure=failure,
        )
        if on_results is not None:
            on_results((result,))
        return result, None if decided is None else decided.input_tokens
