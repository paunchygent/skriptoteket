"""Untitled exams save under the shared fallback file name."""

from skriptoteket.domain.curated_apps.exam_workspace.exam_document_file_name import (
    exam_document_file_name,
)


def test_empty_title_falls_back_to_the_untitled_exam_name() -> None:
    assert exam_document_file_name("") == "Namnlöst prov.provdokument.zip"


def test_whitespace_only_title_falls_back_to_the_untitled_exam_name() -> None:
    assert exam_document_file_name("   ") == "Namnlöst prov.provdokument.zip"


def test_real_title_keeps_its_stem() -> None:
    assert exam_document_file_name("Prov") == "Prov.provdokument.zip"
    assert exam_document_file_name("  Prov  ") == "Prov.provdokument.zip"
