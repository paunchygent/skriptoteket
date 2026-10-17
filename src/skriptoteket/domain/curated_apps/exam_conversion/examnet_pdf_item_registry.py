"""Exam.net PDF item strategy registry and the default target profile registry.

Purpose:
    Select the Exam.net PDF item strategy for a neutral item kind without widening
    callers, and own the default kind-to-strategy mapping.

Relationships:
    - Strategies come from `examnet_pdf_item_strategies`; the result and context values
      from `examnet_pdf_target_profile`.
    - Consumed by the PDF item coordinator and the native-exam PDF export.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_conversion.exam_pdf_item_semantics import (
    PdfExamItemKind,
    PdfExamItemSemantics,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_pdf_item_strategies import (
    GapOpenClozeExamNetPdfItemStrategy,
    MatchingExamNetPdfItemStrategy,
    MultipleResponseExamNetPdfItemStrategy,
    OpenEndedExamNetPdfItemStrategy,
    OrderingExamNetPdfItemStrategy,
    SingleChoiceExamNetPdfItemStrategy,
    UnsupportedExamNetPdfItemStrategy,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_pdf_target_profile import (
    ExamNetPdfItemRenderingStrategy,
    ExamNetPdfItemStrategyResult,
    ExamNetPdfTargetProfileContext,
)


@dataclass(frozen=True)
class ExamNetPdfItemRenderingPolicyRegistry:
    """Registry that selects a target item strategy without widening callers."""

    strategies_by_item_kind: Mapping[PdfExamItemKind, ExamNetPdfItemRenderingStrategy]
    unsupported_strategy: ExamNetPdfItemRenderingStrategy

    def render(
        self,
        *,
        item: PdfExamItemSemantics,
        context: ExamNetPdfTargetProfileContext,
    ) -> ExamNetPdfItemStrategyResult:
        """Render one item with the registered strategy for its neutral kind."""

        strategy = self.strategies_by_item_kind.get(item.kind, self.unsupported_strategy)
        return strategy.render(item=item, context=context)


DEFAULT_EXAMNET_PDF_ITEM_STRATEGY_REGISTRY = ExamNetPdfItemRenderingPolicyRegistry(
    strategies_by_item_kind={
        PdfExamItemKind.OPEN_RESPONSE: OpenEndedExamNetPdfItemStrategy(),
        PdfExamItemKind.SINGLE_CHOICE: SingleChoiceExamNetPdfItemStrategy(),
        PdfExamItemKind.MULTIPLE_RESPONSE: MultipleResponseExamNetPdfItemStrategy(),
        PdfExamItemKind.GAP_OPEN_CLOZE: GapOpenClozeExamNetPdfItemStrategy(),
        PdfExamItemKind.MATCHING: MatchingExamNetPdfItemStrategy(),
        PdfExamItemKind.ORDERING: OrderingExamNetPdfItemStrategy(),
    },
    unsupported_strategy=UnsupportedExamNetPdfItemStrategy(),
)
