from __future__ import annotations

import logging

from skriptoteket.application.curated_apps.classroom_planner.import_contracts import (
    ClassListImportPreview,
)
from skriptoteket.protocols.classroom_planner_imports import (
    ClassListHeuristicParserProtocol,
    DocumentTextExtractorProtocol,
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

    async def handle(
        self,
        *,
        file_content: bytes,
        file_name: str,
        content_type: str,
    ) -> ClassListImportPreview:
        rows = await self._extractor.extract_rows(
            file_content=file_content,
            file_name=file_name,
            content_type=content_type,
        )

        text = None
        if rows is None:
            text = await self._extractor.extract_text(
                file_content=file_content,
                file_name=file_name,
                content_type=content_type,
            )

        if rows is None and text is None:
            logger.warning("File %s could not be extracted as rows or text", file_name)
            return ClassListImportPreview(
                file_name=file_name,
                suggested_class_name=None,
                parsed_students=[],
                ambiguous_rows=[],
            )

        return self._parser.parse(
            file_name=file_name,
            text=text,
            rows=rows,
        )
