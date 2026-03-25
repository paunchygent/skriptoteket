"""Protocols for class-list import extraction and parsing.

Purpose:
  Define the application-facing seams for converting uploaded class-list files
  into text or rows and then parsing them into preview data.

Relationships:
  - Implemented by infrastructure extractors such as
    `ClassListDocumentExtractor`.
  - Consumed by `CreateClassListImportPreviewHandler`.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass
from typing import Literal

if typing.TYPE_CHECKING:
    from skriptoteket.application.curated_apps.classroom_planner.import_contracts import (
        ClassListImportPreview,
    )


@dataclass(frozen=True, slots=True)
class ExtractedDocumentText:
    """Typed text extraction result with source metadata for fallback policy."""

    text: str
    source: Literal["decoded_text_file", "local_pdf_fast_path", "upstream_pdf"]


class DocumentTextExtractorProtocol(typing.Protocol):
    """Protocol for extracting text or tabular data from an uploaded file."""

    async def extract_text(
        self,
        *,
        file_content: bytes,
        file_name: str,
        content_type: str,
        correlation_id: str | None = None,
        allow_local_pdf_fast_path: bool = True,
    ) -> ExtractedDocumentText | None:
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
        correlation_id: str | None = None,
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
