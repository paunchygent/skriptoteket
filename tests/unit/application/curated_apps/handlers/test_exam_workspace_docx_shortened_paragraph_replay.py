"""A shortened own paragraph shows its whole own source paragraph (TASK-SKRIPT-REP-0049).

Replays the recorded conversion: metodprov 1 keeps the second sentence of its own source
paragraph body:0006, which the recorded reply left out, in its final item.
"""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from tests.unit.application.curated_apps.handlers.docx_conversion_cache import (
    ConversionCache,
    conversion_cache_fixture,  # noqa: F401 - registers the `conversions` fixture
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_METODPROV = "metodprov_vetenskaplig_metod_med_facit"

_WHOLE_0006 = (
    "En grupp vill undersöka hur stor andel av skolans tvåor som har läst skönlitteratur "
    "på fritiden under den senaste veckan. "
    "Gruppen har slumpat fram 120 tvåor från en fullständig elevlista."
)

_DROPPED_SENTENCE = "Gruppen har slumpat fram 120 tvåor från en fullständig elevlista."


async def _document(conversions: ConversionCache, exam: str) -> NativeExamDocument:
    return (await conversions.converted(exam)).outcome.result.document


async def test_metodprov_1_keeps_both_sentences_of_its_own_source_paragraph(
    conversions: ConversionCache,
) -> None:
    document = await _document(conversions, _METODPROV)
    (item,) = [
        item
        for item in document.items
        if item.printed_label == "1" and item.plain_text_lines()[:1] == ("Läsning på fritiden",)
    ]
    assert item.plain_text_lines() == (
        "Läsning på fritiden",
        _WHOLE_0006,
        "Vilket sätt att samla in och bearbeta information passar bäst för att besvara frågan?",
        "Markera ett svar.",
    )
    assert "\n".join(item.plain_text_lines()).count(_DROPPED_SENTENCE) == 1
