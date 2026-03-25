from __future__ import annotations

import csv
import io
import logging
from typing import cast

import httpx

from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.classroom_planner_imports import DocumentTextExtractorProtocol

logger = logging.getLogger(__name__)


class ClassListDocumentExtractor(DocumentTextExtractorProtocol):
    def __init__(self, *, settings: Settings, http_client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http_client = http_client

    async def extract_text(
        self,
        *,
        file_content: bytes,
        file_name: str,
        content_type: str,
    ) -> str | None:
        if file_name.lower().endswith(".pdf") or content_type == "application/pdf":
            return await self._extract_pdf_text(file_content, file_name)

        if file_name.lower().endswith((".txt", ".csv", ".tsv")):
            return self._decode_text(file_content)

        return None

    async def extract_rows(
        self,
        *,
        file_content: bytes,
        file_name: str,
        content_type: str,
    ) -> list[list[str]] | None:
        lower_name = file_name.lower()
        if lower_name.endswith(".xlsx"):
            return self._extract_xlsx_rows(file_content)

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

    def _extract_xlsx_rows(self, file_content: bytes) -> list[list[str]]:
        try:
            import openpyxl  # type: ignore
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
                    # Convert to string and handle None
                    row_data = ["" if cell is None else str(cell) for cell in row]
                    if any(cell.strip() for cell in row_data):
                        rows.append(row_data)
            workbook.close()
            return rows
        except Exception as e:
            logger.error("Failed to parse XLSX: %s", e)
            return []

    async def _extract_pdf_text(self, file_content: bytes, file_name: str) -> str:
        base_url = self._settings.SIR_CONVERT_A_LOT_V2_BASE_URL.rstrip("/")
        url = f"{base_url}/api/v2/extract-text"

        headers = {}
        if self._settings.SIR_CONVERT_A_LOT_V2_API_KEY:
            headers["Authorization"] = f"Bearer {self._settings.SIR_CONVERT_A_LOT_V2_API_KEY}"

        try:
            response = await self._http_client.post(
                url,
                headers=headers,
                files={"file": (file_name, file_content, "application/pdf")},
                timeout=self._settings.SIR_CONVERT_A_LOT_V2_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
            return cast(str, data.get("text", ""))
        except httpx.HTTPStatusError as e:
            logger.error(
                "Sir Convert-a-Lot returned error status %s: %s",
                e.response.status_code,
                e.response.text,
            )
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Failed to extract text from PDF via Sir Convert-a-Lot.",
            ) from e
        except httpx.RequestError as e:
            logger.error("Failed to connect to Sir Convert-a-Lot: %s", e)
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Could not reach Sir Convert-a-Lot service.",
            ) from e
