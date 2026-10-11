"""Daily token lease around a metered item-type labeler (TASK-SKRIPT-39-05-04).

Purpose:
    Reserve the estimated input tokens before any provider call, label, then
    reconcile the reservation with the measured input tokens. Decisions bills
    input tokens only, so the reservation carries no output allowance. A failed
    or unmeasured call keeps its reservation charged, as every lease does.

Relationships:
    Implements ``protocols.item_type_labeler.ItemTypeLabelerProtocol`` over a
    ``MeteredItemTypeLabelerProtocol`` and the shared
    ``AnswerKeyTokenLeaseRepositoryProtocol`` daily lease.
"""

from __future__ import annotations

import structlog

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLease,
    AnswerKeyTokenLeaseRefused,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import AnswerKeyTokenLeaseRepositoryProtocol
from skriptoteket.protocols.item_type_labeler import (
    ItemTypeLabelerError,
    ItemTypeLabelerProtocol,
    ItemTypeLabeling,
    LabelingRequest,
    MeteredItemTypeLabelerProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)

LEASE_ITEM_ID = "item_type_labeling"


class LeasedItemTypeLabeler(ItemTypeLabelerProtocol):
    """Charge one labeling call against the daily token lease."""

    def __init__(
        self,
        *,
        labeler: MeteredItemTypeLabelerProtocol,
        leases: AnswerKeyTokenLeaseRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._labeler = labeler
        self._leases = leases
        self._uow = uow
        self._clock = clock

    async def label(self, *, request: LabelingRequest) -> ItemTypeLabeling:
        if not request.items:
            return ItemTypeLabeling(results=())
        lease = await self._reserve(request)
        labeling = await self._labeler.label(request=request)
        await self._reconcile(lease, request, labeling)
        return labeling

    async def _reserve(self, request: LabelingRequest) -> AnswerKeyTokenLease:
        requested = self._labeler.estimate_input_tokens(request=request)
        try:
            async with self._uow:
                return await self._leases.reserve(
                    now=self._clock.now(),
                    requested_tokens=requested,
                    job_id=request.job_id,
                    item_id=LEASE_ITEM_ID,
                    provider_profile_id=self._labeler.provider_profile_id,
                )
        except AnswerKeyTokenLeaseRefused as error:
            raise ItemTypeLabelerError(
                code="lease_refused", message=f"Daily token lease refused {requested} tokens."
            ) from error

    async def _reconcile(
        self, lease: AnswerKeyTokenLease, request: LabelingRequest, labeling: ItemTypeLabeling
    ) -> None:
        """A failed reconciliation keeps the reservation charged; the labels still stand."""

        actual = labeling.usage.input_tokens
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
                job_id=str(request.job_id),
            )
