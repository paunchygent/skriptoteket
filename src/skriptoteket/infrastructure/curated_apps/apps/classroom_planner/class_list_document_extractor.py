"""Class-list document extraction adapters for Klassrumskartan imports.

Purpose:
  Normalize uploaded roster files into text or tabular rows before the domain
  heuristics run.

Relationships:
  - Implements `DocumentTextExtractorProtocol`.
  - Delegates PDF text extraction to `SirConvertALotClientV2Protocol`.
  - Supplies extracted rows/text to `CreateClassListImportPreviewHandler`.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any

import pdfplumber

from skriptoteket.config import Settings
from skriptoteket.protocols.classroom_planner_imports import (
    DocumentTextExtractorProtocol,
    ExtractedDocumentText,
)
from skriptoteket.protocols.sir_convert_a_lot_v2 import SirConvertALotClientV2Protocol

logger = logging.getLogger(__name__)


class ClassListDocumentExtractor(DocumentTextExtractorProtocol):
    def __init__(self, *, settings: Settings, sir_convert: SirConvertALotClientV2Protocol) -> None:
        self._settings = settings
        self._sir_convert = sir_convert

    async def extract_text(
        self,
        *,
        file_content: bytes,
        file_name: str,
        content_type: str,
        correlation_id: str | None = None,
        allow_local_pdf_fast_path: bool = True,
    ) -> ExtractedDocumentText | None:
        if file_name.lower().endswith(".pdf") or content_type == "application/pdf":
            if allow_local_pdf_fast_path:
                local_text = self._extract_pdf_text_locally(
                    file_content=file_content,
                    file_name=file_name,
                    correlation_id=correlation_id,
                )
                if local_text is not None:
                    return ExtractedDocumentText(
                        text=local_text,
                        source="local_pdf_fast_path",
                    )
            upstream_text = await self._sir_convert.extract_text_direct(
                file_bytes=file_content,
                filename=file_name,
                correlation_id=correlation_id,
            )
            return ExtractedDocumentText(text=upstream_text, source="upstream_pdf")

        if file_name.lower().endswith((".txt", ".csv", ".tsv")):
            return ExtractedDocumentText(
                text=self._decode_text(file_content),
                source="decoded_text_file",
            )

        return None

    async def extract_rows(
        self,
        *,
        file_content: bytes,
        file_name: str,
        content_type: str,
        correlation_id: str | None = None,
    ) -> list[list[str]] | None:
        del correlation_id
        lower_name = file_name.lower()
        if lower_name.endswith(".xlsx"):
            return self._extract_xlsx_rows(file_content)
        if lower_name.endswith(".xls"):
            return self._extract_xls_rows(file_content)

        if lower_name.endswith((".csv", ".tsv")):
            text = self._decode_text(file_content)
            delimiter = "\t" if lower_name.endswith(".tsv") else ","
            if delimiter not in text and ";" in text:
                delimiter = ";"
            reader = csv.reader(io.StringIO(text), delimiter=delimiter)
            return [list(row) for row in reader]

        return None

    def _decode_text(self, file_content: bytes) -> str:
        for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                return file_content.decode(encoding)
            except UnicodeDecodeError:
                continue
        return file_content.decode("utf-8", errors="replace")

    def _extract_pdf_text_locally(
        self,
        *,
        file_content: bytes,
        file_name: str,
        correlation_id: str | None,
    ) -> str | None:
        """Extract text from simple text PDFs before falling back upstream."""

        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                page_texts = [page.extract_text() or "" for page in pdf.pages]
        except Exception as exc:
            logger.info(
                "Local PDF extraction failed for %s; falling back to Sir Convert",
                file_name,
                extra={"correlation_id": correlation_id, "error": str(exc)},
            )
            return None

        text = "\n".join(page_texts).strip()
        if any(character.isalpha() for character in text):
            logger.info(
                "Using local PDF extraction for %s",
                file_name,
                extra={"correlation_id": correlation_id},
            )
            return text
        return None

    def _extract_xlsx_rows(self, file_content: bytes) -> list[list[str]]:
        try:
            import openpyxl
        except ImportError:
            logger.warning("openpyxl is not installed, cannot parse XLSX")
            return []

        try:
            workbook = openpyxl.load_workbook(
                filename=io.BytesIO(file_content),
                read_only=True,
                data_only=True,
            )
            rows: list[list[str]] = []
            for sheet in workbook.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    row_data = [self._stringify_cell(cell) for cell in row]
                    if any(cell.strip() for cell in row_data):
                        rows.append(row_data)
            workbook.close()
            return rows
        except Exception as e:
            logger.error("Failed to parse XLSX: %s", e)
            return []

    def _extract_xls_rows(self, file_content: bytes) -> list[list[str]]:
        try:
            import xlrd
        except ImportError:
            logger.warning("xlrd is not installed, cannot parse XLS")
            return []

        try:
            workbook = xlrd.open_workbook(file_contents=file_content)
            rows: list[list[str]] = []
            for sheet in workbook.sheets():
                for row_index in range(sheet.nrows):
                    row_data = [
                        self._stringify_cell(sheet.cell_value(row_index, column_index))
                        for column_index in range(sheet.ncols)
                    ]
                    if any(cell.strip() for cell in row_data):
                        rows.append(row_data)
            return rows
        except Exception as e:
            logger.error("Failed to parse XLS: %s", e)
            return []

    def _stringify_cell(self, cell: Any) -> str:
        if cell is None:
            return ""
        if isinstance(cell, bool):
            return "TRUE" if cell else "FALSE"
        if isinstance(cell, int):
            return str(cell)
        if isinstance(cell, float):
            if cell.is_integer():
                return str(int(cell))
            return str(cell)
        return str(cell)
