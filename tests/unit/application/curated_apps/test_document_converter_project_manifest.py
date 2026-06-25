"""Document Converter HTML/CSS project manifest tests.

Purpose:
    Prove the route-inactive Document Converter project contract validates
    multi-file HTML/CSS preview inputs before rendering or storage begins.

Relationships:
    Exercises the application contract models consumed by the project preview
    API and rendering handler.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from skriptoteket.application.curated_apps.document_converter_projects import (
    DOCUMENT_CONVERTER_PROJECT_MAX_CSS_FILES,
    DOCUMENT_CONVERTER_PROJECT_MAX_FONT_FILES,
    DOCUMENT_CONVERTER_PROJECT_MAX_HTML_ENTRIES,
    DOCUMENT_CONVERTER_PROJECT_MAX_IMAGE_FILES,
    DocumentConverterProjectManifest,
    DocumentConverterProjectOutputMode,
    DocumentConverterProjectTemplateId,
)
from skriptoteket.domain.errors import DomainError, ErrorCode


def _manifest_payload() -> dict[str, object]:
    return {
        "html_entries": [
            {
                "entry_id": "worksheet",
                "filename": "worksheet.html",
                "title": "Worksheet",
            }
        ],
        "css_files": ["style.css"],
        "image_files": ["logo.png"],
        "font_files": [],
        "output_mode": "both",
        "pdf_controls": {
            "paper_size": "a4",
            "orientation": "portrait",
            "margins": {
                "top_mm": 14,
                "right_mm": 12,
                "bottom_mm": 14,
                "left_mm": 12,
            },
            "template_id": "academic_phd",
        },
    }


def test_project_manifest_closes_first_html_css_preview_shape() -> None:
    manifest = DocumentConverterProjectManifest.model_validate(_manifest_payload())

    assert manifest.output_mode is DocumentConverterProjectOutputMode.BOTH
    assert manifest.pdf_controls.template_id is DocumentConverterProjectTemplateId.ACADEMIC_PHD
    assert manifest.html_entries[0].filename == "worksheet.html"
    assert manifest.css_files == ["style.css"]
    assert manifest.image_files == ["logo.png"]
    assert manifest.font_files == []


@pytest.mark.parametrize("paper_size", ["a3", "a4", "a5"])
def test_project_manifest_accepts_real_pdf_paper_sizes(paper_size: str) -> None:
    payload = _manifest_payload()
    pdf_controls = payload["pdf_controls"]
    assert isinstance(pdf_controls, dict)
    pdf_controls["paper_size"] = paper_size

    manifest = DocumentConverterProjectManifest.model_validate(payload)

    assert manifest.pdf_controls.paper_size.value == paper_size


@pytest.mark.parametrize(
    ("field", "values", "max_count"),
    [
        (
            "html_entries",
            [
                {
                    "entry_id": f"entry-{index}",
                    "filename": f"entry-{index}.html",
                }
                for index in range(DOCUMENT_CONVERTER_PROJECT_MAX_HTML_ENTRIES + 1)
            ],
            DOCUMENT_CONVERTER_PROJECT_MAX_HTML_ENTRIES,
        ),
        (
            "css_files",
            [f"style-{index}.css" for index in range(DOCUMENT_CONVERTER_PROJECT_MAX_CSS_FILES + 1)],
            DOCUMENT_CONVERTER_PROJECT_MAX_CSS_FILES,
        ),
        (
            "image_files",
            [
                f"image-{index}.png"
                for index in range(DOCUMENT_CONVERTER_PROJECT_MAX_IMAGE_FILES + 1)
            ],
            DOCUMENT_CONVERTER_PROJECT_MAX_IMAGE_FILES,
        ),
    ],
)
def test_project_manifest_enforces_first_count_caps(
    field: str,
    values: list[object],
    max_count: int,
) -> None:
    payload = _manifest_payload()
    payload[field] = values

    with pytest.raises(ValidationError) as excinfo:
        DocumentConverterProjectManifest.model_validate(payload)

    assert str(max_count) in str(excinfo.value)


@pytest.mark.parametrize(
    ("field", "bad_filename"),
    [
        ("html_entries", "../worksheet.html"),
        ("css_files", "/etc/passwd.css"),
        ("image_files", "nested/logo.png"),
        ("image_files", "logo.svg"),
    ],
)
def test_project_manifest_rejects_paths_and_unsupported_assets(
    field: str,
    bad_filename: str,
) -> None:
    payload = _manifest_payload()
    if field == "html_entries":
        payload[field] = [{"entry_id": "worksheet", "filename": bad_filename}]
    else:
        payload[field] = [bad_filename]

    with pytest.raises(ValidationError):
        DocumentConverterProjectManifest.model_validate(payload)


def test_project_manifest_rejects_uploaded_fonts_in_first_contract() -> None:
    payload = _manifest_payload()
    payload["font_files"] = ["custom.woff2"]

    with pytest.raises(ValidationError) as excinfo:
        DocumentConverterProjectManifest.model_validate(payload)

    assert str(DOCUMENT_CONVERTER_PROJECT_MAX_FONT_FILES) in str(excinfo.value)


def test_project_manifest_upload_boundary_requires_declared_files_only() -> None:
    manifest = DocumentConverterProjectManifest.model_validate(_manifest_payload())

    with pytest.raises(DomainError) as excinfo:
        manifest.validate_uploaded_file_set(
            uploaded_filenames={"worksheet.html", "style.css", "evil.png"}
        )

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
    assert excinfo.value.details["unexpected_filenames"] == ["evil.png"]
    assert excinfo.value.details["missing_filenames"] == ["logo.png"]
