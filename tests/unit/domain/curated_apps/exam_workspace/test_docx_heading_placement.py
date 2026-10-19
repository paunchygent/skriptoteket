"""Printed question headings open the body of the question they own.

A heading over one question opens its body verbatim; a heading over two or
more consecutive questions is the first line of their parent's instruction,
also when no instruction line follows it. A question-number heading keeps its
points label until the final gate settles it.
"""

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_instructions import Placed
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_review import review_source_item
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.points_wording import (
    with_settled_points_wording,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines
from tests.unit.domain.curated_apps.exam_workspace.docx_heading_placement_test_support import (
    _aligned,
    _chunk,
    _item,
    _ordered,
    _place,
)


def test_heading_over_one_question_opens_its_body_verbatim() -> None:
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", "paragraph", "Första frågan?"),
        _chunk("body:0003", "heading", "Facts"),
        _chunk("body:0004", "paragraph", "Andra frågan?"),
        _chunk("body:0005", "heading", "DNA base pairing"),
        _chunk("body:0006", "paragraph", "Tredje frågan?"),
    )
    placed = _place(
        chunks,
        _ordered(chunks, "body:0002", "body:0004", "body:0006"),
        title_anchors=frozenset({"body:0001"}),
    )

    assert placed.items[0].plain_text_lines()[0] == "Frågetext body:0002"
    assert placed.items[1].plain_text_lines()[0] == "Facts"
    assert placed.items[2].plain_text_lines()[0] == "DNA base pairing"
    assert placed.parents == ()


def test_heading_owned_by_one_question_opens_its_body() -> None:
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", "heading", "Classification"),
        _chunk("body:0003", "paragraph", "Frågan?"),
    )
    ordered: list[Placed] = [
        (1, ("body:0002", "body:0003"), _aligned(_item("Frågetext"), "body:0003"))
    ]
    placed = _place(chunks, ordered, title_anchors=frozenset({"body:0001"}))

    assert placed.items[0].plain_text_lines() == ("Classification", "Frågetext")


def test_heading_already_in_the_body_is_not_repeated() -> None:
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", "heading", "Facts"),
        _chunk("body:0003", "paragraph", "Frågan?"),
    )
    item = _item("Facts")
    item = item.model_copy(
        update={
            "body": (
                NativeParagraph(
                    heading_level=None, segments=(NativeTextSegment(text="Facts", marks=()),)
                ),
                NativeParagraph(
                    heading_level=None, segments=(NativeTextSegment(text="Frågetext", marks=()),)
                ),
            )
        }
    )
    placed = _place(
        chunks,
        [(2, ("body:0003",), _aligned(item, "body:0002", "body:0003"))],
        title_anchors=frozenset({"body:0001"}),
    )

    assert placed.items[0].plain_text_lines() == ("Facts", "Frågetext")


def test_heading_over_a_group_forms_the_parent_without_an_instruction_line() -> None:
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", "heading", "Del B: Cellen"),
        _chunk("body:0003", "paragraph", "Fråga ett?"),
        _chunk("body:0004", "paragraph", "Fråga två?"),
        _chunk("body:0005", "heading", "Del C"),
        _chunk("body:0006", "paragraph", "Fråga tre?"),
    )
    placed = _place(
        chunks,
        _ordered(chunks, "body:0003", "body:0004", "body:0006"),
        title_anchors=frozenset({"body:0001"}),
    )

    assert len(placed.parents) == 1
    parent = placed.parents[0]
    assert body_text_lines(parent.instruction) == ("Del B: Cellen",)
    assert parent.item_ids == ("item_001", "item_002")
    # The lone question under the next heading carries it in its own body instead.
    assert placed.items[2].plain_text_lines()[0] == "Del C"


def test_group_heading_opens_the_parent_instruction_ahead_of_printed_instruction_text() -> None:
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", "heading", "Ord och begrepp"),
        _chunk("body:0003", "paragraph", "Fyll i rätt ord."),
        _chunk("body:0004", "paragraph", "Fråga ett?"),
        _chunk("body:0005", "paragraph", "Fråga två?"),
    )
    instruction = ProducedMetadata(text="Fyll i rätt ord.", source_anchors=("body:0003",))
    placed = _place(
        chunks,
        _ordered(chunks, "body:0004", "body:0005"),
        instructions=(instruction,),
        title_anchors=frozenset({"body:0001"}),
    )

    assert len(placed.parents) == 1
    assert body_text_lines(placed.parents[0].instruction) == ("Ord och begrepp", "Fyll i rätt ord.")
    assert placed.parents[0].item_ids == ("item_001", "item_002")


def test_opening_heading_is_the_exam_title_and_never_a_question_heading() -> None:
    chunks = (
        _chunk("body:0001", "heading", "Celler och energi"),
        _chunk("body:0002", "paragraph", "Fråga ett?"),
        _chunk("body:0003", "paragraph", "Fråga två?"),
    )
    placed = _place(chunks, _ordered(chunks, "body:0002", "body:0003"))

    assert placed.parents == ()
    assert all("Celler och energi" not in item.plain_text_lines() for item in placed.items)


def test_heading_of_only_a_question_number_and_points_keeps_the_label_until_the_final_gate() -> (
    None
):
    # D12 extension (review F1): item headings keep points wording; the final gate removes it.
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", "heading", "Fråga 3 (2 p)"),
        _chunk("body:0003", "paragraph", "Frågan?"),
    )
    item = _item("Frågetext").model_copy(update={"printed_label": "Fråga 3"})
    placed = _place(
        chunks,
        [(2, ("body:0003",), _aligned(item, "body:0003"))],
        title_anchors=frozenset({"body:0001"}),
    )

    assert placed.items[0].plain_text_lines() == ("(2 p)", "Frågetext")
    assert with_settled_points_wording(
        placed.items[0].model_copy(update={"points": 2})
    ).plain_text_lines() == ("Frågetext",)
    assert with_settled_points_wording(
        placed.items[0].model_copy(update={"points": 3})
    ).plain_text_lines() == ("(2 p)", "Frågetext")


def test_source_text_fallback_keeps_the_printed_points() -> None:
    chunks = (
        _chunk("body:0001", "paragraph", "15. Skriv en mening om cellen. (3 p)"),
        _chunk("body:0002", "paragraph", "____"),
    )

    item = review_source_item(chunks, "Kontrollera frågan manuellt.")

    assert item.points == 3
