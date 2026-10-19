"""Replay guards exempt only pending source-review items (TASK-SKRIPT-39-04-17 D9, review F1).

A ``review_complete`` item with origin ``source_fallback`` stays checked: if its
visible lines hold its printed label or a points line, both guards must fail.
Only a pending source-review item (``review_required`` + ``source_fallback``)
keeps the accepted D9 exemption. Follows the reviewer's ``guard_probe.py``
approach: build a schema-valid native document, inject it into each guard
module's build cache, then call the real guard test functions.
"""

from uuid import UUID

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_review import (
    review_source_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamHeader,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
    NativeParseOrigin,
)
from tests.unit.domain.curated_apps.exam_workspace.gap_paragraph_test_support import (
    chunk,
)


def is_pending_source_review(item: NativeExamItem) -> bool:
    """Whether the item keeps the D9 exemption: still pending source review."""
    return (
        item.review.state is NativeItemReviewState.REVIEW_REQUIRED
        and item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    )


def _leaking_document(
    state: NativeItemReviewState, origin: NativeParseOrigin
) -> tuple[NativeExamDocument, DocxChunk]:
    source = (chunk("body:0001", "1. Explain the process."), chunk("body:0002", "3 poäng"))
    raw = review_source_item(source, "source review")
    admitted = NativeExamItem.model_validate(
        {
            **raw.model_dump(),
            "printed_label": "1",
            "review": {"state": state.value, "parse_origin": origin.value, "reasons": []},
        }
    )
    honest = NativeExamItem.model_validate(
        {
            **review_source_item(
                (chunk("body:0003", "Explain another process."),), "probe"
            ).model_dump(),
            "item_id": "item_002",
            "sequence": 2,
            "printed_label": "2",
            "review": {
                "state": NativeItemReviewState.REVIEW_COMPLETE.value,
                "parse_origin": NativeParseOrigin.LLM_PARSED.value,
                "reasons": [],
            },
        }
    )
    document = NativeExamDocument(
        document_id=UUID("12345678-1234-4234-9234-123456789abc"),
        revision=1,
        title="Replay guard probe",
        header=NativeExamHeader(printed_total=3),
        items=(admitted, honest),
        origin=NativeExamDocumentOrigin(
            kind="docx_import",
            source_filename="guard_probe.docx",
            source_sha256="a" * 64,
        ),
    )
    total = chunk("body:0004", "Total: 3 poäng")
    return document, total


@pytest.fixture
def _restore_guard_caches():
    from tests.unit.domain.curated_apps.exam_workspace import (
        test_docx_section_instructions as points_module,
    )
    from tests.unit.domain.curated_apps.exam_workspace import (
        test_printed_parent_titles as labels_module,
    )

    labels_snapshot = dict(labels_module._BUILDS)
    points_snapshot = dict(points_module._BUILDS)
    yield
    labels_module._BUILDS.clear()
    labels_module._BUILDS.update(labels_snapshot)
    points_module._BUILDS.clear()
    points_module._BUILDS.update(points_snapshot)


def _inject(document: NativeExamDocument, total: DocxChunk) -> None:
    from tests.unit.domain.curated_apps.exam_workspace import (
        test_docx_section_instructions as points_module,
    )
    from tests.unit.domain.curated_apps.exam_workspace import (
        test_printed_parent_titles as labels_module,
    )

    labels_module._BUILDS["guard_probe"] = labels_module._Build(document)
    for exam in points_module._CLEAN:
        points_module._BUILDS[exam] = points_module._Build(document, {total.anchor: total})


async def test_completed_source_fallback_leak_fails_both_guards(_restore_guard_caches):
    """A REVIEW_COMPLETE + SOURCE_FALLBACK leak must trip both guards."""
    from tests.unit.domain.curated_apps.exam_workspace import (
        test_docx_section_instructions as points_module,
    )
    from tests.unit.domain.curated_apps.exam_workspace import (
        test_printed_parent_titles as labels_module,
    )

    document, total = _leaking_document(
        NativeItemReviewState.REVIEW_COMPLETE, NativeParseOrigin.SOURCE_FALLBACK
    )
    _inject(document, total)
    with pytest.raises(AssertionError):
        await labels_module.test_printed_labels_never_enter_student_visible_text("guard_probe")
    with pytest.raises(AssertionError):
        await points_module.test_points_lines_are_structure_and_never_reach_a_parent_or_an_item()


async def test_pending_source_review_item_keeps_the_d9_exemption(_restore_guard_caches):
    """A REVIEW_REQUIRED + SOURCE_FALLBACK item keeps the accepted exemption."""
    from tests.unit.domain.curated_apps.exam_workspace import (
        test_docx_section_instructions as points_module,
    )
    from tests.unit.domain.curated_apps.exam_workspace import (
        test_printed_parent_titles as labels_module,
    )

    document, total = _leaking_document(
        NativeItemReviewState.REVIEW_REQUIRED, NativeParseOrigin.SOURCE_FALLBACK
    )
    _inject(document, total)
    await labels_module.test_printed_labels_never_enter_student_visible_text("guard_probe")
    await points_module.test_points_lines_are_structure_and_never_reach_a_parent_or_an_item()


async def test_completed_llm_parsed_leak_fails_both_guards(_restore_guard_caches):
    """Control: the same leak as REVIEW_COMPLETE + LLM_PARSED trips both guards."""
    from tests.unit.domain.curated_apps.exam_workspace import (
        test_docx_section_instructions as points_module,
    )
    from tests.unit.domain.curated_apps.exam_workspace import (
        test_printed_parent_titles as labels_module,
    )

    document, total = _leaking_document(
        NativeItemReviewState.REVIEW_COMPLETE, NativeParseOrigin.LLM_PARSED
    )
    _inject(document, total)
    with pytest.raises(AssertionError):
        await labels_module.test_printed_labels_never_enter_student_visible_text("guard_probe")
    with pytest.raises(AssertionError):
        await points_module.test_points_lines_are_structure_and_never_reach_a_parent_or_an_item()
