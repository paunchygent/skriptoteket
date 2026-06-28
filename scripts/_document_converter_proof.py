"""Document Converter proof helpers for authenticated route verification.

Domain purpose:
    Build representative HTML/CSS project fixtures and verify that the
    authenticated Document Converter route renders a real best-effort PDF.

Relationships:
    Used by `scripts/authenticated_home_work_apps.py` and kept separate so
    the route proof entrypoint stays within the repo file-size budget.
"""

from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path

from playwright.sync_api import Locator, Page, expect

from scripts._playwright_touch import pinch_zoom

JsonObject = dict[str, object]

DOCUMENT_CONVERTER_FIXTURE_HTML = "agnes-leandersson.html"
DOCUMENT_CONVERTER_FIXTURE_HEADING = "PR-0388 synlig PDF-förhandsvisning"
DOCUMENT_CONVERTER_FIXTURE_CALLOUT = "CSS-länk aktiv i projektpaketet"
DOCUMENT_CONVERTER_FIXTURE_CAPTION = "Bild inom projektgränsen"
DOCUMENT_CONVERTER_FIXTURE_MISSING = "Saknad resurs"
PREVIEW_VIEWPORT_SELECTOR = '[data-testid="document-converter-pdf-viewport"]'


def build_document_converter_fixture_files(artifact_dir: Path) -> list[str]:
    """Write the representative PR-0388 fixture files and return their paths."""
    fixture_dir = artifact_dir / "document-converter-fixture"
    fixture_dir.mkdir(exist_ok=True)
    html_path = fixture_dir / DOCUMENT_CONVERTER_FIXTURE_HTML
    css_path = fixture_dir / "styles.css"
    image_path = fixture_dir / "cover.png"
    _write_fixture_image(image_path)
    html_path.write_text(
        "<!doctype html>"
        "<html lang='sv'>"
        "<head>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>PR-0388 proof fixture</title>"
        "<style>"
        "h1{margin:0;padding:6mm 7mm;background:#18314f;color:#ffffff;font-size:24pt;}"
        ".lede{margin:0;border-left:3mm solid #18314f;padding-left:4mm;font-size:13pt;}"
        "</style>"
        "<link rel='stylesheet' href='project:///styles.css'>"
        "</head>"
        "<body>"
        "<main class='sheet'>"
        f"<h1>{DOCUMENT_CONVERTER_FIXTURE_HEADING}</h1>"
        "<p class='lede'>Automatisk förhandsvisning ska visa en verklig PDF med länkad CSS, inline CSS och bild.</p>"
        f"<p class='callout'>{DOCUMENT_CONVERTER_FIXTURE_CALLOUT}</p>"
        "<section class='figure-card'>"
        "<img class='card-image' src='project:///cover.png' alt='Omslagsbild inom projektgränsen'>"
        "<div class='card-copy'>"
        "<h2>Representativt projekt</h2>"
        f"<p class='caption'>{DOCUMENT_CONVERTER_FIXTURE_CAPTION}</p>"
        "<ul>"
        "<li>Distinkt rubrikyta från inline CSS</li>"
        "<li>Accentpanel från uppladdad CSS</li>"
        "<li>Länkad PNG inom den uppladdade projektgränsen</li>"
        "</ul>"
        "</div>"
        "</section>"
        "<section class='missing-card'>"
        "<img class='card-image' src='project:///saknas.png' alt='Saknad resurs'>"
        "<div class='card-copy'>"
        f"<h2>{DOCUMENT_CONVERTER_FIXTURE_MISSING}</h2>"
        "<p>Best-effort-förhandsvisning fortsätter när en bild saknas.</p>"
        "</div>"
        "</section>"
        "</main>"
        "</body>"
        "</html>",
        encoding="utf-8",
    )
    css_path.write_text(
        ":root { color-scheme: light; }\n"
        "body {\n"
        "  margin: 0;\n"
        "  padding: 18mm;\n"
        "  font-family: 'Aptos', 'Inter', Arial, sans-serif;\n"
        "  color: #18314f;\n"
        "  background: #f4efe7;\n"
        "}\n"
        ".sheet {\n"
        "  display: grid;\n"
        "  gap: 10mm;\n"
        "  border: 1.5mm solid #18314f;\n"
        "  padding: 10mm;\n"
        "  background: #ffffff;\n"
        "}\n"
        ".callout {\n"
        "  margin: 0;\n"
        "  padding: 5mm 6mm;\n"
        "  background: #f47b52;\n"
        "  color: #ffffff;\n"
        "  font-size: 14pt;\n"
        "  font-weight: 700;\n"
        "}\n"
        ".figure-card,\n"
        ".missing-card {\n"
        "  display: grid;\n"
        "  grid-template-columns: 50mm 1fr;\n"
        "  gap: 8mm;\n"
        "  align-items: center;\n"
        "  border: 1.2mm solid #f47b52;\n"
        "  padding: 6mm;\n"
        "}\n"
        ".figure-card h2,\n"
        ".missing-card h2 {\n"
        "  margin: 0 0 3mm;\n"
        "  color: #18314f;\n"
        "}\n"
        ".caption {\n"
        "  display: inline-block;\n"
        "  margin: 0 0 4mm;\n"
        "  padding: 2.5mm 4mm;\n"
        "  border: 0.8mm solid #18314f;\n"
        "  font-weight: 700;\n"
        "}\n"
        ".card-image {\n"
        "  width: 50mm;\n"
        "  height: 38mm;\n"
        "  object-fit: cover;\n"
        "  border: 1mm solid #18314f;\n"
        "}\n"
        "ul {\n"
        "  margin: 0;\n"
        "  padding-left: 5mm;\n"
        "}\n"
        "li + li {\n"
        "  margin-top: 2mm;\n"
        "}\n",
        encoding="utf-8",
    )
    return [str(html_path), str(css_path), str(image_path)]


def assert_document_converter_route(
    page: Page,
    *,
    artifact_dir: Path,
    viewport_label: str,
) -> JsonObject:
    """Prove the live authenticated Document Converter route meets PR-0388."""
    page.locator('[data-testid="home-work-app-document-converter"]').click()
    expect(page).to_have_url(re.compile(r"/apps/document-converter$"))
    route = page.locator('main[aria-label="Dokumentkonverterare"]')
    expect(route).to_be_visible()

    download_button = route.get_by_test_id("document-converter-download")
    save_button = route.get_by_test_id("document-converter-save")
    frame = route.get_by_test_id("document-converter-pdf-frame")

    expect(route.get_by_text("Exportera som", exact=True)).to_be_visible()
    expect(route.get_by_text("Enskilda PDF-filer", exact=True)).to_be_visible()
    expect(route.get_by_text("Kombinerad PDF", exact=True)).to_be_visible()
    expect(route.get_by_text("Mall", exact=True)).to_have_count(0)
    expect(route.get_by_text("Lägg till fil", exact=True)).to_have_count(0)
    expect(route.get_by_text("Dra filer hit eller klicka", exact=True)).to_be_visible()
    expect(route.get_by_text("Tillfällig förhandsvisning", exact=True)).to_have_count(0)
    expect(route.get_by_text("Förhandsvisa", exact=True)).to_have_count(0)
    expect(route.get_by_text("Ta bort", exact=True)).to_have_count(0)
    expect(route.locator('[aria-label="Status"]')).to_have_count(0)
    expect(route.get_by_test_id("document-converter-retry")).to_have_count(0)
    expect(download_button).to_be_disabled()
    expect(save_button).to_be_disabled()

    preview_request_path = (
        "/api/v1/apps/documents.conversion_hub/document-converter/project-previews"
    )
    with page.expect_response(
        lambda response: preview_request_path in response.url and response.request.method == "POST",
        timeout=45_000,
    ) as preview_response_info:
        page.locator('[data-testid="document-converter-file-input"]').set_input_files(
            build_document_converter_fixture_files(artifact_dir)
        )

    preview_response = preview_response_info.value
    if preview_response.status != 200:
        response_path = artifact_dir / "document-converter-preview-response.json"
        response_body: str
        try:
            response_body = preview_response.text()
        except Exception as exc:  # pragma: no cover - live-proof fallback
            response_body = f"<unavailable: {type(exc).__name__}: {exc}>"
        response_path.write_text(
            json.dumps(
                {
                    "body": response_body,
                    "headers": dict(preview_response.headers),
                    "status": preview_response.status,
                    "url": preview_response.url,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        raise AssertionError(
            "Document Converter project preview request failed with "
            f"{preview_response.status}. See {response_path}."
        )

    expect(route.locator(".dc-preview-header h2")).to_contain_text("agnes-leandersson")
    expect(frame).to_be_visible(timeout=45_000)
    expect(download_button).to_be_enabled(timeout=45_000)
    expect(save_button).to_be_enabled(timeout=45_000)
    zoom_controls = _assert_preview_zoom_controls(page, route)

    first_frame_src = frame.get_attribute("src")
    if not first_frame_src or not first_frame_src.startswith("blob:"):
        raise AssertionError(f"Expected a blob-backed preview iframe, got {first_frame_src!r}.")

    page.locator('[data-test="document-converter-output-combined_pdf"]').click()
    page.wait_for_function(
        """([selector, previous]) => {
            const element = document.querySelector(selector);
            return Boolean(
                element &&
                element.getAttribute("src") &&
                element.getAttribute("src") !== previous
            );
        }""",
        arg=['[data-testid="document-converter-pdf-frame"]', first_frame_src],
        timeout=45_000,
    )
    expect(download_button).to_be_enabled(timeout=45_000)
    expect(save_button).to_be_enabled(timeout=45_000)

    second_frame_src = frame.get_attribute("src")
    if not second_frame_src or second_frame_src == first_frame_src:
        raise AssertionError("Document Converter refresh did not replace the preview iframe URL.")

    downloaded_preview_pdf = _download_preview_pdf(
        page,
        artifact_dir=artifact_dir,
        viewport_label=viewport_label,
    )
    downloaded_preview_png = _render_pdf_first_page_png(pdf_path=downloaded_preview_pdf)
    rendered_preview = _inspect_rendered_preview(
        pdf_path=downloaded_preview_pdf,
        png_path=downloaded_preview_png,
    )
    if not rendered_preview["contains_expected_heading_text"]:
        raise AssertionError("Downloaded preview PDF did not contain the expected heading text.")
    if not rendered_preview["contains_expected_callout_text"]:
        raise AssertionError(
            "Downloaded preview PDF did not contain the expected CSS callout text."
        )
    if not rendered_preview["contains_expected_caption_text"]:
        raise AssertionError(
            "Downloaded preview PDF did not contain the expected image caption text."
        )
    if not rendered_preview["contains_missing_resource_text"]:
        raise AssertionError(
            "Downloaded preview PDF did not contain the expected missing-resource text."
        )
    if not rendered_preview["visually_nonblank"]:
        raise AssertionError("Rendered preview PNG was blank or near-blank.")
    if not rendered_preview["css_accents_visible"]:
        raise AssertionError(
            "Rendered preview PNG did not preserve the expected CSS accent colors."
        )
    if not rendered_preview["image_accents_visible"]:
        raise AssertionError(
            "Rendered preview PNG did not preserve the linked image accent colors."
        )

    return {
        "document_converter_forbidden_surfaces_absent": True,
        "document_converter_initial_download_disabled": True,
        "document_converter_initial_save_disabled": True,
        "document_converter_preview_enabled_after_auto_render": True,
        "document_converter_refresh_replaced_iframe_src": True,
        "document_converter_zoom_controls_working": True,
        "grid_layout_fixture_rendered": True,
        "document_converter_pdf_viewer_dom_inspection_supported": False,
        "document_converter_pdf_viewer_check_strategy": (
            "download-current-preview-and-render-page-1-to-png"
        ),
        "fixture_html_filename": DOCUMENT_CONVERTER_FIXTURE_HTML,
        "first_frame_src": first_frame_src,
        "preview_zoom_controls": zoom_controls,
        "second_frame_src": second_frame_src,
        "rendered_preview": rendered_preview,
    }


def _assert_preview_zoom_controls(page: Page, route: Locator) -> JsonObject:
    viewport = route.get_by_test_id("document-converter-pdf-viewport")
    zoom_out = route.get_by_test_id("document-converter-preview-zoom-out")
    zoom_in = route.get_by_test_id("document-converter-preview-zoom-in")
    fit = route.get_by_test_id("document-converter-preview-fit")
    label = route.get_by_test_id("document-converter-preview-zoom-label")

    expect(viewport).to_be_visible()
    expect(zoom_out).to_be_visible()
    expect(zoom_in).to_be_visible()
    expect(fit).to_be_visible()
    expect(label).to_be_visible()

    touch_action = viewport.evaluate("(element) => window.getComputedStyle(element).touchAction")
    if touch_action == "none":
        raise AssertionError("Document Converter PDF preview blocks touch panning.")
    native_listener_contract = _inspect_preview_native_gesture_listeners(page)

    initial_label = label.inner_text()
    zoom_in.click()
    expect(label).not_to_have_text(initial_label)
    zoomed_label = label.inner_text()
    zoom_out.click()
    expect(label).not_to_have_text(zoomed_label)
    zoom_out_label = label.inner_text()
    fit.click()
    expect(label).to_have_text(initial_label)
    fit_layout = _inspect_preview_fit_layout(viewport)
    touch_probe = _assert_preview_touch_ownership(page, viewport)
    fit.click()
    expect(label).to_have_text(initial_label)

    return {
        "fit_label": initial_label,
        "fit_layout": fit_layout,
        "native_listener_contract": native_listener_contract,
        "touch_action": touch_action,
        "touch_probe": touch_probe,
        "zoomed_label": zoomed_label,
        "zoom_out_label": zoom_out_label,
    }


def _inspect_preview_native_gesture_listeners(page: Page) -> JsonObject:
    client = page.context.new_cdp_session(page)
    try:
        evaluation = client.send(
            "Runtime.evaluate",
            {
                "expression": f"document.querySelector({json.dumps(PREVIEW_VIEWPORT_SELECTOR)})",
                "returnByValue": False,
            },
        )
        object_id = evaluation.get("result", {}).get("objectId")
        if not object_id:
            raise AssertionError(
                "Document Converter preview viewport did not resolve for CDP inspection."
            )
        listeners = client.send(
            "DOMDebugger.getEventListeners",
            {"objectId": object_id},
        ).get("listeners", [])
    finally:
        client.detach()

    expected_types = {
        "gesturechange",
        "gestureend",
        "gesturestart",
        "touchcancel",
        "touchend",
        "touchmove",
        "touchstart",
    }
    relevant_listeners = [
        {
            "passive": listener.get("passive"),
            "type": listener.get("type"),
            "useCapture": listener.get("useCapture"),
        }
        for listener in listeners
        if listener.get("type") in expected_types
    ]
    actual_types = {str(listener["type"]) for listener in relevant_listeners}
    if actual_types != expected_types:
        raise AssertionError(
            "Document Converter preview native gesture listeners were incomplete: "
            f"{sorted(actual_types)!r}."
        )
    passive_false_types = {
        str(listener["type"]) for listener in relevant_listeners if listener.get("passive") is False
    }
    if passive_false_types != expected_types:
        raise AssertionError(
            "Document Converter preview native gesture listeners were not all non-passive: "
            f"{sorted(passive_false_types)!r}."
        )

    return {
        "passive_false_types": sorted(passive_false_types),
        "types": sorted(actual_types),
    }


def _inspect_preview_fit_layout(viewport: Locator) -> JsonObject:
    layout = viewport.evaluate(
        """(element) => {
            const surface = element.querySelector('[data-testid="document-converter-pdf-surface"]');
            const stage = element.querySelector('[data-testid="document-converter-pdf-stage"]');
            if (!(surface instanceof HTMLElement) || !(stage instanceof HTMLElement)) {
                throw new Error("Missing Document Converter fit layout nodes.");
            }
            const viewportRect = element.getBoundingClientRect();
            const surfaceRect = surface.getBoundingClientRect();
            const leftInset = surfaceRect.left - viewportRect.left;
            const rightInset = viewportRect.right - surfaceRect.right;
            const topInset = surfaceRect.top - viewportRect.top;
            const bottomInset = viewportRect.bottom - surfaceRect.bottom;
            return {
                bottom_inset: bottomInset,
                height_ratio: viewportRect.height > 0 ? surfaceRect.height / viewportRect.height : 0,
                left_inset: leftInset,
                right_inset: rightInset,
                stage_contained: stage.classList.contains("dc-pdf-stage--contained"),
                top_inset: topInset,
                viewport_height: viewportRect.height,
                viewport_width: viewportRect.width,
                width_ratio: viewportRect.width > 0 ? surfaceRect.width / viewportRect.width : 0,
            };
        }"""
    )
    if not layout["stage_contained"]:
        raise AssertionError(
            "Document Converter fit mode did not mark the preview stage as contained."
        )

    width_ratio = float(layout["width_ratio"])
    height_ratio = float(layout["height_ratio"])
    if max(width_ratio, height_ratio) < 0.98:
        raise AssertionError(
            "Document Converter fit mode left the preview underfilled on both axes."
        )

    left_inset = float(layout["left_inset"])
    right_inset = float(layout["right_inset"])
    top_inset = float(layout["top_inset"])
    bottom_inset = float(layout["bottom_inset"])
    width_underfills = width_ratio < 0.98
    height_underfills = height_ratio < 0.98

    if width_underfills and abs(left_inset - right_inset) > 2:
        raise AssertionError(
            "Document Converter fit mode left the preview horizontally biased instead of centered."
        )
    if height_underfills and abs(top_inset - bottom_inset) > 2:
        raise AssertionError(
            "Document Converter fit mode left the preview vertically biased instead of centered."
        )

    return layout


def _assert_preview_touch_ownership(page: Page, viewport: Locator) -> JsonObject:
    label = page.get_by_test_id("document-converter-preview-zoom-label")
    initial_label = label.inner_text()
    max_touch_points = int(page.evaluate("navigator.maxTouchPoints || 0"))
    native_pinch_result: JsonObject = {
        "attempted": max_touch_points > 0,
        "max_touch_points": max_touch_points,
    }
    if max_touch_points > 0:
        pinch_zoom(page, PREVIEW_VIEWPORT_SELECTOR, start_distance=100, end_distance=200)
        expect(label).not_to_have_text(initial_label)
        native_pinch_result["zoomed_label"] = label.inner_text()
    else:
        native_pinch_result["skipped_reason"] = "touch-input-not-enabled-for-this-viewport"

    platform_probe = viewport.evaluate(
        """async (element) => {
            const label = document.querySelector('[data-testid="document-converter-preview-zoom-label"]');
            if (!label) throw new Error("Missing Document Converter preview zoom label.");
            const afterFrame = async () => {
                await new Promise((resolve) => window.requestAnimationFrame(resolve));
                await new Promise((resolve) => window.requestAnimationFrame(resolve));
            };
            const makeGestureEvent = (type, scale) => {
                const event = new Event(type, { bubbles: true, cancelable: true });
                Object.defineProperty(event, "scale", { configurable: true, value: scale });
                Object.defineProperty(event, "clientX", { configurable: true, value: 110 });
                Object.defineProperty(event, "clientY", { configurable: true, value: 150 });
                return event;
            };
            const makeTouchList = (points) => {
                const list = { item: (index) => list[index] ?? null, length: points.length };
                points.forEach((point, index) => { list[index] = point; });
                return list;
            };
            const makeTouchMove = (points) => {
                const event = new Event("touchmove", { bubbles: true, cancelable: true });
                Object.defineProperty(event, "touches", { configurable: true, value: makeTouchList(points) });
                return event;
            };
            const initialLabel = label.textContent.trim();
            const oneFingerMove = makeTouchMove([{ clientX: 48, clientY: 128 }]);
            element.dispatchEvent(oneFingerMove);
            const gestureStart = makeGestureEvent("gesturestart", 1);
            const gestureChange = makeGestureEvent("gesturechange", 1.15);
            const gestureEnd = makeGestureEvent("gestureend", 1.15);
            element.dispatchEvent(gestureStart);
            element.dispatchEvent(gestureChange);
            element.dispatchEvent(gestureEnd);
            await afterFrame();
            element.scrollTop = 0;
            element.scrollLeft = 0;
            const scrollHeight = element.scrollHeight;
            const clientHeight = element.clientHeight;
            element.scrollTop = 32;
            element.scrollLeft = 12;
            return {
                client_height: clientHeight, gesture_change_prevented: gestureChange.defaultPrevented, gesture_end_prevented: gestureEnd.defaultPrevented,
                gesture_label: label.textContent.trim(), gesture_start_prevented: gestureStart.defaultPrevented, initial_label: initialLabel,
                one_finger_move_prevented: oneFingerMove.defaultPrevented, scroll_height: scrollHeight, scroll_left_after_set: element.scrollLeft, scroll_top_after_set: element.scrollTop,
            };
        }"""
    )
    if platform_probe["one_finger_move_prevented"]:
        raise AssertionError("Document Converter PDF preview intercepts one-finger touch panning.")
    if (
        not platform_probe["gesture_start_prevented"]
        or not platform_probe["gesture_change_prevented"]
    ):
        raise AssertionError(
            "Document Converter PDF preview did not claim Safari-style platform gestures."
        )
    if platform_probe["gesture_label"] == platform_probe["initial_label"]:
        raise AssertionError("Document Converter PDF preview platform gesture did not change zoom.")
    if (
        platform_probe["scroll_height"] > platform_probe["client_height"]
        and platform_probe["scroll_top_after_set"] <= 0
    ):
        raise AssertionError("Document Converter PDF preview did not remain vertically scrollable.")
    return {
        "native_pinch": native_pinch_result,
        "platform_probe": platform_probe,
    }


def _write_fixture_image(path: Path) -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (240, 180), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 119, 179), fill=(14, 143, 90))
    draw.rectangle((120, 0, 239, 179), fill=(216, 177, 47))
    draw.ellipse((70, 34, 170, 144), fill=(24, 49, 79))
    draw.rectangle((20, 130, 220, 154), fill=(255, 255, 255))
    draw.line((24, 141, 216, 141), fill=(24, 49, 79), width=5)
    image.save(path, format="PNG")


def _download_preview_pdf(
    page: Page,
    *,
    artifact_dir: Path,
    viewport_label: str,
) -> Path:
    download_button = page.get_by_test_id("document-converter-download")
    expect(download_button).to_be_enabled(timeout=45_000)
    with page.expect_download(timeout=45_000) as download_info:
        download_button.click()
    download = download_info.value
    output_path = artifact_dir / f"document-converter-preview-{viewport_label}.pdf"
    download.save_as(str(output_path))
    return output_path


def _render_pdf_first_page_png(*, pdf_path: Path) -> Path:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(str(pdf_path))
    if len(document) < 1:
        raise AssertionError(f"Preview download {pdf_path} contained no pages.")
    page = document[0]
    bitmap = page.render(scale=2, optimize_mode="print", rev_byteorder=True)
    image = bitmap.to_pil().copy()
    png_path = pdf_path.with_suffix(".page-1.png")
    image.save(png_path)
    image.close()
    return png_path


def _inspect_rendered_preview(*, pdf_path: Path, png_path: Path) -> JsonObject:
    from PIL import Image
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    compact_text = re.sub(r"\s+", " ", extracted_text).strip()
    image = Image.open(png_path).convert("RGB")
    width, height = image.size
    total_pixels = width * height
    non_white = 0
    navy_pixels = 0
    orange_pixels = 0
    emerald_pixels = 0
    gold_pixels = 0
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            red, green, blue = pixels[x, y]
            if red < 245 or green < 245 or blue < 245:
                non_white += 1
            if red < 70 and green < 90 and blue > 70:
                navy_pixels += 1
            if red > 190 and 80 < green < 170 and blue < 120:
                orange_pixels += 1
            if red < 90 and green > 100 and blue < 120:
                emerald_pixels += 1
            if red > 170 and green > 130 and blue < 110:
                gold_pixels += 1
    image.close()
    non_white_ratio = non_white / total_pixels
    navy_ratio = navy_pixels / total_pixels
    orange_ratio = orange_pixels / total_pixels
    emerald_ratio = emerald_pixels / total_pixels
    gold_ratio = gold_pixels / total_pixels
    return {
        "pdf_path": str(pdf_path),
        "pdf_sha256": sha256(pdf_path.read_bytes()).hexdigest(),
        "first_page_png_path": str(png_path),
        "first_page_png_sha256": sha256(png_path.read_bytes()).hexdigest(),
        "page_count": len(reader.pages),
        "text_excerpt": compact_text[:500],
        "contains_expected_heading_text": (
            "PR-0388 synlig PDF" in compact_text and "förhandsvisning" in compact_text
        ),
        "contains_expected_callout_text": DOCUMENT_CONVERTER_FIXTURE_CALLOUT in compact_text,
        "contains_expected_caption_text": DOCUMENT_CONVERTER_FIXTURE_CAPTION in compact_text,
        "contains_missing_resource_text": (
            "Bild saknas" in compact_text or DOCUMENT_CONVERTER_FIXTURE_MISSING in compact_text
        ),
        "contains_raw_external_url_text": "https://example.test" in compact_text,
        "contains_raw_file_path_text": "file:///etc/passwd" in compact_text,
        "visual_non_white_ratio": round(non_white_ratio, 4),
        "navy_pixel_ratio": round(navy_ratio, 4),
        "orange_pixel_ratio": round(orange_ratio, 4),
        "emerald_pixel_ratio": round(emerald_ratio, 4),
        "gold_pixel_ratio": round(gold_ratio, 4),
        "visually_nonblank": non_white_ratio > 0.03,
        "css_accents_visible": navy_ratio > 0.01 and orange_ratio > 0.003,
        "image_accents_visible": emerald_ratio > 0.003 and gold_ratio > 0.003,
    }
