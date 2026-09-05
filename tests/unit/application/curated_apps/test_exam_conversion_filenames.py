"""Filename contract tests for Exam Converter target artifacts."""

from __future__ import annotations

import pytest

from skriptoteket.application.curated_apps.exam_conversion import (
    build_examnet_pdf_filename,
    build_examnet_qti_filename,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("source_filename", "expected_stem"),
    [
        ("Nationellt prov svenska.DXE", "Nationellt prov svenska"),
        ("Årskurs 9 – läsförståelse.dxe", "Årskurs 9 – läsförståelse"),
        ("kemi.omprov.version.2.dxe", "kemi.omprov.version.2"),
    ],
)
def test_target_filenames_preserve_sanitized_source_stem(
    source_filename: str,
    expected_stem: str,
) -> None:
    assert build_examnet_pdf_filename(input_filename=source_filename) == (
        f"{expected_stem} - Exam.net.pdf"
    )
    assert build_examnet_qti_filename(input_filename=source_filename) == (
        f"{expected_stem} - QTI.zip"
    )


def test_target_filenames_truncate_only_source_stem_to_255_characters() -> None:
    source_filename = f"{'x' * 251}.DXE"

    pdf_filename = build_examnet_pdf_filename(input_filename=source_filename)
    qti_filename = build_examnet_qti_filename(input_filename=source_filename)

    assert pdf_filename == f"{'x' * (255 - len(' - Exam.net.pdf'))} - Exam.net.pdf"
    assert qti_filename == f"{'x' * (255 - len(' - QTI.zip'))} - QTI.zip"
    assert len(pdf_filename) == 255
    assert len(qti_filename) == 255
