"""Repo-owned SDS corpus store for Reagent Prep Chef.

ADR-0067: SDS is a markdown-first offline corpus:
- Markdown is committed under `data/reagent_prep_chef/sds/markdown/`
- Index is committed under `data/reagent_prep_chef/sds/index.json`
- PDF downloads are generated from markdown and cached on disk outside git

The backend must not fetch SDS content at runtime; it only serves repo-owned SDS documents.
"""

from __future__ import annotations

import base64
import json
import tempfile
from html import escape
from pathlib import Path

import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from skriptoteket.domain.curated_apps.reagent_prep_chef.models import SdsCorpusEntry
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.protocols.reagent_prep_chef import (
    ReagentPrepChefPdfRendererProtocol,
    ReagentPrepChefSdsStoreProtocol,
)

logger = structlog.get_logger(__name__)

SDS_PDF_TEMPLATE_VERSION = 1
SDS_PDF_MEDIA_TYPE = "application/pdf"
SDS_PDF_LOGO_SVG_PATH = Path("src/skriptoteket/web/static/spa/logo-horizontal.svg")

SDS_PDF_CSS = """
@page { size: A4; margin: 18mm 14mm; }
body {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  font-size: 11px;
  line-height: 1.35;
  color: #111;
}
.header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 0 12px 0;
  padding: 0 0 8px 0;
  border-bottom: 2px solid #111;
}
.header__logo { height: 22px; }
.header__title { font-size: 16px; font-weight: 700; margin: 0; }
.header__meta { font-size: 10px; color: #333; margin-top: 2px; }
h1,h2,h3,h4 { break-after: avoid; }
h2 { font-size: 14px; margin: 16px 0 6px; }
h3 { font-size: 12px; margin: 14px 0 6px; }
table { width: 100%; border-collapse: collapse; margin: 8px 0; }
th, td { border: 1px solid #111; padding: 4px 6px; vertical-align: top; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 10px; }
pre { background: #f6f6f6; border: 1px solid #ddd; padding: 8px; white-space: pre-wrap; }
"""


def _svg_data_uri(*, svg_bytes: bytes) -> str:
    b64 = base64.b64encode(svg_bytes).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


class _SdsIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    display_name: str
    sds_ref: str
    md_file_name: str
    provider: str
    revision: str
    pdf_file_name: str | None = None

    def to_domain(self) -> SdsCorpusEntry:
        return SdsCorpusEntry(
            sds_ref=self.sds_ref,
            key=self.key,
            md_file_name=self.md_file_name,
            provider=self.provider,
            revision=self.revision,
            pdf_file_name=self.pdf_file_name,
        )


class _SdsIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    as_of: str
    entries: dict[str, _SdsIndexEntry] = Field(default_factory=dict)


class FileSystemReagentPrepChefSdsStore(ReagentPrepChefSdsStoreProtocol):
    def __init__(
        self,
        *,
        index_path: Path,
        markdown_dir: Path,
        pdf_cache_dir: Path,
        pdf_renderer: ReagentPrepChefPdfRendererProtocol,
    ) -> None:
        self._index_path = index_path
        self._markdown_dir = markdown_dir
        self._pdf_cache_dir: Path | None = self._init_pdf_cache_dir(pdf_cache_dir=pdf_cache_dir)
        self._pdf_renderer = pdf_renderer

        self._logo_data_uri: str | None = None
        try:
            self._logo_data_uri = _svg_data_uri(svg_bytes=SDS_PDF_LOGO_SVG_PATH.read_bytes())
        except FileNotFoundError:
            self._logo_data_uri = None

        self._index = self._load_index(index_path=index_path)
        self._entries_by_ref: dict[str, _SdsIndexEntry] = {
            entry.sds_ref: entry for entry in self._index.entries.values()
        }

    def get_entry(self, *, sds_ref: str) -> SdsCorpusEntry:
        entry = self._lookup(sds_ref=sds_ref)
        return entry.to_domain()

    def get_markdown(self, *, sds_ref: str) -> tuple[SdsCorpusEntry, str]:
        entry = self._lookup(sds_ref=sds_ref)
        path = self._markdown_dir / entry.md_file_name
        if not path.is_file():
            raise not_found("SDS", sds_ref)
        try:
            markdown = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Kunde inte läsa SDS-markdown.",
                details={"path": str(path)},
            ) from exc
        return (entry.to_domain(), markdown)

    def get_pdf(self, *, sds_ref: str) -> tuple[str, bytes, str]:
        entry = self._lookup(sds_ref=sds_ref)
        md_path = self._markdown_dir / entry.md_file_name
        if not md_path.is_file():
            raise not_found("SDS", sds_ref)

        pdf_file_name = self._generated_pdf_name(md_file_name=entry.md_file_name)
        pdf_path = None if self._pdf_cache_dir is None else (self._pdf_cache_dir / pdf_file_name)

        if pdf_path is not None:
            try:
                if pdf_path.is_file() and pdf_path.stat().st_mtime >= md_path.stat().st_mtime:
                    return (pdf_file_name, pdf_path.read_bytes(), SDS_PDF_MEDIA_TYPE)
            except OSError as exc:
                logger.warning(
                    "Failed to read SDS PDF cache; regenerating",
                    pdf_path=str(pdf_path),
                    md_path=str(md_path),
                    error=str(exc),
                )

        try:
            markdown_text = md_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Kunde inte läsa SDS-markdown.",
                details={"path": str(md_path)},
            ) from exc

        try:
            html = self._build_sds_pdf_html(entry=entry, markdown=markdown_text)
        except Exception as exc:  # noqa: BLE001
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Kunde inte skapa SDS-PDF just nu. Försök igen.",
                details={},
            ) from exc
        try:
            pdf_bytes = self._pdf_renderer.render_html(html=html)
        except Exception as exc:  # noqa: BLE001
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Kunde inte skapa SDS-PDF just nu. Försök igen.",
                details={},
            ) from exc

        if pdf_path is not None:
            self._write_cached_pdf(path=pdf_path, content=pdf_bytes)
        return (pdf_file_name, pdf_bytes, SDS_PDF_MEDIA_TYPE)

    @staticmethod
    def _generated_pdf_name(*, md_file_name: str) -> str:
        stem = Path(md_file_name).stem
        return f"{stem}__skriptoteket__pdfv{SDS_PDF_TEMPLATE_VERSION}.pdf"

    def _build_sds_pdf_html(self, *, entry: _SdsIndexEntry, markdown: str) -> str:
        import markdown as markdown_lib

        body = markdown_lib.markdown(
            markdown,
            extensions=["tables", "fenced_code", "sane_lists"],
            output_format="html",
        )

        title = "Säkerhetsdatablad (SDS)"
        meta_parts: list[str] = [f"SDS-ref: {entry.sds_ref}"]
        if entry.provider:
            meta_parts.append(f"Leverantör: {entry.provider}")
        if entry.revision:
            meta_parts.append(f"Revision: {entry.revision}")

        logo_html = ""
        if self._logo_data_uri:
            logo_html = (
                "<img class='header__logo' alt='Skriptoteket' "
                f"src='{escape(self._logo_data_uri, quote=True)}'/>"
            )

        meta_html = escape(" • ".join(meta_parts))
        return (
            "<!doctype html>"
            "<html lang='sv'>"
            "<head>"
            "<meta charset='utf-8'/>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
            f"<title>{escape(title)}</title>"
            "<style>"
            f"{SDS_PDF_CSS}"
            "</style>"
            "</head>"
            "<body>"
            "<div class='header'>"
            f"{logo_html}"
            "<div>"
            f"<div class='header__title'>{escape(title)}</div>"
            f"<div class='header__meta'>{meta_html}</div>"
            "</div>"
            "</div>"
            f"{body}"
            "</body>"
            "</html>"
        )

    def _write_cached_pdf(self, *, path: Path, content: bytes) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=str(path.parent), delete=False, prefix=path.name, suffix=".tmp"
            ) as tmp:
                tmp.write(content)
                tmp.flush()
                Path(tmp.name).replace(path)
        except OSError as exc:
            logger.warning(
                "Failed to write SDS PDF cache; continuing without cache",
                pdf_path=str(path),
                error=str(exc),
            )

    @staticmethod
    def _init_pdf_cache_dir(*, pdf_cache_dir: Path) -> Path | None:
        try:
            pdf_cache_dir.mkdir(parents=True, exist_ok=True)
            return pdf_cache_dir
        except OSError as exc:
            fallback_dir = (
                Path(tempfile.gettempdir()) / "skriptoteket" / "reagent_prep_chef" / "sds_pdfs"
            )
            try:
                fallback_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                logger.warning(
                    "SDS PDF cache disabled; no writable cache directory available",
                    requested_dir=str(pdf_cache_dir),
                    fallback_dir=str(fallback_dir),
                    error=str(exc),
                )
                return None

            logger.warning(
                "SDS PDF cache dir not writable; using fallback directory",
                requested_dir=str(pdf_cache_dir),
                fallback_dir=str(fallback_dir),
                error=str(exc),
            )
            return fallback_dir

    def _lookup(self, *, sds_ref: str) -> _SdsIndexEntry:
        normalized = sds_ref.strip()
        if not normalized:
            raise not_found("SDS", sds_ref)

        entry = self._index.entries.get(normalized) or self._entries_by_ref.get(normalized)
        if entry is None:
            raise not_found("SDS", sds_ref)
        return entry

    @staticmethod
    def _load_index(*, index_path: Path) -> _SdsIndex:
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            return _SdsIndex.model_validate(payload)
        except FileNotFoundError as exc:
            raise not_found("SDS index", str(index_path)) from exc
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise validation_error(
                "SDS-index kunde inte läsas.", details={"path": str(index_path)}
            ) from exc
