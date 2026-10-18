"""Section placement reads the source alignment, never the wording (TASK-SKRIPT-39-04-13).

Whether an item already shows a heading or instruction, and where a joined instruction
stands in its body, follow which source chunk each body paragraph is aligned to. Each case
pairs a body whose wording would mislead a text match with the alignment that decides.
"""

from collections.abc import Sequence

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import AlignedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_instructions import (
    Placed,
    place_section_instructions,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)

_TITLE = frozenset({"body:0001"})


def _chunk(anchor: str, kind: str, text: str) -> DocxChunk:
    return DocxChunk(anchor=anchor, kind=kind, text=text, marked_text=text)


def _aligned(*paragraphs: tuple[str, str | None]) -> AlignedItem:
    """A converted item whose body paragraph ``text`` shows source chunk ``anchor``."""
    item = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=tuple(
            NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=text, marks=()),))
            for text, _ in paragraphs
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.LLM_PARSED,
        ),
    )
    return AlignedItem(item, tuple(anchor for _, anchor in paragraphs))


def _lines(
    chunks: tuple[DocxChunk, ...],
    placed: Sequence[Placed],
    instructions: tuple[ProducedMetadata, ...] = (),
) -> tuple[str, ...]:
    result = place_section_instructions(chunks, list(placed), instructions, {}, _TITLE)
    (item,) = result.items
    return item.plain_text_lines()


_HEADED = (
    _chunk("body:0001", "heading", "Provets titel"),
    _chunk("body:0002", "heading", "Läs dikten noga"),
    _chunk("body:0003", "paragraph", "Vad handlar dikten om?"),
)


def test_a_reworded_reply_line_aligned_to_the_heading_shows_it_once() -> None:
    item = _aligned(("Läs dikten", "body:0002"), ("Vad handlar den om?", "body:0003"))

    lines = _lines(_HEADED, [(1, ("body:0002", "body:0003"), item)])

    assert lines == ("Läs dikten", "Vad handlar den om?")


def test_a_reply_that_omits_the_heading_gets_the_source_heading() -> None:
    item = _aligned(("Vad handlar dikten om?", "body:0003"))

    lines = _lines(_HEADED, [(1, ("body:0002", "body:0003"), item)])

    assert lines == ("Läs dikten noga", "Vad handlar dikten om?")


def test_a_reply_line_with_the_heading_wording_but_no_alignment_does_not_count() -> None:
    # The reply's copy is aligned to no unique source paragraph, so it is reply wording:
    # the item does not show the heading chunk and gets it in its source form.
    item = _aligned(("Läs dikten noga", None), ("Vad handlar dikten om?", "body:0003"))

    lines = _lines(_HEADED, [(1, ("body:0002", "body:0003"), item)])

    assert lines == ("Läs dikten noga", "Läs dikten noga", "Vad handlar dikten om?")


def test_an_instruction_whose_wording_is_also_a_stem_line_is_still_placed() -> None:
    # The stem repeats the section instruction as one of its own lines. That line shows the
    # question's chunk, not the instruction's, so the instruction still opens the item.
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", "paragraph", "Svara med hela meningar."),
        _chunk("body:0003", "paragraph", "Svara med hela meningar.\nVarför regnar det?"),
    )
    item = _aligned(("Svara med hela meningar.", "body:0003"), ("Varför regnar det?", "body:0003"))
    instruction = ProducedMetadata(text="Svara med hela meningar.", source_anchors=("body:0002",))

    lines = _lines(chunks, [(2, ("body:0003",), item)], (instruction,))

    assert lines == ("Svara med hela meningar.", "Svara med hela meningar.", "Varför regnar det?")


_JOINED = (
    _chunk("body:0001", "heading", "Provets titel"),
    _chunk("body:0002", "paragraph", "1. Läs texten om vulkaner."),
    _chunk("body:0003", "paragraph", "Använd ordlistan nedan."),
    _chunk("body:0004", "paragraph", "a) Vad är magma?"),
)
_JOINED_INSTRUCTION = ProducedMetadata(
    text="Använd ordlistan nedan.", source_anchors=("body:0003",)
)


def test_a_joined_instruction_stands_at_its_source_place_among_reworded_lines() -> None:
    # Neither reply line starts with its source wording; the alignment still puts the
    # instruction between the question's first and second chunk.
    item = _aligned(("Läs om vulkaner.", "body:0002"), ("Förklara magma.", "body:0004"))

    lines = _lines(_JOINED, [(1, ("body:0002", "body:0004"), item)], (_JOINED_INSTRUCTION,))

    assert lines == ("Läs om vulkaner.", "Använd ordlistan nedan.", "Förklara magma.")


def test_an_unaligned_reply_line_keeps_the_place_of_the_line_before_it() -> None:
    item = _aligned(
        ("Läs om vulkaner.", "body:0002"),
        ("Tänk efter först.", None),
        ("Förklara magma.", "body:0004"),
    )

    lines = _lines(_JOINED, [(1, ("body:0002", "body:0004"), item)], (_JOINED_INSTRUCTION,))

    assert lines == (
        "Läs om vulkaner.",
        "Tänk efter först.",
        "Använd ordlistan nedan.",
        "Förklara magma.",
    )


def test_a_joined_instruction_the_reply_shows_reworded_stands_once_in_its_source_form() -> None:
    item = _aligned(
        ("Läs om vulkaner.", "body:0002"),
        ("Ta hjälp av ordlistan.", "body:0003"),
        ("Förklara magma.", "body:0004"),
    )

    lines = _lines(_JOINED, [(1, ("body:0002", "body:0004"), item)], (_JOINED_INSTRUCTION,))

    assert lines == ("Läs om vulkaner.", "Använd ordlistan nedan.", "Förklara magma.")


def test_a_reply_that_splits_a_joined_instruction_shows_it_once_at_its_first_line() -> None:
    item = _aligned(
        ("Läs om vulkaner.", "body:0002"),
        ("Använd", "body:0003"),
        ("ordlistan.", "body:0003"),
        ("Förklara magma.", "body:0004"),
    )

    lines = _lines(_JOINED, [(1, ("body:0002", "body:0004"), item)], (_JOINED_INSTRUCTION,))

    assert lines == ("Läs om vulkaner.", "Använd ordlistan nedan.", "Förklara magma.")


def test_a_body_aligned_to_nothing_ends_with_the_joined_instruction() -> None:
    item = _aligned(("Läs om vulkaner.", None), ("Förklara magma.", None))

    lines = _lines(_JOINED, [(1, ("body:0002", "body:0004"), item)], (_JOINED_INSTRUCTION,))

    assert lines == ("Läs om vulkaner.", "Förklara magma.", "Använd ordlistan nedan.")


def test_an_aligned_item_body_and_chunks_must_have_the_same_length() -> None:
    item = _aligned(("Läs om vulkaner.", "body:0002")).item

    with pytest.raises(ValueError, match="aligned chunks"):
        AlignedItem(item, ())
