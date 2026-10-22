"""Section, parent, governing and subsection headings place parents and bodies.

A section heading above owned question headings forms their parent; governing
lines order the parent's instruction; titles above subsections land once and
never repeat over every group.
"""

from types import MappingProxyType
from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import assemble_build_result
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxSourceParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_instructions import Placed
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines
from tests.unit.domain.curated_apps.exam_workspace.docx_heading_placement_test_support import (
    aligned,
    chunk,
    item,
    ordered,
    place,
)


def _titled(anchor: str, text: str, level: int) -> DocxChunk:
    return DocxChunk(
        anchor=anchor,
        kind="heading",
        text=text,
        marked_text=text,
        paragraphs=(DocxSourceParagraph(offset=0, text=text, heading_level=level),),
    )


def test_section_heading_before_owned_question_headings_forms_the_parent() -> None:
    # A question's own heading is no section boundary: the section heading above two
    # numbered question headings still introduces their parent (review F1).
    chunks = (
        chunk("body:0001", "heading", "Provets titel"),
        chunk("body:0002", "heading", "Cellens delar"),
        chunk("body:0003", "heading", "Fråga 1. Beskriv kärnan."),
        chunk("body:0004", "paragraph", "Förklara kärnans funktion."),
        chunk("body:0005", "heading", "Fråga 2. Beskriv membranet."),
        chunk("body:0006", "paragraph", "Förklara membranets funktion."),
    )
    first = item("Beskriv kärnan.\nFörklara kärnans funktion.").model_copy(
        update={"printed_label": "Fråga 1"}
    )
    second = item("Beskriv membranet.\nFörklara membranets funktion.").model_copy(
        update={"printed_label": "Fråga 2"}
    )
    ordered: list[Placed] = [
        (2, ("body:0003", "body:0004"), aligned(first, "body:0003")),
        (4, ("body:0005", "body:0006"), aligned(second, "body:0005")),
    ]
    instruction = ProducedMetadata(text="Cellens delar", source_anchors=("body:0002",))
    placed = place(
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
        chunk("body:0001", "heading", "Provets titel"),
        chunk("body:0002", "paragraph", "Namn: ____"),
        chunk("body:0003", "heading", "Cellens delar"),
        chunk("body:0004", "paragraph", "Fråga ett?"),
        chunk("body:0005", "paragraph", "Fråga två?"),
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
    placed = place(
        chunks,
        ordered(chunks, "body:0004", "body:0005"),
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
        chunk("body:0001", "heading", "Provets titel"),
        chunk("body:0002", "paragraph", "Name: ___ Date: ___"),
        chunk("body:0003", "heading", "A. Multiple choice"),
        chunk("body:0004", "paragraph", "Choose the best answer."),
        chunk("body:0005", "paragraph", "Fråga ett?"),
        chunk("body:0006", "paragraph", "Fråga två?"),
        chunk("body:0007", "heading", "B. Open questions"),
        chunk("body:0008", "paragraph", "Fråga tre?"),
    )
    instructions = (
        ProducedMetadata(text="Name: ___ Date: ___", source_anchors=("body:0002",)),
        ProducedMetadata(text="A. Multiple choice", source_anchors=("body:0003",)),
        ProducedMetadata(text="Choose the best answer.", source_anchors=("body:0004",)),
    )
    placed = place(
        chunks,
        ordered(chunks, "body:0005", "body:0006", "body:0008"),
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
        chunk("body:0001", "heading", "Prov"),
        chunk("body:0002", "paragraph", "Besvara alla frågor."),
        chunk("body:0003", "paragraph", "Första frågan?"),
        chunk("body:0004", "heading", "Använd följande ord för fråga två och tre"),
        chunk("body:0005", "paragraph", "Andra frågan?"),
        chunk("body:0006", "paragraph", "Tredje frågan?"),
    )
    accepted = (
        (aligned(item("Första frågan?"), "body:0003"), ("body:0003",)),
        (aligned(item("Andra frågan?"), "body:0005"), ("body:0005",)),
        (aligned(item("Tredje frågan?"), "body:0006"), ("body:0006",)),
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
        origin_kind="docx_import",
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


def test_section_title_above_subsections_opens_its_own_questions_once() -> None:
    # TASK-SKRIPT-39-09-08 walk: a Heading 1 directly above a Heading 2 reached no
    # question and became exam-wide text repeated above every group.
    chunks = (
        _titled("body:0001", "Formateringsprov", 1),
        _titled("body:0002", "Del A: Grundbegrepp", 1),
        _titled("body:0003", "Flervalsfrågor", 2),
        chunk("body:0004", "paragraph", "1. Fråga ett?"),
        chunk("body:0005", "paragraph", "2. Fråga två?"),
        _titled("body:0006", "Del B: Resonemang", 1),
        _titled("body:0007", "Fritextfrågor", 2),
        _titled("body:0008", "Energi", 3),
        chunk("body:0009", "paragraph", "3. Fråga tre?"),
    )
    instructions = (
        ProducedMetadata(text="Del A: Grundbegrepp", source_anchors=("body:0002",)),
        ProducedMetadata(text="Del B: Resonemang", source_anchors=("body:0006",)),
    )
    placed = place(
        chunks,
        ordered(chunks, "body:0004", "body:0005", "body:0009"),
        instructions=instructions,
        title_anchors=frozenset({"body:0001"}),
    )

    assert set(placed.landed) == {0, 1}
    assert len(placed.parents) == 1
    assert body_text_lines(placed.parents[0].instruction) == (
        "Del A: Grundbegrepp",
        "Flervalsfrågor",
    )
    assert placed.parents[0].item_ids == ("item_001", "item_002")
    assert placed.items[2].plain_text_lines()[:3] == (
        "Del B: Resonemang",
        "Fritextfrågor",
        "Energi",
    )
    shown = [line for item in placed.items for line in item.plain_text_lines()]
    assert "Del A: Grundbegrepp" not in shown
    assert shown.count("Del B: Resonemang") == 1


def test_section_title_over_two_subsection_parents_opens_the_first_parent_only() -> None:
    chunks = (
        _titled("body:0001", "Provets titel", 1),
        _titled("body:0002", "Del A", 1),
        _titled("body:0003", "Flerval", 2),
        chunk("body:0004", "paragraph", "1. Fråga ett?"),
        chunk("body:0005", "paragraph", "2. Fråga två?"),
        _titled("body:0006", "Fritext", 2),
        chunk("body:0007", "paragraph", "3. Fråga tre?"),
        chunk("body:0008", "paragraph", "4. Fråga fyra?"),
    )
    placed = place(
        chunks,
        ordered(chunks, "body:0004", "body:0005", "body:0007", "body:0008"),
        title_anchors=frozenset({"body:0001"}),
    )

    assert [body_text_lines(parent.instruction) for parent in placed.parents] == [
        ("Del A", "Flerval"),
        ("Fritext",),
    ]
    assert [parent.item_ids for parent in placed.parents] == [
        ("item_001", "item_002"),
        ("item_003", "item_004"),
    ]
    assert all("Del A" not in item.plain_text_lines() for item in placed.items)


def test_points_labelled_section_heading_opens_its_own_questions() -> None:
    # A styled heading is a title even when its label is short and prints points; a
    # plain "Total: 59 points" paragraph is no heading at all.
    chunks = (
        _titled("body:0001", "Unit test", 1),
        chunk("body:0002", "paragraph", "Total: 59 points"),
        _titled("body:0003", "Vocabulary Matching (9 points)", 2),
        chunk("body:0004", "paragraph", "1. Fråga ett?"),
        chunk("body:0005", "paragraph", "2. Fråga två?"),
        _titled("body:0006", "Language Choice (6 points)", 2),
        chunk("body:0007", "paragraph", "3. Fråga tre?"),
        chunk("body:0008", "paragraph", "4. Fråga fyra?"),
    )
    placed = place(
        chunks,
        ordered(chunks, "body:0004", "body:0005", "body:0007", "body:0008"),
        title_anchors=frozenset({"body:0001"}),
    )

    assert [body_text_lines(parent.instruction) for parent in placed.parents] == [
        ("Vocabulary Matching",),
        ("Language Choice",),
    ]
