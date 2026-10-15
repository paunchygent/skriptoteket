"""Native exam -> Exam.net PDF document plan tests (real fixture + render proof)."""

from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
    DigiExamExamNetPdfWarningCode,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchPair,
    NativeMatchRight,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import plain_body
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    parent_over,
    recorded_document,
    recorded_items,
)

_FIXTURE = Path("tests/fixtures/exam_conversion/native_workspace_grammatik.json")


def _reviewed(document: NativeExamDocument) -> NativeExamDocument:
    """Flip every item to an export-ready review/trust state via model_copy."""
    items = []
    for item in document.items:
        answer_key = item.answer_key
        if answer_key.origin is NativeAnswerKeyOrigin.MACHINE_PROPOSED:
            answer_key = answer_key.model_copy(
                update={"origin": NativeAnswerKeyOrigin.REVIEWED_ADVISORY}
            )
        items.append(
            item.model_copy(
                update={
                    "review": item.review.model_copy(
                        update={"state": NativeItemReviewState.REVIEW_COMPLETE}
                    ),
                    "answer_key": answer_key,
                    "points": item.points if item.points is not None else 1,
                }
            )
        )
    return document.model_copy(update={"items": tuple(items)})


@pytest.fixture(scope="module")
def reviewed_document() -> NativeExamDocument:
    return _reviewed(NativeExamDocument.model_validate_json(_FIXTURE.read_bytes()))


class TestPdfDocumentPlan:
    def test_reviewed_fixture_builds_a_success_document(
        self, reviewed_document: NativeExamDocument
    ) -> None:
        document = native_exam_to_pdf_document(reviewed_document)

        assert document.status is DigiExamExamNetPdfStatus.SUCCESS
        assert "Omprov: grammatik och språkstrukturer" in document.html
        assert "Fråga 1" in document.html
        assert "Frastyp:" in document.html
        assert '<span class="gap-placeholder">[____]</span>' in document.html
        assert document.asset_files == ()

    def test_missing_points_blocks_the_document(
        self, reviewed_document: NativeExamDocument
    ) -> None:
        first_item = reviewed_document.items[0].model_copy(update={"points": None})
        broken = reviewed_document.model_copy(
            update={"items": (first_item, *reviewed_document.items[1:])}
        )

        document = native_exam_to_pdf_document(broken)

        assert document.status is DigiExamExamNetPdfStatus.BLOCKED
        assert document.html == ""
        assert any(
            warning.code is DigiExamExamNetPdfWarningCode.MISSING_POINT_VALUE
            for warning in document.warnings
        )


class TestPdfRendering:
    def test_weasyprint_renders_non_empty_pdf_bytes(
        self, reviewed_document: NativeExamDocument
    ) -> None:
        document = native_exam_to_pdf_document(reviewed_document)

        pdf_bytes = WeasyPrintExamNetPdfRenderer().render_pdf(document=document)

        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 1000


def _sections(html: str) -> list[str]:
    return html.split('<section class="exam-item">')[1:]


def _grid(html: str) -> ET.Element:
    table = "<table" + html.split("<table", 1)[1].split("</table>", 1)[0] + "</table>"
    return ET.fromstring(table)


def _with_distractor(item: NativeExamItem) -> NativeExamItem:
    extra = NativeMatchRight(
        right_id=f"right_{len(item.match_right) + 1:03d}", body=plain_body("Spare <entry>")
    )
    return NativeExamItem.model_validate({**dict(item), "match_right": (*item.match_right, extra)})


class TestMatchingItems:
    def test_recorded_matching_items_print_blank_grid_and_marked_answer_grid(
        self,
    ) -> None:
        items = recorded_items()
        document = native_exam_to_pdf_document(recorded_document(items=items))

        assert document.status is DigiExamExamNetPdfStatus.SUCCESS
        sections = _sections(document.html)
        matching = [item for item in items if item.kind is NativeExamItemKind.MATCHING]
        assert matching
        for item in matching:
            section = sections[item.sequence - 1]
            printed, key = section.split('<div class="answer-key">')
            for entry in item.match_left:
                assert escape(body_plain_text(entry.body)) in printed
            positions = [
                printed.index(escape(body_plain_text(entry.body))) for entry in item.match_right
            ]
            assert positions == sorted(positions)
            student_grid = _grid(printed)
            key_grid = _grid(key)
            correct = {(pair.left_id, pair.right_id) for pair in item.answer_key.match_pairs}
            assert [node.text for node in student_grid.findall("./thead/tr/th")] == [
                body_plain_text(entry.body) for entry in item.match_right
            ]
            for row_index, left in enumerate(item.match_left):
                student_cells = student_grid.findall("./tbody/tr")[row_index].findall("td/span")
                key_cells = key_grid.findall("./tbody/tr")[row_index].findall("td/span")
                assert len(student_cells) == len(item.match_right)
                assert all(cell.text is None for cell in student_cells)
                assert [cell.text for cell in key_cells] == [
                    "X" if (left.left_id, right.right_id) in correct else None
                    for right in item.match_right
                ]

    def test_an_unpaired_right_entry_is_printed_in_the_list_and_never_keyed(self) -> None:
        items = list(recorded_items())
        index = next(i for i, item in enumerate(items) if item.kind is NativeExamItemKind.MATCHING)
        items[index] = _with_distractor(items[index])

        document = native_exam_to_pdf_document(recorded_document(items=tuple(items)))

        assert document.status is DigiExamExamNetPdfStatus.SUCCESS
        printed, key = _sections(document.html)[index].split('<div class="answer-key">')
        assert "Spare &lt;entry&gt;" in printed
        grid = _grid(key)
        assert grid.findall("./thead/tr/th")[-1].text == "Spare <entry>"
        assert all(row.findall("td/span")[-1].text is None for row in grid.findall("./tbody/tr"))

    def test_a_many_to_many_key_marks_every_tick_and_leaves_unused_category_blank(self) -> None:
        items = list(recorded_items())
        index = next(i for i, item in enumerate(items) if item.kind is NativeExamItemKind.MATCHING)
        item = _with_distractor(items[index])
        existing = {(pair.left_id, pair.right_id) for pair in item.answer_key.match_pairs}
        extra = next(
            NativeMatchPair(left_id=item.match_left[0].left_id, right_id=right.right_id)
            for right in item.match_right[:-1]
            if (item.match_left[0].left_id, right.right_id) not in existing
        )
        pairs = (*item.answer_key.match_pairs, extra)
        items[index] = NativeExamItem.model_validate(
            {
                **dict(item),
                "tick_points": 0.5,
                "points": 0.5 * len(pairs),
                "answer_key": item.answer_key.model_copy(update={"match_pairs": pairs}),
            }
        )
        document = native_exam_to_pdf_document(recorded_document(items=tuple(items)))

        assert document.status is DigiExamExamNetPdfStatus.SUCCESS
        student, key = _sections(document.html)[index].split('<div class="answer-key">')
        assert all(cell.text is None for cell in _grid(student).findall("./tbody/tr/td/span"))
        rows = _grid(key).findall("./tbody/tr")
        assert [cell.text for cell in rows[0].findall("td/span")].count("X") == 2
        assert sum(cell.text == "X" for cell in _grid(key).findall("./tbody/tr/td/span")) == len(
            pairs
        )
        assert all(row.findall("td/span")[-1].text is None for row in rows)
        assert WeasyPrintExamNetPdfRenderer().render_pdf(document=document).startswith(b"%PDF")

    def test_a_matching_item_without_a_key_blocks_the_document(self) -> None:
        items = list(recorded_items())
        index = next(i for i, item in enumerate(items) if item.kind is NativeExamItemKind.MATCHING)
        unkeyed = NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT)
        items[index] = items[index].model_copy(update={"answer_key": unkeyed, "points": None})

        document = native_exam_to_pdf_document(recorded_document(items=tuple(items)))

        assert document.status is DigiExamExamNetPdfStatus.BLOCKED
        assert [w.code for w in document.warnings] == [
            DigiExamExamNetPdfWarningCode.MISSING_POINT_VALUE
        ]

    def test_weasyprint_renders_a_document_with_matching_items(self) -> None:
        document = native_exam_to_pdf_document(recorded_document())

        assert WeasyPrintExamNetPdfRenderer().render_pdf(document=document).startswith(b"%PDF")


class TestParentInstruction:
    def test_the_parent_instruction_prints_once_with_its_first_child(self) -> None:
        run = range(1, 5)
        items = recorded_items()
        assert len({items[n - 1].kind for n in run}) == 1
        parent = parent_over("parent_001", "Shared <instruction> line.", *run)

        document = native_exam_to_pdf_document(recorded_document((parent,), items=items))

        assert document.html.count("Shared &lt;instruction&gt; line.") == 1
        sections = _sections(document.html)
        assert "Shared &lt;instruction&gt; line." in sections[0]
        assert not any("Shared" in section for section in sections[1:])
