"""Two-pass item-type classifier behind the daily token lease (TASK-SKRIPT-39-05-04 D23).

Purpose:
    The batched first pass labels every question. A label at or above the acceptance
    threshold is settled at once; every other question is decided alone by the second
    pass (B), all such questions concurrently. A second pass that fails leaves the
    question unresolved, which conversion treats as free text. Each call reserves its
    estimated tokens before any network access and reconciles the measured tokens after;
    a failed or unmeasured call keeps its reservation charged, as every lease does.

Relationships:
    Implements ``protocols.item_type_labeler.ItemTypeLabelerProtocol`` over a
    ``MeteredItemTypeLabelerProtocol`` first pass, a ``SecondPassItemTypeLabelerProtocol``
    second pass and the shared ``AnswerKeyTokenLeaseRepositoryProtocol`` daily lease.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

import structlog

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLease,
    AnswerKeyTokenLeaseRefused,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import AnswerKeyTokenLeaseRepositoryProtocol
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
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)

FIRST_PASS_LEASE_ITEM_ID = "item_type_labeling"


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


def _decided(
    first: ItemTypeLabelResult, label: ItemTypeLabel, *, refused: bool, failure: str | None
) -> ItemTypeLabelResult:
    """The second pass decides alone; the first-pass probability of its label is kept."""
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
    """Charge each labeling call against the daily token lease and settle every question."""

    def __init__(
        self,
        *,
        first_pass: MeteredItemTypeLabelerProtocol,
        second_pass: SecondPassItemTypeLabelerProtocol,
        leases: AnswerKeyTokenLeaseRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._first = first_pass
        self._second = second_pass
        self._leases = leases
        self._uow = uow
        self._clock = clock

    async def label(
        self, *, request: LabelingRequest, on_results: LabelSink | None = None
    ) -> ItemTypeLabeling:
        if not request.items:
            return ItemTypeLabeling(results=())
        first, first_tokens = await self._first_pass(request)
        accepted = tuple(r for r in first if r.route is LabelRoute.ACCEPT)
        if on_results is not None and accepted:
            on_results(accepted)
        escalated = [
            (index, item)
            for index, (item, result) in enumerate(zip(request.items, first, strict=True))
            if result.route is LabelRoute.ESCALATE
        ]
        decided = await asyncio.gather(
            *(
                self._second_pass(request.job_id, item, first[index], on_results)
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
        """A failed first pass sends every question to the second pass; a refused lease stops."""
        lease = await self._reserve(
            request.job_id,
            FIRST_PASS_LEASE_ITEM_ID,
            self._first.estimate_input_tokens(request=request),
            self._first.provider_profile_id,
        )
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
        await self._reconcile(lease, request.job_id, labeling.usage.input_tokens)
        return labeling.results, labeling.usage.input_tokens

    async def _second_pass(
        self,
        job_id: UUID,
        item: LabelingItem,
        first: ItemTypeLabelResult,
        on_results: LabelSink | None,
    ) -> tuple[ItemTypeLabelResult, int | None]:
        decided: SecondPassLabel | None = None
        failure: str | None = None
        try:
            lease = await self._reserve(
                job_id,
                f"label_b:{item.item_id}",
                self._second.estimate_tokens(item=item),
                self._second.provider_profile_id,
            )
            decided = await self._second.label_one(job_id=job_id, item=item)
            if decided.input_tokens is not None and decided.output_tokens is not None:
                await self._reconcile(lease, job_id, decided.input_tokens + decided.output_tokens)
        except ItemTypeLabelerError as error:
            failure = error.code
            logger.warning(
                "Item-type second pass failed; the question stays unresolved",
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

    async def _reserve(
        self, job_id: UUID, item_id: str, requested: int, profile_id: str
    ) -> AnswerKeyTokenLease:
        try:
            async with self._uow:
                return await self._leases.reserve(
                    now=self._clock.now(),
                    requested_tokens=requested,
                    job_id=job_id,
                    item_id=item_id,
                    provider_profile_id=profile_id,
                )
        except AnswerKeyTokenLeaseRefused as error:
            raise ItemTypeLabelerError(
                code="lease_refused", message=f"Daily token lease refused {requested} tokens."
            ) from error

    async def _reconcile(
        self, lease: AnswerKeyTokenLease, job_id: UUID, actual: int | None
    ) -> None:
        """A failed reconciliation keeps the reservation charged; the labels still stand."""
        if actual is None:
            return
        try:
            async with self._uow:
                await self._leases.reconcile(
                    lease_id=lease.lease_id, actual_tokens=actual, now=self._clock.now()
                )
        except Exception:
            logger.exception(
                "Item-type labeling token reconciliation failed; reservation retained",
                job_id=str(job_id),
            )
