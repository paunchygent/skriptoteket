"""Meter central-content suggestions on the shared daily token lease."""

from __future__ import annotations

import structlog

from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import (
    NativeExamContentTag,
    aggregate_content_tags,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import AnswerKeyTokenLeaseRepositoryProtocol
from skriptoteket.protocols.item_type_labeler import (
    ContentTagClassificationRequest,
    ExamContentTagClassifierProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)


class MeteredExamContentTagClassifier:
    """Optional suggestions never turn a successful conversion into a failure."""

    def __init__(
        self,
        *,
        classifier: ExamContentTagClassifierProtocol,
        leases: AnswerKeyTokenLeaseRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._classifier = classifier
        self._leases = leases
        self._uow = uow
        self._clock = clock

    async def suggest(
        self, *, request: ContentTagClassificationRequest, fail_open: bool = True
    ) -> tuple[NativeExamContentTag, ...]:
        if not request.items or not request.content_items:
            return ()
        try:
            async with self._uow:
                lease = await self._leases.reserve(
                    now=self._clock.now(),
                    requested_tokens=self._classifier.estimate_content_tokens(request=request),
                    job_id=request.job_id,
                    item_id="exam_content_tags",
                    provider_profile_id=self._classifier.provider_profile_id,
                )
            classification = await self._classifier.classify_content(request=request)
            if classification.usage.input_tokens is not None:
                try:
                    async with self._uow:
                        await self._leases.reconcile(
                            lease_id=lease.lease_id,
                            actual_tokens=classification.usage.input_tokens,
                            now=self._clock.now(),
                        )
                except Exception:
                    logger.exception(
                        "Content-tag token reconciliation failed; reservation retained"
                    )
            expected = {item.item_id for item in request.items}
            if (
                len(classification.results) != len(request.items)
                or {result.item_id for result in classification.results} != expected
            ):
                raise ValueError("Content classification results do not match the questions")
            return aggregate_content_tags(
                request.content_items,
                [(r.item_id, r.content_id, r.probability) for r in classification.results],
            )
        except Exception:
            if not fail_open:
                raise
            logger.exception(
                "Content-tag suggestions failed; conversion continues without tags",
                job_id=str(request.job_id),
            )
            return ()
