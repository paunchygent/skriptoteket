"""Source text the facit copies is a recovered key carrier (TASK-SKRIPT-REP-0049 review F3/F1).

Replays the recorded conversion of `svenska_2_grammatik_omprov_variant_2_med_facit`,
item `Fråga 5`: the reply ends each source paragraph at "Analys:" while its facit holds
the three analyses. The student body keeps the instruction and each question sentence,
holds no analysis, and the facit is unchanged.
"""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from tests.unit.application.curated_apps.handlers.docx_conversion_cache import (
    ConversionCache,
    conversion_cache_fixture,  # noqa: F401 - registers the `conversions` fixture
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_EXAM = "svenska_2_grammatik_omprov_variant_2_med_facit"

_FACIT = (
    "Klassen (S) läste (P) inte (SA) texten (DO) i klassrummet (Adv). "
    "Mentorn (S) skickade (P) eleverna (IO) ett tydligt schema (DO) på morgonen (Adv). "
    "Dagen (S) blev (P) stressig (Pf) efter beskedet (Adv)."
)


async def _document(conversions: ConversionCache) -> NativeExamDocument:
    return (await conversions.converted(_EXAM)).outcome.result.document


async def test_fraga_5_keeps_no_analysis_in_the_student_body(
    conversions: ConversionCache,
) -> None:
    document = await _document(conversions)
    (item,) = [item for item in document.items if item.printed_label == "Fråga 5"]
    text = body_plain_text(item.body)
    assert item.facit_text == _FACIT
    assert "Gör satsdelsanalys av meningarna." in text
    assert "a) Klassen läste inte texten i klassrummet." in text
    assert "b) Mentorn skickade eleverna ett tydligt schema på morgonen." in text
    assert "c) Dagen blev stressig efter beskedet." in text
    for analysis in (
        "Klassen (S) läste (P) inte (SA) texten (DO) i klassrummet (Adv).",
        "Mentorn (S) skickade (P) eleverna (IO) ett tydligt schema (DO) på morgonen (Adv).",
        "Dagen (S) blev (P) stressig (Pf) efter beskedet (Adv).",
    ):
        assert analysis not in text
    assert "(S)" not in text
    assert "(P)" not in text
