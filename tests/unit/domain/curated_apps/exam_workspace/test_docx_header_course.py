"""Chosen course snapshots outrank source hints without losing raw metadata."""

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_header import apply_header
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import ExamManifest, HeaderAnchor
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    ExamCourseChoice,
    NativeExamDocument,
    NativeExamHeader,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_support import (
    choice,
    conversion_update,
)


def _document() -> NativeExamDocument:
    return conversion_update([("q1", [choice("p1", "Frågan")])], pending=()).document


# Real identities from the committed Skolverket recording. The source lines are
# adversarial teacher-document examples, not observed AI extraction outputs.
@pytest.mark.parametrize(
    ("hint", "picked", "expected_key", "expected_name"),
    [
        ("Svenska 2", "ENGENG05", "ENGENG05", "Engelska 5"),
        ("Svenska 2 kursavslutande", None, "SVESVE02", "Svenska 2"),
        ("svesve02", None, "SVESVE02", "Svenska 2"),
        ("Matematik, åk 7-9", None, "GRGRMAT01/7-9", "Matematik, åk 7–9"),
        ("Svenska 2 och Engelska 5", None, None, None),
        ("GRGRMAT01", None, None, None),
        ("Lokalt temaprov höstterminen", None, None, None),
        (None, "ENGENG05", "ENGENG05", "Engelska 5"),
        (None, None, None, None),
    ],
)
def test_header_course_selection_keeps_the_hint_and_only_accepts_one_identity(
    hint: str | None, picked: str | None, expected_key: str | None, expected_name: str | None
) -> None:
    manifest = ExamManifest(
        questions=(),
        contexts=(),
        title_anchors=(),
        header=(HeaderAnchor("c1", "course", ()),) if hint else (),
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=(),
    )
    chunks = (
        (DocxChunk(anchor="c1", kind="paragraph", text=hint, marked_text=hint),) if hint else ()
    )
    result = apply_header(
        _document(), manifest, chunks, course_key=picked, courses=load_exam_course_catalog().courses
    )
    assert result.document.header.course_hint == hint
    assert result.document.header.course == (
        ExamCourseChoice(key=expected_key, name=expected_name) if expected_key else None
    )


def test_missing_picked_key_is_not_silently_replaced_by_a_hint() -> None:
    manifest = ExamManifest(
        questions=(),
        contexts=(),
        title_anchors=(),
        header=(HeaderAnchor("c1", "course", ()),),
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=(),
    )
    with pytest.raises(ValueError):
        apply_header(
            _document(),
            manifest,
            (DocxChunk(anchor="c1", kind="paragraph", text="Svenska 2", marked_text="Svenska 2"),),
            course_key="missing-official-course",
            courses=load_exam_course_catalog().courses,
        )


def test_document_roundtrip_preserves_the_chosen_name_snapshot_and_rejects_v3() -> None:
    # A catalog refresh cannot rename a previously saved exam's choice.
    header = NativeExamHeader(
        course_hint="SVESVE02",
        printed_total=36,
        course=ExamCourseChoice(key="SVESVE02", name="Svenska 2 vid valtillfället"),
    )
    document = _document().model_copy(update={"header": header})
    payload = document.model_dump(mode="json")
    assert payload["schema_version"] == "native_exam_document_v10"
    assert NativeExamDocument.model_validate(payload).header == header
    assert header.course is not None
    with pytest.raises(ValidationError):
        setattr(header.course, "name", "Utbytt namn")
    payload["schema_version"] = "native_exam_document_v3"
    with pytest.raises(ValidationError):
        NativeExamDocument.model_validate(payload)
