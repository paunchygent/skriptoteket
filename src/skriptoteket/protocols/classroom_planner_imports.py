from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from skriptoteket.application.curated_apps.classroom_planner.import_contracts import (
        ClassListImportPreview,
    )


class DocumentTextExtractorProtocol(typing.Protocol):
    """Protocol for extracting text or tabular data from an uploaded file."""

    async def extract_text(
        self,
        *,
        file_content: bytes,
        file_name: str,
        content_type: str,
    ) -> str | None:
        """Extract raw text from a document.

        Returns None if the format is strictly tabular or if text extraction fails.
        """
        ...

    async def extract_rows(
        self,
        *,
        file_content: bytes,
        file_name: str,
        content_type: str,
    ) -> list[list[str]] | None:
        """Extract tabular rows from a document like XLSX or CSV.

        Returns None if the format is not tabular.
        """
        ...


class ClassListHeuristicParserProtocol(typing.Protocol):
    """Protocol for applying heuristics to extracted text/rows to find student names."""

    def parse(
        self,
        *,
        file_name: str,
        text: str | None,
        rows: list[list[str]] | None,
    ) -> ClassListImportPreview:
        """Parse text/rows and produce a structured preview."""
        ...
