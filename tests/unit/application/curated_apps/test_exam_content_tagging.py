"""Optional tag suggestions must respect both citations and the shared budget."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_content_tagging import (
    MeteredExamContentTagClassifier,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLease,
    AnswerKeyTokenLeaseRefused,
    AnswerKeyTokenLeaseState,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import ExamContentItem
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import AnswerKeyTokenLeaseRepositoryProtocol
from skriptoteket.protocols.item_type_labeler import (
    ContentTagChoice,
    ContentTagClassification,
    ContentTagClassificationRequest,
    ExamContentTagClassifierProtocol,
    LabelingItem,
    LabelingUsage,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol

pytestmark = pytest.mark.unit
_NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)
_CONTENT = (
    ExamContentItem(id="course:a", text="Språkets uppbyggnad"),
    ExamContentItem(id="course:b", text="Litterära verkningsmedel"),
)


class _Setup:
    def __init__(self) -> None:
        self.classifier = Mock(spec=ExamContentTagClassifierProtocol)
        self.classifier.provider_profile_id = "decisions-test"
        self.classifier.estimate_content_tokens.return_value = 400
        self.classifier.classify_content = AsyncMock(
            return_value=ContentTagClassification(
                results=(ContentTagChoice("q1", "course:a", 0.9),),
                usage=LabelingUsage(input_tokens=67, requests=1, attempts=1),
            )
        )
        self.leases = AsyncMock(spec=AnswerKeyTokenLeaseRepositoryProtocol)
        self.lease = AnswerKeyTokenLease(
            lease_id=uuid4(),
            utc_day=_NOW.date(),
            reserved_tokens=400,
            state=AnswerKeyTokenLeaseState.RESERVED,
        )
        self.leases.reserve.return_value = self.lease
        self.uow = AsyncMock(spec=UnitOfWorkProtocol)
        clock = Mock(spec=ClockProtocol)
        clock.now.return_value = _NOW
        self.service = MeteredExamContentTagClassifier(
            classifier=self.classifier,
            leases=self.leases,
            uow=self.uow,
            clock=clock,
        )
        self.request = ContentTagClassificationRequest(
            job_id=uuid4(),
            items=(LabelingItem(item_id="q1", source_text="Analysera meningen."),),
            content_items=_CONTENT,
        )


@pytest.mark.asyncio
async def test_threshold_citations_and_actual_input_tokens_use_same_daily_lease() -> None:
    setup = _Setup()

    async def classify(*, request):
        setup.leases.reserve.assert_awaited_once()
        assert request is setup.request
        return ContentTagClassification(
            results=(ContentTagChoice("q1", "course:a", 0.9),),
            usage=LabelingUsage(input_tokens=67, requests=1, attempts=1),
        )

    setup.classifier.classify_content.side_effect = classify
    tags = await setup.service.suggest(request=setup.request)
    assert [tag.model_dump() for tag in tags] == [
        {
            "id": "course:a",
            "text": "Språkets uppbyggnad",
            "origin": "suggested",
            "question_ids": ("q1",),
        }
    ]
    setup.leases.reserve.assert_awaited_once_with(
        now=_NOW,
        requested_tokens=400,
        job_id=setup.request.job_id,
        item_id="exam_content_tags",
        provider_profile_id="decisions-test",
    )
    setup.leases.reconcile.assert_awaited_once_with(
        lease_id=setup.lease.lease_id,
        actual_tokens=67,
        now=_NOW,
    )


@pytest.mark.asyncio
async def test_exhausted_daily_budget_never_calls_model_or_fails_conversion() -> None:
    setup = _Setup()
    setup.leases.reserve.side_effect = AnswerKeyTokenLeaseRefused(
        utc_day=_NOW.date(),
        requested_tokens=400,
        available_tokens=0,
        resets_at=_NOW,
    )
    assert await setup.service.suggest(request=setup.request) == ()
    setup.classifier.classify_content.assert_not_awaited()
    setup.leases.reconcile.assert_not_awaited()


@pytest.mark.asyncio
async def test_provider_failure_keeps_reservation_charged_and_returns_no_tags() -> None:
    setup = _Setup()
    setup.classifier.classify_content.side_effect = RuntimeError("provider unavailable")
    assert await setup.service.suggest(request=setup.request) == ()
    setup.leases.reserve.assert_awaited_once()
    setup.leases.reconcile.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_usage_does_not_refund_reserved_budget() -> None:
    setup = _Setup()
    setup.classifier.classify_content.return_value = ContentTagClassification(
        results=(ContentTagChoice("q1", "course:a", 0.95),),
    )
    assert len(await setup.service.suggest(request=setup.request)) == 1
    setup.leases.reconcile.assert_not_awaited()


@pytest.mark.asyncio
async def test_reconciliation_failure_does_not_discard_valid_suggestions() -> None:
    setup = _Setup()
    setup.leases.reconcile.side_effect = RuntimeError("database transient failure")
    assert len(await setup.service.suggest(request=setup.request)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["missing", "foreign", "duplicate"])
async def test_incomplete_or_duplicate_classification_cannot_invent_citations(case: str) -> None:
    setup = _Setup()
    results = {
        "missing": (),
        "foreign": (ContentTagChoice("q-foreign", "course:a", 0.99),),
        "duplicate": (
            ContentTagChoice("q1", "course:a", 0.99),
            ContentTagChoice("q1", "course:b", 0.99),
        ),
    }[case]
    setup.classifier.classify_content.return_value = ContentTagClassification(results=results)
    assert await setup.service.suggest(request=setup.request) == ()
