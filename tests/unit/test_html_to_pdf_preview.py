from __future__ import annotations

import json
from pathlib import Path

import pytest

from skriptoteket.script_bank.scripts import html_to_pdf_preview


def _find_table_output(payload: dict[str, object], *, title: str) -> dict[str, object]:
    outputs = payload.get("outputs")
    assert isinstance(outputs, list)
    for out in outputs:
        if not isinstance(out, dict):
            continue
        if out.get("kind") == "table" and out.get("title") == title:
            return out
    raise AssertionError(f"Missing table output with title: {title}")


@pytest.mark.unit
def test_build_page_css_sets_margin_zero_and_normalizes_page_size() -> None:
    css_a4 = html_to_pdf_preview._build_page_css(
        page_size="a4",
        orientation="portrait",
    )
    assert "size: A4 portrait" in css_a4
    assert "margin: 0" in css_a4
    assert "details > :not(summary)" in css_a4
    assert ".sidebar { display: none" in css_a4
    assert "overflow: visible" in css_a4
    assert ".card, .diagram" in css_a4
    assert "max-height" in css_a4

    css_letter = html_to_pdf_preview._build_page_css(
        page_size="letter",
        orientation="landscape",
    )
    assert "size: Letter landscape" in css_letter
    assert "margin: 0" in css_letter


@pytest.mark.unit
def test_force_details_open_adds_open_attribute() -> None:
    html = "<html><body><details><summary>x</summary><div>y</div></details></body></html>"
    updated = html_to_pdf_preview._force_details_open(html=html)
    assert "<details open>" in updated


@pytest.mark.unit
def test_force_details_open_does_not_duplicate_open_attribute() -> None:
    html = (
        "<html><body><details open><summary>x</summary><div>y</div></details>"
        '<details open="open"><summary>a</summary><div>b</div></details>'
        "</body></html>"
    )
    updated = html_to_pdf_preview._force_details_open(html=html)
    assert updated.count("<details open") == 2


@pytest.mark.unit
def test_inject_author_css_inserts_before_head_close() -> None:
    html = "<html><head><title>x</title></head><body>y</body></html>"
    css = "body { color: red; }"
    updated = html_to_pdf_preview._inject_author_css(html=html, css=css)
    assert "<style>" in updated
    assert css in updated
    assert updated.index("<style>") < updated.index("</head>")


@pytest.mark.unit
def test_rewrite_details_to_divs_removes_summary_tags() -> None:
    html = "<html><body><details><summary>Title</summary><div>Body</div></details></body></html>"
    updated = html_to_pdf_preview._rewrite_details_to_divs(html=html)
    assert "<details" not in updated
    assert "</details>" not in updated
    assert "<summary" not in updated
    assert "</summary>" not in updated
    assert 'class="pdf-details"' in updated
    assert 'class="pdf-summary"' in updated


@pytest.mark.unit
def test_inline_css_into_svgs_inserts_style_tag_inside_svg(tmp_path: Path) -> None:
    html = (
        "<html><head><style>.node{fill:red}</style></head><body>"
        '<svg viewBox="0 0 10 10"><rect class="node"/></svg>'
        "</body></html>"
    )
    updated = html_to_pdf_preview._inline_css_into_svgs(html=html, base_dir=tmp_path)
    assert "<svg" in updated
    assert "<style" in updated
    assert ".node{fill:red}" in updated
    svg_start = updated.index("<svg")
    svg_end = updated.index("</svg>")
    style_pos = updated.index("<style", svg_start)
    assert style_pos < svg_end


@pytest.mark.unit
def test_inline_css_into_svgs_includes_linked_css_and_imports(tmp_path: Path) -> None:
    base_dir = tmp_path
    (base_dir / "a.css").write_text(".from_a{fill:green}\n@import 'b.css';", encoding="utf-8")
    (base_dir / "b.css").write_text(".from_b{stroke:blue}", encoding="utf-8")

    html = (
        "<html><head>"
        '<link rel="stylesheet" href="a.css">'
        "</head><body>"
        '<svg viewBox="0 0 10 10"><rect class="from_a"/></svg>'
        "</body></html>"
    )
    updated = html_to_pdf_preview._inline_css_into_svgs(html=html, base_dir=base_dir)
    assert ".from_a{fill:green}" in updated
    assert ".from_b{stroke:blue}" in updated


@pytest.mark.unit
def test_inline_css_into_svgs_ignores_remote_stylesheets(tmp_path: Path) -> None:
    html = (
        "<html><head>"
        '<link rel="stylesheet" href="https://example.com/a.css">'
        "</head><body>"
        '<svg viewBox="0 0 10 10"><rect/></svg>'
        "</body></html>"
    )
    updated = html_to_pdf_preview._inline_css_into_svgs(html=html, base_dir=tmp_path)
    assert '<style type="text/css">' not in updated


@pytest.mark.unit
def test_select_print_css_skips_injection_when_document_defines_at_page(
    tmp_path: Path,
) -> None:
    css_path = tmp_path / "debate_card_style.css"
    css_path.write_text("@page { margin: 12mm; }\nbody { color: black; }", encoding="utf-8")

    html = (
        '<html><head><link rel="stylesheet" href="debate_card_style.css"></head>'
        '<body><div class="page">x</div></body></html>'
    )
    css, is_tool_editor = html_to_pdf_preview._select_print_css_for_document(
        html=html,
        base_dir=tmp_path,
        page_size="a4",
        orientation="portrait",
    )
    assert css == ""
    assert is_tool_editor is False


@pytest.mark.unit
def test_select_print_css_injects_size_only_when_no_at_page(tmp_path: Path) -> None:
    html = "<html><head><style>body { color: black; }</style></head><body>x</body></html>"
    css, is_tool_editor = html_to_pdf_preview._select_print_css_for_document(
        html=html,
        base_dir=tmp_path,
        page_size="a4",
        orientation="portrait",
    )
    assert "@page" in css
    assert "size: A4 portrait" in css
    assert "margin:" not in css
    assert is_tool_editor is False


@pytest.mark.unit
def test_select_print_css_uses_tool_editor_overrides_when_detected(tmp_path: Path) -> None:
    html = (
        "<html><head><style>.app{display:grid}</style></head>"
        '<body><div class="app"><aside class="sidebar"></aside></div></body></html>'
    )
    css, is_tool_editor = html_to_pdf_preview._select_print_css_for_document(
        html=html,
        base_dir=tmp_path,
        page_size="a4",
        orientation="portrait",
    )
    assert "margin: 0" in css
    assert ".sidebar { display: none" in css
    assert is_tool_editor is True


@pytest.mark.unit
def test_handle_action_writes_error_artifact_and_short_table_message(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "tooleditor_flow.html"
    source.write_text("<html><body>Hello</body></html>", encoding="utf-8")

    output_dir = tmp_path / "out"

    action_path = tmp_path / "action.json"
    action_path.write_text(
        json.dumps(
            {
                "action_id": "convert",
                "input": {"page_size": "a4", "orientation": "portrait"},
                "state": {"html_files": [str(source)]},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    long_a = "A" * 2_000

    def _fail_weasyprint(
        *,
        source: Path,
        pdf_path: Path,
        page_size: str,
        orientation: str,
    ) -> str | None:  # noqa: ARG001
        raise Exception(long_a)  # noqa: BLE001

    def _pypandoc_should_not_be_called(
        *,
        source: Path,
        pdf_path: Path,
        page_size: str,
        orientation: str,
    ) -> str | None:  # noqa: ARG001
        raise AssertionError("_try_pypandoc must not be called")

    monkeypatch.setattr(html_to_pdf_preview, "_try_weasyprint", _fail_weasyprint)
    monkeypatch.setattr(
        html_to_pdf_preview,
        "_try_pypandoc",
        _pypandoc_should_not_be_called,
    )

    payload = html_to_pdf_preview._handle_action(
        action_path=action_path,
        output_dir=output_dir,
    )

    table = _find_table_output(payload, title="Konverteringsresultat")
    rows = table.get("rows")
    assert isinstance(rows, list)
    assert len(rows) == 1

    message = rows[0].get("message")
    assert isinstance(message, str)
    assert len(message) <= 200

    error_artifact = output_dir / "conversion-errors.txt"
    assert error_artifact.is_file()
    artifact_text = error_artifact.read_text(encoding="utf-8")
    assert "WeasyPrint:" in artifact_text


@pytest.mark.unit
def test_handle_action_success_does_not_write_error_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "ok.html"
    source.write_text("<html><body>OK</body></html>", encoding="utf-8")

    output_dir = tmp_path / "out"

    action_path = tmp_path / "action.json"
    action_path.write_text(
        json.dumps(
            {
                "action_id": "convert",
                "input": {"page_size": "a4", "orientation": "portrait"},
                "state": {"html_files": [str(source)]},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def _ok_weasyprint(
        *,
        source: Path,
        pdf_path: Path,
        page_size: str,
        orientation: str,
    ) -> str | None:  # noqa: ARG001
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        return "weasyprint"

    monkeypatch.setattr(html_to_pdf_preview, "_try_weasyprint", _ok_weasyprint)

    payload = html_to_pdf_preview._handle_action(
        action_path=action_path,
        output_dir=output_dir,
    )

    table = _find_table_output(payload, title="Konverteringsresultat")
    rows = table.get("rows")
    assert isinstance(rows, list)
    assert len(rows) == 1

    assert not (output_dir / "conversion-errors.txt").exists()

    message = rows[0].get("message")
    assert message == ""
