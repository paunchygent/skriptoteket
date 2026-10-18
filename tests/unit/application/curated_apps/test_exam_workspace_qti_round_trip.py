"""End-to-end QTI round trip through the real package bytes (TASK-SKRIPT-41-02-01 Q2).

Every document is exported through ``build_native_examnet_qti_package`` — the same
function the workspace export route calls — and imported again through
``ParseExamWorkspaceQtiPackageHandler`` with the real ``ExamNetQtiPackageReader``.
The projections compare positions and payload hashes, never regenerated identifiers.
The parent ruling of 2026-10-18 names the accepted losses; each one is asserted in
its own test, and any other difference fails the round trip.
"""

import hashlib
from pathlib import Path
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
    export_file_base_name,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_qti_import import (
    ParseExamWorkspaceQtiPackageHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_package_reader import (  # noqa: E501
    ExamNetQtiPackageReader,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    SequenceIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _settings,
)
from tests.unit.application.curated_apps.qti_round_trip_support import (
    _body_projection,
    _document_projection,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_gap_fill_item,
    make_single_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    parent_over,
    recorded_document,
    recorded_items,
)

# Lead ruling 2026-10-18: only exports that exist are round-trip inputs. The
# kursavslutande exam's recording leaves the points of its fifteen single-choice
# questions empty, so the real export route refuses it (missing_points) and it is
# not a round-trip input.
_ROUND_TRIP_EXAMS = (
    "svenska_2_grammatik_omprov_variant_1_med_facit",
    "svenska_2_grammatik_omprov_variant_2_med_facit",
)

_REFERENCE_PACKAGE = Path("tests/fixtures/exam_conversion/reference-qti-package.zip")


def _parse_handler() -> ParseExamWorkspaceQtiPackageHandler:
    return ParseExamWorkspaceQtiPackageHandler(
        reader=ExamNetQtiPackageReader(),
        settings=_settings(),
        id_generator=SequenceIdGenerator([uuid4() for _ in range(5)]),
    )


def _document(
    items: tuple[NativeExamItem, ...],
    *,
    instructions: tuple[NativeParagraph, ...] = (),
    parents: tuple[NativeExamParent, ...] = (),
) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov på svenska",
        instructions=instructions,
        items=items,
        parents=parents,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _round_trip(
    document: NativeExamDocument, *, filename: str = "paket.zip"
) -> tuple[bytes, ExamWorkspaceContainerContent]:
    """Export through the workspace's own package builder, import through the handler."""

    package, _report = build_native_examnet_qti_package(
        document,
        package_name=export_file_base_name(document),
        qti_writer=ExamNetQtiPackageWriter(),
    )
    container = _parse_handler().handle(filename=filename, content=package, course_key=None)
    return package, container


@pytest.mark.parametrize("exam", _ROUND_TRIP_EXAMS)
def test_omprov_exam_round_trips_through_the_real_package_bytes(exam: str) -> None:
    items = recorded_items(exam)
    document = recorded_document(items=items)

    package, container = _round_trip(document, filename=f"{exam}.zip")

    assert container.notes == ()
    assert container.document.origin.kind == "qti_import"
    assert container.document.origin.source_filename == f"{exam}.zip"
    assert container.document.origin.source_sha256 == hashlib.sha256(package).hexdigest()
    assert _document_projection(container.document) == _document_projection(document)
    # The named free-text loss: criterion text never reaches the package, points stay.
    for original, imported in zip(items, container.document.items, strict=True):
        if original.criteria:
            assert imported.criteria == ()
            assert imported.points == original.points


@pytest.mark.parametrize("exam", _ROUND_TRIP_EXAMS)
def test_parent_over_four_recorded_items_round_trips_its_grouping(exam: str) -> None:
    items = recorded_items(exam)
    numbers = tuple(item.sequence for item in items[:4])
    document = recorded_document(
        items=items,
        parents=(parent_over("parent_001", "Answer every question.", *numbers),),
    )

    _package, container = _round_trip(document)

    assert container.notes == ()
    assert _document_projection(container.document) == _document_projection(document)


def test_free_text_criteria_text_is_not_carried_by_qti() -> None:
    item = make_free_text_item().model_copy(
        update={
            "points": 3,
            "criteria": (
                NativeExamCriterion(text="Ett korrekt exempel.", points=2),
                NativeExamCriterion(text="En korrekt förklaring.", points=1),
            ),
        }
    )
    document = _document((item,))

    _package, container = _round_trip(document)

    imported = container.document.items[0]
    assert imported.criteria == ()
    assert imported.points == 3
    assert _document_projection(container.document) == _document_projection(document)


def test_document_instructions_are_folded_into_each_item_prompt() -> None:
    instructions = (
        NativeParagraph(
            heading_level=None,
            segments=(NativeTextSegment(text="Läs instruktionerna noggrant.", marks=()),),
        ),
    )
    document = _document(
        (make_single_choice_item(), make_single_choice_item(sequence=2, item_id="item_002")),
        instructions=instructions,
    )

    _package, container = _round_trip(document)

    imported = container.document
    assert imported.instructions == ()
    instruction_projection = _body_projection(instructions, {})
    for original, imported_item in zip(document.items, imported.items, strict=True):
        assert imported_item.points == original.points
        assert (
            _body_projection(imported_item.body, {})[: len(instruction_projection)]
            == instruction_projection
        )


def test_automatic_gap_values_return_as_accepted_values() -> None:
    document = _document(
        (make_gap_fill_item(accepted=("nationalekonomi",), automatic=("nationalekonomie",)),)
    )

    _package, container = _round_trip(document)

    imported = container.document.items[0]
    assert imported.gaps[0].accepted_values == ("nationalekonomi", "nationalekonomie")
    assert imported.gaps[0].automatic_values == ()


def test_single_non_gap_child_parent_is_flattened() -> None:
    document = _document(
        (make_single_choice_item(),),
        parents=(parent_over("parent_001", "Läs texten först.", 1),),
    )

    _package, container = _round_trip(document)

    imported = container.document
    assert imported.parents == ()
    assert imported.items[0].kind.value == "single_choice"
    assert imported.items[0].points == 1
    assert _body_projection(imported.items[0].body, {}) == (
        (None, (("text", ("Läs texten först.", ())),)),
        (None, (("text", ("Vilket är huvudordet?", ())),)),
    )


def test_plain_space_between_marked_runs_is_lost_to_writer_indentation() -> None:
    body = (
        NativeParagraph(
            heading_level=None,
            segments=(
                NativeTextSegment(text="Fet", marks=("bold",)),
                NativeTextSegment(text=" ", marks=()),
                NativeTextSegment(text="kursiv", marks=("italic",)),
            ),
        ),
    )
    document = _document((make_single_choice_item().model_copy(update={"body": body}),))

    _package, container = _round_trip(document)

    imported = container.document.items[0]
    assert _body_projection(imported.body, {}) == (
        (None, (("text", ("Fet", ("bold",))), ("text", ("kursiv", ("italic",))))),
    )


def test_reference_package_imports_with_seven_scored_items_and_no_notes() -> None:
    package = _REFERENCE_PACKAGE.read_bytes()

    container = _parse_handler().handle(
        filename="reference-qti-package.zip", content=package, course_key=None
    )

    assert [item.points for item in container.document.items] == [5, 2, 2, 2, 4, 6, 3]
    assert container.notes == ()
