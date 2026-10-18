"""Exam.net PDF target profile: labels, context, strategy result and strategy protocol.

Purpose:
    Own the Exam.net-oriented PDF target policy values that item strategies read and
    return: localized labels, the read-only target-profile context, the rendered
    section with its warnings, and the strategy protocol.

Relationships:
    - Consumes `domain.exam_pdf_item_semantics` values without source-adapter
      imports or mutations.
    - Produces item render contracts from `domain.digiexam_examnet_pdf_contracts`.
    - Strategies live in `examnet_pdf_item_strategies`; the registry that selects them
      lives in `examnet_pdf_item_registry`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfItemRender,
    DigiExamExamNetPdfWarning,
)
from skriptoteket.domain.curated_apps.exam_conversion.exam_pdf_item_semantics import (
    PdfExamItemSemantics,
)


@dataclass(frozen=True)
class ExamNetPdfItemLabelPolicy:
    """Localized target labels owned by the Exam.net PDF target profile."""

    free_text_type_label: str = "Fritext"
    choice_type_label: str = "Multiple choice"
    multiple_response_type_label: str = "Multiple response"
    gap_open_cloze_type_label: str = "Lucktext"
    matching_type_label: str = "Matching"
    ordering_type_label: str = "Ordering"
    source_item_type_marker: str = "Typ"
    target_item_type_marker: str = "Type"
    point_label: str = "Poängvärde"
    single_answer_key_label: str = "Correct answer"
    multiple_answer_key_label: str = "Correct answers"
    match_key_label: str = "Correct answers"
    ordering_key_label: str = "Correct order"
    gap_label: str = "Lucka"
    marking_guide_label: str = "Marking guide"


@dataclass(frozen=True)
class ExamNetPdfTargetProfileContext:
    """Read-only target-profile context passed to Exam.net PDF item strategies."""

    target_id: str
    profile_version: str
    label_policy: ExamNetPdfItemLabelPolicy
    allow_gap_open_cloze_alternate_layout: bool = False


@dataclass(frozen=True)
class ExamNetPdfItemStrategyResult:
    """Rendered target item section plus warnings emitted by one strategy."""

    item: DigiExamExamNetPdfItemRender | None
    warnings: tuple[DigiExamExamNetPdfWarning, ...] = ()


class ExamNetPdfItemRenderingStrategy(Protocol):
    """Strategy protocol for one neutral item family in an Exam.net PDF target."""

    def render(
        self,
        *,
        item: PdfExamItemSemantics,
        context: ExamNetPdfTargetProfileContext,
    ) -> ExamNetPdfItemStrategyResult:
        """Render one immutable neutral PDF item into an Exam.net section."""
        ...


DEFAULT_EXAMNET_PDF_TARGET_PROFILE_CONTEXT = ExamNetPdfTargetProfileContext(
    target_id="examnet_pdf",
    profile_version="examnet-pdf-swedish-v1",
    label_policy=ExamNetPdfItemLabelPolicy(),
)
