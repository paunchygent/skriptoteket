"""Unit tests for the deterministic DOCX extraction rules."""

from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_workspace.docx_extraction import (
    DocxBlockKind,
    DocxSourceBlock,
    extract_native_exam_from_docx_blocks,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
)

_SHA = "a" * 64


def _blocks(*specs: tuple[DocxBlockKind, str]) -> tuple[DocxSourceBlock, ...]:
    return tuple(
        DocxSourceBlock(kind=kind, text=text, index=index)
        for index, (kind, text) in enumerate(specs)
    )


def _extract(blocks: tuple[DocxSourceBlock, ...]):
    return extract_native_exam_from_docx_blocks(
        blocks=blocks,
        document_id=uuid4(),
        source_filename="prov.docx",
        source_sha256=_SHA,
    )


class TestStructure:
    def test_title_instructions_and_sections_flow_into_items(self) -> None:
        result = _extract(
            _blocks(
                (DocxBlockKind.TITLE, "Omprov: grammatik"),
                (DocxBlockKind.BODY, "Total: 10 poäng"),
                (DocxBlockKind.SECTION, "Del 1: Fraser, 10 poäng"),
                (DocxBlockKind.HEADING, "Fråga 1. Ange frastyp."),
                (DocxBlockKind.BODY, "Skriv NF, PF eller VF."),
                (DocxBlockKind.BODY, "a) på bussen Frastyp: PF"),
                (DocxBlockKind.BODY, "Poäng: 10 poäng"),
            )
        )
        document = result.document
        assert document.title == "Omprov: grammatik"
        assert document.instructions == ("Total: 10 poäng",)
        item = document.items[0]
        assert item.kind is NativeExamItemKind.GAP_FILL
        assert item.points == 10
        assert item.body[0].segments[0].text == "Del 1: Fraser, 10 poäng"
        assert item.gaps[0].accepted_values == ("PF",)
        assert item.answer_key.origin is NativeAnswerKeyOrigin.SOURCE_PROVIDED
        assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE

    def test_content_after_points_flows_to_next_item(self) -> None:
        result = _extract(
            _blocks(
                (DocxBlockKind.HEADING, "Fråga 1. Läs texten."),
                (DocxBlockKind.BODY, "Poäng: 2 poäng"),
                (DocxBlockKind.HEADING, "Text A"),
                (DocxBlockKind.BODY, "En vattenläcka uppstod."),
                (DocxBlockKind.HEADING, "Fråga 2. Jämför texterna."),
                (DocxBlockKind.BODY, "Poäng: 4 poäng"),
            )
        )
        second = result.document.items[1]
        texts = [paragraph.segments[0].text for paragraph in second.body]
        assert texts[:2] == ["Text A", "En vattenläcka uppstod."]

    def test_points_fall_back_to_heading_parenthetical(self) -> None:
        result = _extract(
            _blocks(
                (DocxBlockKind.HEADING, "Fråga 1 – grundfakta (8p)"),
                (DocxBlockKind.BODY, "Vilken tidsperiod omfattar medeltiden?"),
            )
        )
        assert result.document.items[0].points == 8

    def test_no_question_structure_falls_back_to_reviewable_item(self) -> None:
        result = _extract(
            _blocks(
                (DocxBlockKind.BODY, "Lös uppgiften nedan."),
                (DocxBlockKind.BODY, "Beskriv fotosyntesen."),
            )
        )
        item = result.document.items[0]
        assert item.kind is NativeExamItemKind.FREE_TEXT
        assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
        assert "no_question_structure_detected" in item.review.reasons


class TestAnswerLabelRules:
    def test_multiple_labels_keep_answers_out_of_stem_and_flag_review(self) -> None:
        result = _extract(
            _blocks(
                (DocxBlockKind.HEADING, "Fråga 1. Ange bisatsens typ."),
                (
                    DocxBlockKind.BODY,
                    "a) Jag vet att det regnar. Bisats: att det regnar Typ: att-sats",
                ),
                (DocxBlockKind.BODY, "Poäng: 1 poäng"),
            )
        )
        item = result.document.items[0]
        assert item.kind is NativeExamItemKind.GAP_FILL
        visible = item.body[0].segments[0].text
        assert visible.endswith("Bisats: ")
        assert "Typ: att-sats" not in visible
        assert item.gaps[0].accepted_values == ("att det regnar Typ: att-sats",)
        assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
        assert "multiple_answer_labels_detected" in item.review.reasons

    def test_long_answers_lower_confidence(self) -> None:
        long_answer = "Eleverna (S) lämnade (P) inte (SA) sina mobiler (DO) i skåpet (Adv)."
        result = _extract(
            _blocks(
                (DocxBlockKind.HEADING, "Fråga 1. Gör satsdelsanalys."),
                (DocxBlockKind.BODY, f"a) Eleverna lämnade mobiler. Analys: {long_answer}"),
                (DocxBlockKind.BODY, "Poäng: 2 poäng"),
            )
        )
        item = result.document.items[0]
        assert "long_answer_key" in item.review.reasons
        assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED

    def test_mixed_keyed_and_unkeyed_sublines_fall_back_to_free_text(self) -> None:
        result = _extract(
            _blocks(
                (DocxBlockKind.HEADING, "Fråga 1. Blandad fråga."),
                (DocxBlockKind.BODY, "a) på bussen Frastyp: PF"),
                (DocxBlockKind.BODY, "b) skriv en egen mening"),
                (DocxBlockKind.BODY, "Poäng: 2 poäng"),
            )
        )
        item = result.document.items[0]
        assert item.kind is NativeExamItemKind.FREE_TEXT
        assert item.gaps == ()
        texts = [paragraph.segments[0].text for paragraph in item.body]
        assert "a) på bussen Frastyp: PF" in texts
        assert "partial_answer_keys_detected" in item.review.reasons
        assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED

    def test_sublines_without_any_labels_stay_visible_free_text(self) -> None:
        result = _extract(
            _blocks(
                (DocxBlockKind.HEADING, "Fråga 1. Diskutera."),
                (DocxBlockKind.BODY, "a) första perspektivet"),
                (DocxBlockKind.BODY, "b) andra perspektivet"),
                (DocxBlockKind.BODY, "Poäng: 4 poäng"),
            )
        )
        item = result.document.items[0]
        assert item.kind is NativeExamItemKind.FREE_TEXT
        assert "sublines_without_answer_keys" in item.review.reasons

    def test_missing_points_requires_review(self) -> None:
        result = _extract(
            _blocks(
                (DocxBlockKind.HEADING, "Fråga 1. Ange frastyp."),
                (DocxBlockKind.BODY, "a) på bussen Frastyp: PF"),
            )
        )
        item = result.document.items[0]
        assert item.points is None
        assert "missing_points" in item.review.reasons
        assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
