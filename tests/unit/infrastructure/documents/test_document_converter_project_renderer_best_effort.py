"""Best-effort renderer tests for Document Converter project previews.

Purpose:
    Prove the HTML/CSS project renderer produces readable temporary PDFs for
    ordinary teacher-authored HTML, including missing linked assets and CSS
    grid layouts rendered by the supported WeasyPrint engine.

Relationships:
    Complements the preview store and fetcher tests by exercising the
    WeasyPrint renderer through the application manifest contract.
"""

from __future__ import annotations

import io
import re

import pytest
from pypdf import PdfReader

from skriptoteket.application.curated_apps.document_converter_projects import (
    DocumentConverterProjectManifest,
    DocumentConverterProjectUploadedFile,
)
from skriptoteket.infrastructure.documents import (
    document_converter_project_previews as preview_module,
)
from skriptoteket.infrastructure.documents.document_converter_project_previews import (
    WeasyPrintDocumentConverterProjectRenderer,
)


def test_project_renderer_renders_best_effort_pdf_for_missing_and_blocked_assets(
    tmp_path,
) -> None:
    renderer = WeasyPrintDocumentConverterProjectRenderer()
    artifacts = renderer.render_project(
        manifest=_manifest(
            html_filename="agnes-leandersson.html",
            css_filename="styles.css",
            image_files=["cover.png"],
        ),
        files=[
            DocumentConverterProjectUploadedFile(
                filename="agnes-leandersson.html",
                content_type="text/html",
                content=(
                    b"<style>h1{background:#18314f;color:#fff;padding:8mm}</style>"
                    b"<link rel='stylesheet' href='project:///styles.css'>"
                    b"<h1>Inline CSS fungerar</h1>"
                    b"<p class='callout'>Uppladdad CSS fungerar</p>"
                    b"<section><img src='project:///cover.png' alt='bild inom projektgransen'>"
                    b"<p>Bild inom projektgransen</p></section>"
                    b"<section><img src='project:///missing.png' alt='saknas'>"
                    b"<h2>Saknad resurs</h2><p>Best effort fortsatter.</p></section>"
                ),
            ),
            DocumentConverterProjectUploadedFile(
                filename="styles.css",
                content_type="text/css",
                content=(
                    b".callout{background:#f47b52;color:#fff;font-weight:700;padding:5mm}"
                    b"@import url('https://example.test/blocked.css');"
                ),
            ),
            DocumentConverterProjectUploadedFile(
                filename="cover.png",
                content_type="image/png",
                content=_fixture_image_bytes(),
            ),
        ],
    )

    assert [artifact.filename for artifact in artifacts] == ["combined.pdf"]
    pdf_path = tmp_path / "preview.pdf"
    pdf_path.write_bytes(artifacts[0].content)
    extracted_text = _extract_pdf_text(artifacts[0].content)

    assert "Inline CSS fungerar" in extracted_text
    assert "Uppladdad CSS fungerar" in extracted_text
    assert "Saknad resurs" in extracted_text
    assert "https://example.test" not in extracted_text
    assert "file:///etc/passwd" not in extracted_text
    assert "nested/cover.png" not in extracted_text

    ratios = _rendered_page_color_ratios(pdf_path=pdf_path)
    assert ratios["navy"] > 0.01
    assert ratios["orange"] > 0.003


def test_project_renderer_renders_grid_heavy_html_on_native_path(
    tmp_path,
) -> None:
    renderer = WeasyPrintDocumentConverterProjectRenderer()
    artifacts = renderer.render_project(
        manifest=_manifest(
            html_filename="agnes-leandersson.html",
            css_filename="styles.css",
            image_files=["cover.png"],
        ),
        files=[
            DocumentConverterProjectUploadedFile(
                filename="agnes-leandersson.html",
                content_type="text/html",
                content=_grid_heavy_html(),
            ),
            DocumentConverterProjectUploadedFile(
                filename="styles.css",
                content_type="text/css",
                content=_grid_heavy_css(),
            ),
            DocumentConverterProjectUploadedFile(
                filename="cover.png",
                content_type="image/png",
                content=_fixture_image_bytes(),
            ),
        ],
    )

    assert [artifact.filename for artifact in artifacts] == ["combined.pdf"]
    pdf_path = tmp_path / "grid-preview.pdf"
    pdf_path.write_bytes(artifacts[0].content)
    compact_text = re.sub(r"\s+", " ", _extract_pdf_text(artifacts[0].content)).strip()

    assert "Grid tung forhandsvisning" in compact_text
    assert "Grid-layout med uppladdad CSS fungerar" in compact_text
    assert "Bild inom projektgransen" in compact_text
    assert "Saknad resurs" in compact_text
    assert "https://example.test" not in compact_text
    assert "file:///etc/passwd" not in compact_text

    ratios = _rendered_page_color_ratios(pdf_path=pdf_path)
    assert ratios["navy"] > 0.01
    assert ratios["orange"] > 0.003
    assert ratios["emerald"] > 0.003
    assert ratios["gold"] > 0.003


def test_project_renderer_renders_teacher_css_grid_layout(tmp_path) -> None:
    renderer = WeasyPrintDocumentConverterProjectRenderer()

    artifacts = renderer.render_project(
        manifest=_manifest(html_filename="grid-heavy-fixture.html", css_filename="grid.css"),
        files=[
            DocumentConverterProjectUploadedFile(
                filename="grid-heavy-fixture.html",
                content_type="text/html",
                content=(
                    b"<link rel='stylesheet' href='project:///grid.css'>"
                    b"<main class='sheet'>"
                    b"<h1>Gridbaserad larar-HTML</h1>"
                    b"<section class='figure-card'>"
                    b"<div class='grid-left'>Forsta gridcellen</div>"
                    b"<div class='grid-right'>Andra gridcellen</div>"
                    b"</section>"
                    b"</main>"
                ),
            ),
            DocumentConverterProjectUploadedFile(
                filename="grid.css",
                content_type="text/css",
                content=(
                    b".sheet{display:grid;gap:10mm;border:1.5mm solid #18314f;padding:10mm}"
                    b".figure-card{display:grid;grid-template-columns:50mm 1fr;"
                    b"gap:8mm;align-items:center}"
                    b".grid-left{min-height:35mm;background:#0e8f5a;color:#fff;padding:5mm}"
                    b".grid-right{min-height:35mm;background:#f47b52;color:#fff;padding:5mm}"
                ),
            ),
        ],
    )

    assert [artifact.filename for artifact in artifacts] == ["combined.pdf"]
    pdf_path = tmp_path / "grid-preview.pdf"
    pdf_path.write_bytes(artifacts[0].content)
    extracted_text = _extract_pdf_text(artifacts[0].content)

    assert "Gridbaserad larar-HTML" in extracted_text
    assert "Forsta gridcellen" in extracted_text
    assert "Andra gridcellen" in extracted_text

    ratios = _rendered_page_color_ratios(pdf_path=pdf_path)
    assert ratios["emerald"] > 0.003
    assert ratios["orange"] > 0.003


def test_project_renderer_forced_grid_fallback_preserves_visible_css_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    original_write = preview_module._write_weasyprint_pdf_bytes

    def fail_once_with_grid_assertion(*, html, css_text, fetcher) -> bytes:
        nonlocal calls
        calls += 1
        if calls == 1:
            _raise_weasyprint_grid_assertion()
        return original_write(html=html, css_text=css_text, fetcher=fetcher)

    monkeypatch.setattr(
        preview_module,
        "_write_weasyprint_pdf_bytes",
        fail_once_with_grid_assertion,
    )
    renderer = WeasyPrintDocumentConverterProjectRenderer()

    artifacts = renderer.render_project(
        manifest=_manifest(
            html_filename="fallback-grid.html",
            css_filename="grid.css",
            image_files=["cover.png"],
        ),
        files=[
            DocumentConverterProjectUploadedFile(
                filename="fallback-grid.html",
                content_type="text/html",
                content=(
                    b"<link rel='stylesheet' href='project:///grid.css'>"
                    b"<main class='sheet' style='display:grid;grid-template-columns:1fr 1fr'>"
                    b"<h1>Fallback bevarar text</h1>"
                    b"<p>Synlig kodtext display:grid ska vara kvar.</p>"
                    b"<img src='file:///etc/passwd.png' alt='blockerad resurs'>"
                    b"</main>"
                ),
            ),
            DocumentConverterProjectUploadedFile(
                filename="grid.css",
                content_type="text/css",
                content=b".sheet{display:grid;grid-template-columns:1fr 1fr;color:#18314f}",
            ),
            DocumentConverterProjectUploadedFile(
                filename="cover.png",
                content_type="image/png",
                content=_fixture_image_bytes(),
            ),
        ],
    )

    assert calls == 2
    assert [artifact.filename for artifact in artifacts] == ["combined.pdf"]
    compact_text = re.sub(r"\s+", " ", _extract_pdf_text(artifacts[0].content)).strip()
    assert "Fallback bevarar text" in compact_text
    assert "display:grid ska vara kvar" in compact_text
    assert "file:///etc/passwd" not in compact_text


def _manifest(
    *,
    html_filename: str,
    css_filename: str,
    image_files: list[str] | None = None,
    output_mode: str = "combined_pdf",
) -> DocumentConverterProjectManifest:
    return DocumentConverterProjectManifest.model_validate(
        {
            "html_entries": [
                {"entry_id": html_filename.removesuffix(".html"), "filename": html_filename}
            ],
            "css_files": [css_filename],
            "image_files": image_files or [],
            "font_files": [],
            "output_mode": output_mode,
            "pdf_controls": {
                "paper_size": "a4",
                "orientation": "portrait",
                "margins": {"top_mm": 12, "right_mm": 12, "bottom_mm": 12, "left_mm": 12},
                "template_id": "academic_phd",
            },
        }
    )


def _raise_weasyprint_grid_assertion() -> None:
    code = compile(
        "raise AssertionError('grid layout crash')",
        "/app/__pypackages__/3.13/lib/weasyprint/layout/grid.py",
        "exec",
    )
    exec(code, {})


def _grid_heavy_html() -> bytes:
    return (
        b"<!doctype html><html lang='sv'><head><meta charset='utf-8'>"
        b"<title>Grid tungt projekt</title>"
        b"<style>"
        b"h1{margin:0;padding:6mm 7mm;background:#18314f;color:#fff;font-size:24pt;}"
        b".lede{margin:0;border-left:3mm solid #18314f;padding-left:4mm;font-size:13pt;}"
        b"</style>"
        b"<link rel='stylesheet' href='project:///styles.css'>"
        b"</head><body><main class='sheet'>"
        b"<h1>Grid tung forhandsvisning</h1>"
        b"<p class='lede'>Ordinarie HTML och CSS med grid ska fortfarande ge en lasbar PDF.</p>"
        b"<p class='callout'>Grid-layout med uppladdad CSS fungerar</p>"
        b"<section class='figure-card'>"
        b"<img class='card-image' src='project:///cover.png' alt='Bild inom projektgransen'>"
        b"<div class='card-copy'><h2>Representativt projekt</h2>"
        b"<p class='caption'>Bild inom projektgransen</p>"
        b"<ul><li>Inline CSS rubrik</li><li>Uppladdad CSS accentpanel</li>"
        b"<li>Grid-kort med bild</li></ul></div></section>"
        b"<section class='missing-card'>"
        b"<img class='card-image' src='project:///saknas.png' alt='Saknad resurs'>"
        b"<div class='card-copy'><h2>Saknad resurs</h2>"
        b"<p>Best effort fortsatter trots saknad bild.</p></div></section>"
        b"<img class='blocked-probe' src='https://example.test/blocked.png' alt='Blockerad resurs'>"
        b"<img class='blocked-probe' src='file:///etc/passwd.png' alt='Filsystemresurs'>"
        b"</main></body></html>"
    )


def _grid_heavy_css() -> bytes:
    return (
        b":root{color-scheme:light}"
        b"body{margin:0;padding:18mm;font-family:'Aptos','Inter',Arial,sans-serif;"
        b"color:#18314f;background:#f4efe7}"
        b".sheet{display:grid;gap:10mm;border:1.5mm solid #18314f;padding:10mm;background:#fff}"
        b".callout{margin:0;padding:5mm 6mm;background:#f47b52;color:#fff;"
        b"font-size:14pt;font-weight:700}"
        b".figure-card,.missing-card{display:grid;grid-template-columns:50mm 1fr;"
        b"gap:8mm;align-items:center;border:1.2mm solid #f47b52;padding:6mm}"
        b".figure-card h2,.missing-card h2{margin:0 0 3mm;color:#18314f}"
        b".caption{display:inline-block;margin:0 0 4mm;padding:2.5mm 4mm;"
        b"border:0.8mm solid #18314f;font-weight:700}"
        b".card-image{width:50mm;height:38mm;object-fit:cover;border:1mm solid #18314f}"
        b".blocked-probe{display:none}"
        b"ul{margin:0;padding-left:5mm}"
        b"li+li{margin-top:2mm}"
    )


def _extract_pdf_text(pdf_content: bytes) -> str:
    return " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_content)).pages)


def _rendered_page_color_ratios(*, pdf_path) -> dict[str, float]:
    import pypdfium2 as pdfium  # type: ignore[import-untyped]

    document = pdfium.PdfDocument(str(pdf_path))
    bitmap = document[0].render(scale=2, optimize_mode="print", rev_byteorder=True)
    image = bitmap.to_pil().convert("RGB")
    width, height = image.size
    total_pixels = width * height
    navy_pixels = 0
    orange_pixels = 0
    emerald_pixels = 0
    gold_pixels = 0
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            red, green, blue = pixels[x, y]
            if red < 70 and green < 90 and blue > 70:
                navy_pixels += 1
            if red > 190 and 80 < green < 170 and blue < 120:
                orange_pixels += 1
            if red < 90 and green > 100 and blue < 120:
                emerald_pixels += 1
            if red > 170 and green > 130 and blue < 110:
                gold_pixels += 1
    image.close()
    return {
        "navy": navy_pixels / total_pixels,
        "orange": orange_pixels / total_pixels,
        "emerald": emerald_pixels / total_pixels,
        "gold": gold_pixels / total_pixels,
    }


def _fixture_image_bytes() -> bytes:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (240, 180), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 119, 179), fill=(14, 143, 90))
    draw.rectangle((120, 0, 239, 179), fill=(216, 177, 47))
    draw.ellipse((70, 34, 170, 144), fill=(24, 49, 79))
    draw.rectangle((20, 130, 220, 154), fill=(255, 255, 255))
    draw.line((24, 141, 216, 141), fill=(24, 49, 79), width=5)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
