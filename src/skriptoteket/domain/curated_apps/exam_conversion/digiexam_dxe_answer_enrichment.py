"""DigiExam `.dxe` answer-key validation.

Purpose:
    Bind populated `.dxe` gap validations to their blank GUIDs without
    inventing answer keys when the source carries none.

Relationships:
    - Used by `domain.digiexam_dxe_parser` after `.dxe` structure extraction.
    - Emits shared DigiExam answer value objects for downstream
      renderer-neutral contracts.
"""

from __future__ import annotations

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamGap,
    DigiExamGapAnswer,
)


def dxe_gap_answers(gaps: tuple[DigiExamGap, ...]) -> tuple[DigiExamGapAnswer, ...]:
    """Return populated `.dxe` gap validations bound to their blank GUIDs."""

    return tuple(
        DigiExamGapAnswer(guid=gap.guid, value=value) for gap in gaps for value in gap.validations
    )
