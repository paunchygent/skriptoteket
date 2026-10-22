"""Source text the facit repeats is never shown silently (TASK-SKRIPT-REP-0049 rereview F4).

Replays the recorded conversion of `svenska_2_grammatik_omprov_variant_2_med_facit`,
item `Fråga 5`: the reply ends each source paragraph at "Analys:" while its facit holds
the three analyses. The shared wording has unknown ownership, so the item goes to
source review with its question text intact, and no converted item shows an analysis.
"""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import FORMATTING_REASON
from tests.unit.application.curated_apps.handlers.docx_conversion_cache import (
    ConversionCache,
    conversion_cache_fixture,  # noqa: F401 - registers the `conversions` fixture
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_EXAM = "svenska_2_grammatik_omprov_variant_2_med_facit"


async def _document(conversions: ConversionCache) -> NativeExamDocument:
    return (await conversions.converted(_EXAM)).outcome.result.document


async def test_fraga_5_goes_to_source_review_with_its_question_text(
    conversions: ConversionCache,
) -> None:
    document = await _document(conversions)
    (item,) = [
        item
        for item in document.items
        if item.review.state is NativeItemReviewState.REVIEW_REQUIRED
        and "Gör satsdelsanalys av meningarna." in body_plain_text(item.body)
    ]
    assert item.review.reasons == (FORMATTING_REASON,)
    text = body_plain_text(item.body)
    assert "Gör satsdelsanalys av meningarna." in text
    assert "a) Klassen läste inte texten i klassrummet." in text
    assert "b) Mentorn skickade eleverna ett tydligt schema på morgonen." in text
    assert "c) Dagen blev stressig efter beskedet." in text
    for done in document.items:
        if done.review.state is not NativeItemReviewState.REVIEW_COMPLETE:
            continue
        done_text = body_plain_text(done.body)
        for analysis in (
            "Klassen (S) läste (P) inte (SA) texten (DO) i klassrummet (Adv).",
            "Mentorn (S) skickade (P) eleverna (IO) ett tydligt schema (DO) på morgonen (Adv).",
            "Dagen (S) blev (P) stressig (Pf) efter beskedet (Adv).",
        ):
            assert analysis not in done_text
        assert "(S)" not in done_text
