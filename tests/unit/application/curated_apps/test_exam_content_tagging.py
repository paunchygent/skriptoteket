"""Optional tag suggestions must respect citations and never fail conversion."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_content_tagging import (
    MeteredExamContentTagClassifier,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import ExamContentItem
from skriptoteket.protocols.item_type_labeler import (
    ContentTagChoice,
    ContentTagClassification,
    ContentTagClassificationRequest,
    ExamContentTagClassifierProtocol,
    LabelingItem,
    LabelingUsage,
)

pytestmark = pytest.mark.unit
_CONTENT = (
    ExamContentItem(id="course:a", text="Språkets uppbyggnad"),
    ExamContentItem(id="course:b", text="Litterära verkningsmedel"),
)


class _Setup:
    def __init__(self) -> None:
        self.classifier = Mock(spec=ExamContentTagClassifierProtocol)
        self.classifier.provider_profile_id = "decisions-test"
        self.classifier.classify_content = AsyncMock(
            return_value=ContentTagClassification(
                results=(ContentTagChoice("q1", "course:a", 0.9),),
                usage=LabelingUsage(input_tokens=67, requests=1, attempts=1),
            )
        )
        self.service = MeteredExamContentTagClassifier(classifier=self.classifier)
        self.request = ContentTagClassificationRequest(
            job_id=uuid4(),
            items=(LabelingItem(item_id="q1", source_text="Analysera meningen."),),
            content_items=_CONTENT,
        )


@pytest.mark.asyncio
async def test_threshold_citations_use_actual_input_tokens() -> None:
    setup = _Setup()

    async def classify(*, request):
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
    setup.classifier.classify_content.assert_awaited_once()


@pytest.mark.asyncio
async def test_provider_failure_returns_no_tags_without_failing_conversion() -> None:
    setup = _Setup()
    setup.classifier.classify_content.side_effect = RuntimeError("provider unavailable")
    assert await setup.service.suggest(request=setup.request) == ()


@pytest.mark.asyncio
async def test_unknown_usage_still_returns_valid_suggestions() -> None:
    setup = _Setup()
    setup.classifier.classify_content.return_value = ContentTagClassification(
        results=(ContentTagChoice("q1", "course:a", 0.95),),
    )
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
