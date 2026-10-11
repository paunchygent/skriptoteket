"""Native exam -> Exam.net PDF document plan tests (real fixture + render proof)."""

from html import escape
from pathlib import Path

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
    DigiExamExamNetPdfWarningCode,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeExamDocument,
    NativeExamItem,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeMatchRight,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
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


def _with_distractor(item: NativeExamItem) -> NativeExamItem:
    extra = NativeMatchRight(
        right_id=f"right_{len(item.match_right) + 1:03d}", text="Spare <entry>"
    )
    return NativeExamItem.model_validate({**dict(item), "match_right": (*item.match_right, extra)})


class TestMatchingItems:
    def test_recorded_matching_items_print_both_lists_in_order_and_pairs_only_in_the_key(
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
                assert escape(entry.text) in printed
            positions = [printed.index(escape(entry.text)) for entry in item.match_right]
            assert positions == sorted(positions)
            left_text = {entry.left_id: entry.text for entry in item.match_left}
            right_text = {entry.right_id: entry.text for entry in item.match_right}
            for pair in item.answer_key.match_pairs:
                assert (
                    f"{escape(left_text[pair.left_id])} – {escape(right_text[pair.right_id])}"
                    in key
                )
                assert " – " not in printed

    def test_an_unpaired_right_entry_is_printed_in_the_list_and_never_keyed(self) -> None:
        items = list(recorded_items())
        index = next(i for i, item in enumerate(items) if item.kind is NativeExamItemKind.MATCHING)
        items[index] = _with_distractor(items[index])

        document = native_exam_to_pdf_document(recorded_document(items=tuple(items)))

        assert document.status is DigiExamExamNetPdfStatus.SUCCESS
        printed, key = _sections(document.html)[index].split('<div class="answer-key">')
        assert "Spare &lt;entry&gt;" in printed
        assert "Spare" not in key

    def test_a_matching_item_without_a_key_blocks_the_document(self) -> None:
        items = list(recorded_items())
        index = next(i for i, item in enumerate(items) if item.kind is NativeExamItemKind.MATCHING)
        unkeyed = NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT)
        items[index] = items[index].model_copy(update={"answer_key": unkeyed})

        document = native_exam_to_pdf_document(recorded_document(items=tuple(items)))

        assert document.status is DigiExamExamNetPdfStatus.BLOCKED
        assert [w.code for w in document.warnings] == [
            DigiExamExamNetPdfWarningCode.MANUAL_ANSWER_KEY_REQUIRED
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
