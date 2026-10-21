"""Unit tests for the exam file name following the exam title (D13)."""

from skriptoteket.application.curated_apps.exam_workspace_exports import export_file_base_name
from skriptoteket.application.curated_apps.exam_workspace_file_name import (
    UNTITLED_EXAM_NAME,
    exam_document_file_name,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_blank import (
    blank_native_exam_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)


def _titled(title: str) -> NativeExamDocument:
    return blank_native_exam_document().model_copy(update={"title": title})


def test_empty_title_falls_back_to_the_untitled_exam_name() -> None:
    assert exam_document_file_name(_titled("")) == "Namnlöst prov.provdokument.zip"
    assert exam_document_file_name(_titled("   ")) == "Namnlöst prov.provdokument.zip"
    assert UNTITLED_EXAM_NAME == "Namnlöst prov"


def test_punctuation_only_title_falls_back_to_the_untitled_exam_name() -> None:
    assert exam_document_file_name(_titled("... !!!")) == "Namnlöst prov.provdokument.zip"
    assert exam_document_file_name(_titled(": -,")) == "Namnlöst prov.provdokument.zip"


def test_real_title_uses_the_export_rule_stem() -> None:
    document = _titled("Prov: Vecka 5!")
    assert exam_document_file_name(document) == "Prov Vecka 5.provdokument.zip"


def test_long_title_is_capped_like_the_export_base_name() -> None:
    document = _titled("Prov med en mycket längre rubrik " * 9)
    name = exam_document_file_name(document)
    assert name == f"{export_file_base_name(document)}.provdokument.zip"
    assert len(name) <= 255
