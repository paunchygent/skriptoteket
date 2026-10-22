"""Central content-tag suggestions."""

from __future__ import annotations

import structlog

from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import (
    NativeExamContentTag,
    aggregate_content_tags,
)
from skriptoteket.domain.llm_door import AiDailyLimitReached, AiDoorBusy, AiJobOverageCapReached
from skriptoteket.protocols.item_type_labeler import (
    ContentTagClassificationRequest,
    ExamContentTagClassifierProtocol,
)

logger = structlog.get_logger(__name__)


class ExamContentTagSuggester:
    """Optional suggestions never turn a successful conversion into a failure."""

    def __init__(self, *, classifier: ExamContentTagClassifierProtocol) -> None:
        self._classifier = classifier

    async def suggest(
        self, *, request: ContentTagClassificationRequest, fail_open: bool = True
    ) -> tuple[NativeExamContentTag, ...]:
        if not request.items or not request.content_items:
            return ()
        try:
            classification = await self._classifier.classify_content(request=request)
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
        except (AiDailyLimitReached, AiJobOverageCapReached, AiDoorBusy):
            raise
        except Exception:
            if not fail_open:
                raise
            logger.exception(
                "Content-tag suggestions failed; conversion continues without tags",
                job_id=str(request.job_id),
            )
            return ()
