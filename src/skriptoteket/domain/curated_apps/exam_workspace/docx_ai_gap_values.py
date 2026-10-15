"""Automatic misspellings for one DOCX gap, from the shared deterministic producer.

The producer owns the tiered data; conversion supplies one document-wide language and
excludes every other gold answer of the same item.
"""

from skriptoteket.domain.curated_apps.exam_workspace.answer_misspellings import (
    produce_answer_misspellings,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_spelling import normalize_answer
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedSegment
from skriptoteket.domain.curated_apps.exam_workspace.exam_document_language import Language
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import NativeGap


def gap_automatic_values(
    accepted_values: tuple[str, ...],
    *,
    language: Language,
    item_gold_answers: tuple[str, ...],
) -> tuple[str, ...]:
    """The producer's bounded misspellings for one gap; the item's other gold answers are out."""
    own = {normalize_answer(value) for value in accepted_values}
    other = tuple(value for value in item_gold_answers if normalize_answer(value) not in own)
    return produce_answer_misspellings(accepted_values, language=language, other_gold_answers=other)


def native_gap(
    segment: ProducedSegment,
    *,
    gap_id: str,
    language: Language,
    item_gold_answers: tuple[str, ...],
) -> NativeGap:
    """The native gap with the producer's automatic values, empty for an unkeyed gap."""
    automatic = (
        gap_automatic_values(
            segment.accepted_values,
            language=language,
            item_gold_answers=item_gold_answers,
        )
        if segment.accepted_values
        else ()
    )
    return NativeGap(
        gap_id=gap_id,
        accepted_values=segment.accepted_values,
        automatic_values=automatic,
    )
