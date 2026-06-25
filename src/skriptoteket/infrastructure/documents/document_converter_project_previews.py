"""Filesystem and WeasyPrint adapters for Document Converter project previews.

Purpose:
    Render uploaded HTML/CSS project files into temporary PDFs with a constrained
    in-memory asset sandbox, then store preview artifacts under the server
    artifacts root with owner-scoped authority and TTL cleanup.

Relationships:
    Implements Document Converter project preview protocols for application
    handlers and uses WeasyPrint/pypdf only behind the infrastructure boundary.
"""

from __future__ import annotations

import io
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubPdfOrientationV2,
)
from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterStoredArtifact,
)
from skriptoteket.application.curated_apps.document_converter_projects import (
    DOCUMENT_CONVERTER_PROJECT_BASE_URL,
    DocumentConverterProjectManifest,
    DocumentConverterProjectOutputMode,
    DocumentConverterProjectTemplateId,
    DocumentConverterProjectUploadedFile,
)
from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.scripting.input_files import sanitize_input_filename
from skriptoteket.infrastructure.documents.document_converter_project_preview_store import (
    FilesystemDocumentConverterProjectPreviewStore,
)
from skriptoteket.protocols.document_converter import (
    DocumentConverterProjectPreviewRendererProtocol,
)

__all__ = [
    "DocumentConverterProjectAssetFetcher",
    "FilesystemDocumentConverterProjectPreviewStore",
    "WeasyPrintDocumentConverterProjectRenderer",
]

_PDF_CONTENT_TYPE = "application/pdf"
_COMBINED_FILENAME = "combined.pdf"

_TEMPLATE_CSS = {
    DocumentConverterProjectTemplateId.ACADEMIC_PHD: """
body {
  font-family: "Aptos", "Inter", "Helvetica Neue", Arial, sans-serif;
  font-size: 11pt;
  line-height: 1.45;
}
h1, h2, h3 { font-family: "Aptos Display", "Georgia", serif; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 0.2mm solid #777; padding: 2.5mm; }
""",
    DocumentConverterProjectTemplateId.CLEAN_WORKSHEET: """
body {
  font-family: "Inter", "Arial", sans-serif;
  font-size: 11pt;
  line-height: 1.5;
}
h1, h2, h3 { font-weight: 700; }
hr { border: 0; border-top: 0.3mm solid #444; }
""",
    DocumentConverterProjectTemplateId.EXPRESSIVE_HANDOUT: """
body {
  font-family: "Georgia", "Aptos", serif;
  font-size: 11.5pt;
  line-height: 1.5;
}
h1, h2 { letter-spacing: 0; }
blockquote { border-left: 1.5mm solid #333; padding-left: 4mm; }
""",
}


class DocumentConverterProjectAssetFetcher:
    """Resolve WeasyPrint resources from declared in-memory project files only."""

    def __init__(self, *, files: list[DocumentConverterProjectUploadedFile]) -> None:
        self._files = {project_file.filename: project_file for project_file in files}

    def __call__(self, url: str):
        """Allow WeasyPrint to use this object as ``url_fetcher``."""
        return self.fetch(url)

    def fetch(self, url: str, headers=None):
        """Return one declared project file or stop rendering on unsafe URLs."""
        del headers
        from weasyprint.urls import FatalURLFetchingError, URLFetcherResponse

        filename = _project_filename_from_url(url=url)
        project_file = self._files.get(filename)
        if project_file is None:
            raise FatalURLFetchingError("Project asset is not declared in the manifest.")
        return URLFetcherResponse(
            url,
            project_file.content,
            {"Content-Type": project_file.content_type},
        )


class WeasyPrintDocumentConverterProjectRenderer(DocumentConverterProjectPreviewRendererProtocol):
    """Render HTML/CSS project uploads into separate and combined preview PDFs."""

    def render_project(
        self,
        *,
        manifest: DocumentConverterProjectManifest,
        files: list[DocumentConverterProjectUploadedFile],
    ) -> list[DocumentConverterStoredArtifact]:
        """Render preview artifacts requested by the manifest output mode."""
        manifest.validate_uploaded_file_set(
            uploaded_filenames={project_file.filename for project_file in files}
        )
        files_by_name = {project_file.filename: project_file for project_file in files}
        fetcher = DocumentConverterProjectAssetFetcher(files=files)
        css_text = _build_stylesheet(manifest=manifest, files_by_name=files_by_name)
        separate = [
            _render_entry_pdf(
                manifest=manifest,
                files_by_name=files_by_name,
                fetcher=fetcher,
                css_text=css_text,
                entry_index=index,
            )
            for index in range(len(manifest.html_entries))
        ]
        return _select_output_artifacts(manifest=manifest, separate=separate)


def _render_entry_pdf(
    *,
    manifest: DocumentConverterProjectManifest,
    files_by_name: dict[str, DocumentConverterProjectUploadedFile],
    fetcher: DocumentConverterProjectAssetFetcher,
    css_text: str,
    entry_index: int,
) -> DocumentConverterStoredArtifact:
    entry = manifest.html_entries[entry_index]
    html = _decode_text_file(files_by_name[entry.filename])
    pdf_bytes = _render_weasyprint_pdf(html=html, css_text=css_text, fetcher=fetcher)
    return DocumentConverterStoredArtifact(
        filename=_entry_pdf_filename(input_filename=entry.filename),
        content_type=_PDF_CONTENT_TYPE,
        content=pdf_bytes,
    )


def _render_weasyprint_pdf(
    *,
    html: str,
    css_text: str,
    fetcher: DocumentConverterProjectAssetFetcher,
) -> bytes:
    from weasyprint import CSS, HTML
    from weasyprint.text.fonts import FontConfiguration
    from weasyprint.urls import FatalURLFetchingError

    font_config = FontConfiguration()
    try:
        stylesheet = CSS(
            string=css_text,
            base_url=DOCUMENT_CONVERTER_PROJECT_BASE_URL,
            url_fetcher=fetcher,
            font_config=font_config,
        )
        rendered = HTML(
            string=html,
            base_url=DOCUMENT_CONVERTER_PROJECT_BASE_URL,
            url_fetcher=fetcher,
        ).write_pdf(stylesheets=[stylesheet], font_config=font_config)
    except FatalURLFetchingError as exc:
        raise validation_error(
            "Document Converter project asset is outside the uploaded project boundary."
        ) from exc
    if isinstance(rendered, bytes):
        return rendered
    if isinstance(rendered, bytearray):
        return bytes(rendered)
    raise TypeError("WeasyPrint returned a non-bytes PDF payload.")


def _build_stylesheet(
    *,
    manifest: DocumentConverterProjectManifest,
    files_by_name: dict[str, DocumentConverterProjectUploadedFile],
) -> str:
    declared_css = "\n".join(
        _decode_text_file(files_by_name[filename]) for filename in manifest.css_files
    )
    return "\n".join(
        [
            _page_css(manifest=manifest),
            _TEMPLATE_CSS[manifest.pdf_controls.template_id],
            declared_css,
        ]
    )


def _page_css(*, manifest: DocumentConverterProjectManifest) -> str:
    controls = manifest.pdf_controls
    page_size = controls.paper_size.value.upper()
    orientation = (
        "landscape"
        if controls.orientation is ConversionHubPdfOrientationV2.LANDSCAPE
        else "portrait"
    )
    margins = controls.margins
    return (
        "@page { "
        f"size: {page_size} {orientation}; "
        "margin: "
        f"{margins.top_mm}mm {margins.right_mm}mm "
        f"{margins.bottom_mm}mm {margins.left_mm}mm; "
        "}"
    )


def _select_output_artifacts(
    *,
    manifest: DocumentConverterProjectManifest,
    separate: list[DocumentConverterStoredArtifact],
) -> list[DocumentConverterStoredArtifact]:
    artifacts: list[DocumentConverterStoredArtifact] = []
    if manifest.output_mode in {
        DocumentConverterProjectOutputMode.SEPARATE_PDFS,
        DocumentConverterProjectOutputMode.BOTH,
    }:
        artifacts.extend(separate)
    if manifest.output_mode in {
        DocumentConverterProjectOutputMode.COMBINED_PDF,
        DocumentConverterProjectOutputMode.BOTH,
    }:
        artifacts.append(
            DocumentConverterStoredArtifact(
                filename=_COMBINED_FILENAME,
                content_type=_PDF_CONTENT_TYPE,
                content=_combine_pdf_bytes(separate),
            )
        )
    return artifacts


def _combine_pdf_bytes(artifacts: list[DocumentConverterStoredArtifact]) -> bytes:
    from pypdf import PdfWriter

    writer = PdfWriter()
    streams: list[io.BytesIO] = []
    try:
        for artifact in artifacts:
            stream = io.BytesIO(artifact.content)
            streams.append(stream)
            writer.append(fileobj=stream, import_outline=False)
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()
    except Exception as exc:
        raise validation_error("Could not combine project preview PDFs.") from exc
    finally:
        for stream in streams:
            stream.close()


def _project_filename_from_url(*, url: str) -> str:
    from weasyprint.urls import FatalURLFetchingError

    parsed = urlsplit(url)
    if parsed.scheme != "project" or parsed.netloc or parsed.query or parsed.fragment:
        raise FatalURLFetchingError("Project assets must use the project scheme.")
    filename = unquote(parsed.path.lstrip("/"))
    path = PurePosixPath(filename)
    if (
        not filename
        or filename != path.name
        or "/" in filename
        or "\\" in filename
        or filename in {".", ".."}
    ):
        raise FatalURLFetchingError("Project assets must resolve by bare filename.")
    return filename


def _decode_text_file(project_file: DocumentConverterProjectUploadedFile) -> str:
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return project_file.content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return project_file.content.decode("utf-8", errors="replace")


def _entry_pdf_filename(*, input_filename: str) -> str:
    safe_name = sanitize_input_filename(input_filename=input_filename)
    stem = PurePosixPath(safe_name).stem or "preview"
    return f"{stem}.pdf"
