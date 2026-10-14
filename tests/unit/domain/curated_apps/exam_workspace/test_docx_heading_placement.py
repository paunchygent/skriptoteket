"""Printed headings become question body text or parent instructions (TASK-SKRIPT-39-05-08).

Synthetic placement: chunks and items are built directly, so these tests pin T1 and T2
without a recorded provider reply. A heading over one question opens its body verbatim; a
heading over two or more consecutive questions is the first line of their parent's
instruction, also when no instruction line follows it.
"""

from types import MappingProxyType
from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import (
    assemble_build_result,
    review_source_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_instructions import (
    Placed,
    SectionInstructions,
    place_section_instructions,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeItemReview,
    NativeItemReviewState,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines

_NOTHING_GOVERNED: MappingProxyType[str, frozenset[str]] = MappingProxyType({})


def _chunk(anchor: str, kind: str, text: str) -> DocxChunk:
    return DocxChunk(anchor=anchor, kind=kind, text=text, marked_text=text)


def _item(text: str) -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=(NativeParagraph(segments=(NativeTextSegment(text=text),)),),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.LLM_PARSED,
        ),
    )


def _place(
    chunks: tuple[DocxChunk, ...],
    placed: list[Placed],
    instructions: tuple[ProducedMetadata, ...] = (),
    title_anchors: frozenset[str] = frozenset(),
    governed: MappingProxyType[str, frozenset[str]] = _NOTHING_GOVERNED,
) -> SectionInstructions:
    return place_section_instructions(chunks, placed, instructions, governed, title_anchors)


def _ordered(chunks: tuple[DocxChunk, ...], *anchors: str) -> list[Placed]:
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    return [(positions[anchor], (anchor,), _item(f"Frågetext {anchor}")) for anchor in anchors]


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
    ordered: list[Placed] = [(1, ("body:0002", "body:0003"), _item("Frågetext"))]
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
                NativeParagraph(segments=(NativeTextSegment(text="Facts"),)),
                NativeParagraph(segments=(NativeTextSegment(text="Frågetext"),)),
            )
        }
    )
    placed = _place(chunks, [(2, ("body:0003",), item)], title_anchors=frozenset({"body:0001"}))

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


def test_heading_that_is_only_a_question_number_and_points_leaves_nothing() -> None:
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", "heading", "Fråga 3 (2 p)"),
        _chunk("body:0003", "paragraph", "Frågan?"),
    )
    item = _item("Frågetext").model_copy(update={"printed_label": "Fråga 3"})
    placed = _place(chunks, [(2, ("body:0003",), item)], title_anchors=frozenset({"body:0001"}))

    assert placed.items[0].plain_text_lines() == ("Frågetext",)


def test_section_heading_before_owned_question_headings_forms_the_parent() -> None:
    # A question's own heading is no section boundary: the section heading above two
    # numbered question headings still introduces their parent (review F1).
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", "heading", "Cellens delar"),
        _chunk("body:0003", "heading", "Fråga 1. Beskriv kärnan."),
        _chunk("body:0004", "paragraph", "Förklara kärnans funktion."),
        _chunk("body:0005", "heading", "Fråga 2. Beskriv membranet."),
        _chunk("body:0006", "paragraph", "Förklara membranets funktion."),
    )
    first = _item("Beskriv kärnan.\nFörklara kärnans funktion.").model_copy(
        update={"printed_label": "Fråga 1"}
    )
    second = _item("Beskriv membranet.\nFörklara membranets funktion.").model_copy(
        update={"printed_label": "Fråga 2"}
    )
    ordered: list[Placed] = [
        (2, ("body:0003", "body:0004"), first),
        (4, ("body:0005", "body:0006"), second),
    ]
    instruction = ProducedMetadata(text="Cellens delar", source_anchors=("body:0002",))
    placed = _place(
        chunks, ordered, instructions=(instruction,), title_anchors=frozenset({"body:0001"})
    )

    assert len(placed.parents) == 1
    assert body_text_lines(placed.parents[0].instruction) == ("Cellens delar",)
    assert placed.parents[0].item_ids == ("item_001", "item_002")
    # The questions keep their own headings in their bodies, exactly once.
    assert placed.items[0].plain_text_lines()[0].startswith("Beskriv kärnan.")
    assert placed.items[1].plain_text_lines()[0].startswith("Beskriv membranet.")
    assert 0 in placed.landed


def test_governing_heading_opens_the_parent_ahead_of_an_earlier_governing_line() -> None:
    # A heading the grouping marks as governing is the parent's first line even when
    # another governing line is printed before it; that line is preserved (review F3).
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", "paragraph", "Namn: ____"),
        _chunk("body:0003", "heading", "Cellens delar"),
        _chunk("body:0004", "paragraph", "Fråga ett?"),
        _chunk("body:0005", "paragraph", "Fråga två?"),
    )
    instructions = (
        ProducedMetadata(text="Namn: ____", source_anchors=("body:0002",)),
        ProducedMetadata(text="Cellens delar", source_anchors=("body:0003",)),
    )
    governed = MappingProxyType(
        {
            "body:0002": frozenset({"body:0004", "body:0005"}),
            "body:0003": frozenset({"body:0004", "body:0005"}),
        }
    )
    placed = _place(
        chunks,
        _ordered(chunks, "body:0004", "body:0005"),
        instructions=instructions,
        title_anchors=frozenset({"body:0001"}),
        governed=governed,
    )

    assert len(placed.parents) == 1
    assert body_text_lines(placed.parents[0].instruction) == ("Cellens delar", "Namn: ____")


def test_line_before_a_section_heading_stays_document_level() -> None:
    # A line printed before the section heading ends at that heading, even with
    # instruction lines on both sides of it; it lands on no item and stays
    # document-level instead of opening the section parent (biology Name line).
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", "paragraph", "Name: ___ Date: ___"),
        _chunk("body:0003", "heading", "A. Multiple choice"),
        _chunk("body:0004", "paragraph", "Choose the best answer."),
        _chunk("body:0005", "paragraph", "Fråga ett?"),
        _chunk("body:0006", "paragraph", "Fråga två?"),
        _chunk("body:0007", "heading", "B. Open questions"),
        _chunk("body:0008", "paragraph", "Fråga tre?"),
    )
    instructions = (
        ProducedMetadata(text="Name: ___ Date: ___", source_anchors=("body:0002",)),
        ProducedMetadata(text="A. Multiple choice", source_anchors=("body:0003",)),
        ProducedMetadata(text="Choose the best answer.", source_anchors=("body:0004",)),
    )
    placed = _place(
        chunks,
        _ordered(chunks, "body:0005", "body:0006", "body:0008"),
        instructions=instructions,
        title_anchors=frozenset({"body:0001"}),
    )

    assert len(placed.parents) == 1
    assert body_text_lines(placed.parents[0].instruction) == (
        "A. Multiple choice",
        "Choose the best answer.",
    )
    assert 0 not in placed.landed
    assert all("Name:" not in line for item in placed.items for line in item.plain_text_lines())


def test_governing_heading_subset_of_wider_parent_opens_every_governed_questions_body() -> None:
    # A heading the grouping marks as governing only q2-q3 never joins the q1-q3
    # parent (D40 exact scope, review F5): parents are flat, so it opens the body
    # of every question it governs. Through the production assembly.
    chunks = (
        _chunk("body:0001", "heading", "Prov"),
        _chunk("body:0002", "paragraph", "Besvara alla frågor."),
        _chunk("body:0003", "paragraph", "Första frågan?"),
        _chunk("body:0004", "heading", "Använd följande ord för fråga två och tre"),
        _chunk("body:0005", "paragraph", "Andra frågan?"),
        _chunk("body:0006", "paragraph", "Tredje frågan?"),
    )
    accepted = (
        (_item("Första frågan?"), ("body:0003",)),
        (_item("Andra frågan?"), ("body:0005",)),
        (_item("Tredje frågan?"), ("body:0006",)),
    )
    instructions = (
        ProducedMetadata(text="Besvara alla frågor.", source_anchors=("body:0002",)),
        ProducedMetadata(
            text="Använd följande ord för fråga två och tre", source_anchors=("body:0004",)
        ),
    )
    governed = MappingProxyType(
        {
            "body:0002": frozenset({"body:0003", "body:0005", "body:0006"}),
            "body:0004": frozenset({"body:0005", "body:0006"}),
        }
    )
    document = assemble_build_result(
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        accepted=accepted,
        review_reasons={},
        instructions=instructions,
        governed=governed,
        title=ProducedMetadata(text="Prov", source_anchors=("body:0001",)),
        questions=tuple(anchors for _, anchors in accepted),
    ).document

    assert len(document.parents) == 1
    parent = document.parents[0]
    assert parent.item_ids == ("item_001", "item_002", "item_003")
    assert body_text_lines(parent.instruction) == ("Besvara alla frågor.",)
    assert "Använd följande ord för fråga två och tre" not in document.items[0].plain_text_lines()
    assert document.items[1].plain_text_lines()[0] == "Använd följande ord för fråga två och tre"
    assert document.items[2].plain_text_lines()[0] == "Använd följande ord för fråga två och tre"


def test_source_text_fallback_keeps_the_printed_points() -> None:
    chunks = (
        _chunk("body:0001", "paragraph", "15. Skriv en mening om cellen. (3 p)"),
        _chunk("body:0002", "paragraph", "____"),
    )

    item = review_source_item(chunks, "Kontrollera frågan manuellt.")

    assert item.points == 3
