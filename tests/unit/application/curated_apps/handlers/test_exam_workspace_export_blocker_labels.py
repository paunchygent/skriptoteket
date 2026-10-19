"""Export blockers name questions by the workspace list label (user rule 2026-10-19)."""

from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_export_renderer import (
    ExamWorkspaceExportRenderer,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_writer import (  # noqa: E501
    ExamWorkspaceDocxWriter,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_exports_handler import (
    _FakeExamNetPdfRenderer,
    _FakePrintRenderer,
)
from tests.unit.domain.curated_apps.exam_workspace.inline_choice_test_support import (
    inline_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
)


def _parent_instruction() -> tuple[NativeParagraph, ...]:
    return (
        NativeParagraph(
            heading_level=None,
            segments=(NativeTextSegment(text="Do these.", marks=()),),
        ),
    )


def _document_with_part_before_blocker() -> NativeExamDocument:
    blocker_payload = inline_choice_item(sequence=4, points=2).model_dump(mode="json")
    blocker_payload["gaps"][0]["options"][0]["body"][0]["heading_level"] = 2
    blocker = NativeExamItem.model_validate(blocker_payload)
    items = (
        make_free_text_item(sequence=1, item_id="item_001"),
        make_free_text_item(sequence=2, item_id="item_002"),
        make_free_text_item(sequence=3, item_id="item_003"),
        blocker,
    )
    parents = (
        NativeExamParent(
            parent_id="parent_001",
            place=0,
            instruction=_parent_instruction(),
            item_ids=("item_001", "item_002", "item_003"),
        ),
    )
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov",
        items=items,
        parents=parents,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _renderer() -> ExamWorkspaceExportRenderer:
    return ExamWorkspaceExportRenderer(
        qti_writer=ExamNetQtiPackageWriter(),
        pdf_renderer=_FakeExamNetPdfRenderer(),
        docx_writer=ExamWorkspaceDocxWriter(),
        print_renderer=_FakePrintRenderer(),
    )


def test_blocker_after_part_names_the_list_label_not_the_sequence():
    document = _document_with_part_before_blocker()

    with pytest.raises(DomainError) as exc_info:
        _renderer()._raise_for_blockers(document)

    assert "Fråga 2: Rubrikformat är inte tillåtet i rullistealternativ." in exc_info.value.message
    assert "Fråga 4" not in exc_info.value.message
