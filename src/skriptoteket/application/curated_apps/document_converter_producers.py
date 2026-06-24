"""Document Converter producer routing and local execution services.

Purpose:
    Select the automatic producer for each validated Document Converter item
    and execute the simple local lanes that remain inside the Skriptoteket app
    boundary.

Relationships:
    Used by the Document Converter job handler and Dishka provider graph. It
    depends on central document rendering/extraction protocols and returns the
    shared Document Converter contract models defined by the scoped API module.
"""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJobSpecV2,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterProducerDecision,
    DocumentConverterProducerKind,
    DocumentConverterStoredArtifact,
    build_document_converter_result_filename,
    get_document_converter_output_content_type,
)
from skriptoteket.domain.errors import validation_error
from skriptoteket.protocols.documents import (
    HtmlToPdfRendererProtocol,
    MarkdownToHtmlRendererProtocol,
    PdfTextExtractorProtocol,
)

if TYPE_CHECKING:
    from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
        ConversionHubUpload,
    )


class DocumentConverterProducerPolicy:
    """Choose the local app producer or Sir Convert for one validated item."""

    def __init__(self, *, pdf_text_extractor: PdfTextExtractorProtocol) -> None:
        self._pdf_text_extractor = pdf_text_extractor

    async def decide(
        self,
        *,
        spec: ConversionHubJobSpecV2,
        upload: "ConversionHubUpload",
        correlation_id: str | None,
    ) -> DocumentConverterProducerDecision:
        """Return the automatic producer decision for one upload."""
        del correlation_id
        route = (spec.source_format, spec.output_format)
        if route == (ConversionHubSourceFormatV2.HTML, ConversionHubOutputFormatV2.PDF):
            return _local_decision("local_html_to_pdf")
        if route == (ConversionHubSourceFormatV2.MD, ConversionHubOutputFormatV2.PDF):
            return _local_decision("local_markdown_to_pdf")
        if route == (ConversionHubSourceFormatV2.PDF, ConversionHubOutputFormatV2.MD):
            probe = self._pdf_text_extractor.probe_text(
                file_bytes=upload.file_bytes,
                filename=upload.filename,
            )
            if probe.heavy_reason is not None:
                return _sir_convert_decision(probe.heavy_reason)
            if probe.text is not None:
                return _local_decision("local_pdf_text_to_markdown")
            return _sir_convert_decision("failed_local_pdf_text_extraction")
        return _sir_convert_decision(_sir_convert_route_reason(spec=spec))


class LocalDocumentConverterProducer:
    """Produce first-slice local Document Converter artifacts."""

    def __init__(
        self,
        *,
        html_to_pdf: HtmlToPdfRendererProtocol,
        markdown_to_html: MarkdownToHtmlRendererProtocol,
        pdf_text_extractor: PdfTextExtractorProtocol,
    ) -> None:
        self._html_to_pdf = html_to_pdf
        self._markdown_to_html = markdown_to_html
        self._pdf_text_extractor = pdf_text_extractor

    async def convert(
        self,
        *,
        spec: ConversionHubJobSpecV2,
        upload: "ConversionHubUpload",
        correlation_id: str | None,
    ) -> DocumentConverterStoredArtifact:
        """Convert one upload through a local supported lane."""
        del correlation_id
        route = (spec.source_format, spec.output_format)
        if route == (ConversionHubSourceFormatV2.HTML, ConversionHubOutputFormatV2.PDF):
            html = _decode_text_source(upload=upload)
            return self._pdf_artifact(spec=spec, upload=upload, html=html)
        if route == (ConversionHubSourceFormatV2.MD, ConversionHubOutputFormatV2.PDF):
            markdown_text = _decode_text_source(upload=upload)
            body = self._markdown_to_html.render_markdown(markdown_text=markdown_text)
            return self._pdf_artifact(
                spec=spec,
                upload=upload,
                html=_wrap_markdown_html(body=body, title=upload.filename),
            )
        if route == (ConversionHubSourceFormatV2.PDF, ConversionHubOutputFormatV2.MD):
            text = self._pdf_text_extractor.extract_text(
                file_bytes=upload.file_bytes,
                filename=upload.filename,
            )
            if text is None:
                raise validation_error("Local PDF text extraction failed.")
            return DocumentConverterStoredArtifact(
                filename=build_document_converter_result_filename(
                    input_filename=upload.filename,
                    output_format=ConversionHubOutputFormatV2.MD,
                ),
                content_type=_content_type(ConversionHubOutputFormatV2.MD),
                content=text.encode("utf-8"),
            )
        raise validation_error(
            "Document Converter route is not supported by the local producer.",
            details={
                "source_format": spec.source_format.value,
                "output_format": spec.output_format.value,
            },
        )

    def _pdf_artifact(
        self,
        *,
        spec: ConversionHubJobSpecV2,
        upload: "ConversionHubUpload",
        html: str,
    ) -> DocumentConverterStoredArtifact:
        pdf_bytes = self._html_to_pdf.render_html(html=html)
        return DocumentConverterStoredArtifact(
            filename=build_document_converter_result_filename(
                input_filename=upload.filename,
                output_format=spec.output_format,
            ),
            content_type=_content_type(ConversionHubOutputFormatV2.PDF),
            content=pdf_bytes,
        )


def _local_decision(reason: str) -> DocumentConverterProducerDecision:
    return DocumentConverterProducerDecision(
        producer=DocumentConverterProducerKind.LOCAL,
        reason=reason,
    )


def _sir_convert_decision(reason: str) -> DocumentConverterProducerDecision:
    return DocumentConverterProducerDecision(
        producer=DocumentConverterProducerKind.SIR_CONVERT,
        reason=reason,
    )


def _sir_convert_route_reason(*, spec: ConversionHubJobSpecV2) -> str:
    if spec.source_format is ConversionHubSourceFormatV2.PDF:
        return "heavy_pdf_route"
    if spec.source_format is ConversionHubSourceFormatV2.DOCX:
        return "docx_route_requires_producer"
    if spec.output_format is ConversionHubOutputFormatV2.DOCX:
        return "docx_output_requires_producer"
    return "unsupported_local_route_requires_producer"


def _decode_text_source(*, upload: "ConversionHubUpload") -> str:
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return upload.file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return upload.file_bytes.decode("utf-8", errors="replace")


def _wrap_markdown_html(*, body: str, title: str) -> str:
    safe_title = escape(title)
    return f"""<!doctype html>
<html lang="sv">
  <head>
    <meta charset="utf-8">
    <title>{safe_title}</title>
  </head>
  <body>
    {body}
  </body>
</html>"""


def _content_type(output_format: ConversionHubOutputFormatV2) -> str:
    content_type = get_document_converter_output_content_type(output_format)
    if content_type is None:
        raise validation_error(
            "Document Converter output content type is not supported.",
            details={"output_format": output_format.value},
        )
    return content_type
