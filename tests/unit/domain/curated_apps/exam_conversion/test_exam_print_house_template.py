"""The one house template's page and block geometry (TASK-SKRIPT-40-04-07 W1, W3)."""

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    HEADING_GEOMETRY,
    PAGE_HEIGHT_MM,
    PAGE_MARGIN_SIDE_MM,
    PAGE_WIDTH_MM,
    TEXT_WIDTH_MM,
    ExamPrintVariant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    PrintHeading,
    build_print_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_change_type_test_support import (
    KINDS,
    source_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_ordering_item,
)


def _document_with_every_item_kind() -> NativeExamDocument:
    """One item of every native kind, each with a unique id, as the print document sees them."""
    items = [
        source_item(kind).model_copy(update={"item_id": f"item_{index:03d}", "sequence": index})
        for index, kind in enumerate(KINDS, start=1)
    ]
    ordering_index = len(KINDS) + 1
    items.append(make_ordering_item(sequence=ordering_index, item_id=f"item_{ordering_index:03d}"))
    return make_document(*items)


def _emitted_heading_levels() -> set[int]:
    document = build_print_document(
        _document_with_every_item_kind(), variant=ExamPrintVariant.STUDENT
    )
    return {
        block.level
        for entry in document.entries
        for block in entry.blocks
        if isinstance(block, PrintHeading)
    }


def test_the_page_is_a4() -> None:
    assert PAGE_WIDTH_MM == 210.0
    assert PAGE_HEIGHT_MM == 297.0


def test_text_width_is_the_page_width_without_the_side_margins() -> None:
    assert TEXT_WIDTH_MM == PAGE_WIDTH_MM - 2 * PAGE_MARGIN_SIDE_MM


def test_every_heading_level_the_print_document_emits_has_geometry() -> None:
    levels = _emitted_heading_levels()

    assert levels
    assert levels <= set(HEADING_GEOMETRY)
