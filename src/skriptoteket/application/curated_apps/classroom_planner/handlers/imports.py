"""Application handler for class-list import previews.

Purpose:
  Coordinate extraction plus parsing for teacher-uploaded roster files without
  persisting any roster until the teacher confirms the preview.

Relationships:
  - Depends on `DocumentTextExtractorProtocol` and
    `ClassListHeuristicParserProtocol`.
  - Used by `apps_classroom_planner.py` through Dishka DI.
"""

from __future__ import annotations

import logging

from skriptoteket.application.curated_apps.classroom_planner.import_contracts import (
    ClassListImportPreview,
)
from skriptoteket.protocols.classroom_planner_imports import (
    ClassListHeuristicParserProtocol,
    DocumentTextExtractorProtocol,
    ExtractedDocumentText,
)

logger = logging.getLogger(__name__)


class CreateClassListImportPreviewHandler:
    def __init__(
        self,
        *,
        extractor: DocumentTextExtractorProtocol,
        parser: ClassListHeuristicParserProtocol,
    ) -> None:
        self._extractor = extractor
        self._parser = parser

    def _should_retry_pdf_with_upstream(
        self,
        *,
        file_name: str,
        content_type: str,
        extracted_text: ExtractedDocumentText | None,
    ) -> bool:
        is_pdf_upload = file_name.lower().endswith(".pdf") or content_type == "application/pdf"
        if not is_pdf_upload or extracted_text is None:
            return False
        return extracted_text.source == "local_pdf_fast_path"

    @staticmethod
    def _preview_quality(preview: ClassListImportPreview) -> tuple[int, int, int]:
        """Rank preview usefulness so upstream retries can replace partial local parses."""

        return (
            1 if preview.suggested_class_name else 0,
            len(preview.parsed_students),
            -len(preview.ambiguous_rows),
        )

    def _choose_better_preview(
        self,
        *,
        local_preview: ClassListImportPreview,
        upstream_preview: ClassListImportPreview,
    ) -> ClassListImportPreview:
        if self._preview_quality(upstream_preview) > self._preview_quality(local_preview):
            return upstream_preview
        return local_preview

    async def handle(
        self,
        *,
        file_content: bytes,
        file_name: str,
        content_type: str,
        correlation_id: str | None = None,
    ) -> ClassListImportPreview:
        rows = await self._extractor.extract_rows(
            file_content=file_content,
            file_name=file_name,
            content_type=content_type,
            correlation_id=correlation_id,
        )

        text_result = None
        if rows is None:
            text_result = await self._extractor.extract_text(
                file_content=file_content,
                file_name=file_name,
                content_type=content_type,
                correlation_id=correlation_id,
            )
        text = text_result.text if text_result is not None else None

        if rows is None and text is None:
            logger.warning("File %s could not be extracted as rows or text", file_name)
            return ClassListImportPreview(
                file_name=file_name,
                suggested_class_name=None,
                parsed_students=[],
                ambiguous_rows=[],
            )

        preview = self._parser.parse(
            file_name=file_name,
            text=text,
            rows=rows,
        )
        if not self._should_retry_pdf_with_upstream(
            file_name=file_name,
            content_type=content_type,
            extracted_text=text_result,
        ):
            return preview

        logger.info(
            "Comparing local PDF extraction against upstream result for %s",
            file_name,
        )
        try:
            upstream_text_result = await self._extractor.extract_text(
                file_content=file_content,
                file_name=file_name,
                content_type=content_type,
                correlation_id=correlation_id,
                allow_local_pdf_fast_path=False,
            )
        except Exception:
            logger.exception(
                "Upstream PDF extraction failed after a local preview succeeded for %s",
                file_name,
            )
            return preview
        if upstream_text_result is None:
            return preview
        upstream_preview = self._parser.parse(
            file_name=file_name,
            text=upstream_text_result.text,
            rows=rows,
        )
        return self._choose_better_preview(
            local_preview=preview,
            upstream_preview=upstream_preview,
        )
