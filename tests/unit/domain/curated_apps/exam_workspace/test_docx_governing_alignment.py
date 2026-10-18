"""Governing chunks and left-out own chunks follow the source alignment (TASK-SKRIPT-39-04-14).

Which body paragraphs a governing chunk takes out of an item, and whether an item already
shows a left-out own chunk of its question, follow which source chunk each body paragraph
is aligned to. Each case pairs wording that would mislead a text match with the alignment
that decides.
"""

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_governing_chunks import (
    ReleasedChunks,
    release_governing_chunks,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import AlignedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_own_instructions import (
    left_out_chunks,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)

_GOVERNING = "body:0002"
_STEM = "body:0003"
_INSTRUCTION = "Läs texten nedan och svara på frågorna 1–3 med hela meningar."
_QUESTION = "Vilket år skrevs romanen och vem skrev den?"
_CHUNKS = (
    DocxChunk("body:0001", "heading", "Del A", "Del A"),
    DocxChunk(_GOVERNING, "paragraph", _INSTRUCTION, _INSTRUCTION),
    DocxChunk(_STEM, "paragraph", _QUESTION, _QUESTION),
)
_GOVERNED = {_GOVERNING: frozenset({_STEM, "body:0004", "body:0005"})}


def _body(*texts: str) -> tuple[NativeParagraph, ...]:
    return tuple(
        NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=text, marks=()),))
        for text in texts
    )


def _text(text: str) -> dict[str, object]:
    return {"kind": "text", "text": text, "accepted_values": [], "asset_id": None}


def _aligned(*paragraphs: tuple[str, str | None]) -> AlignedItem:
    """A converted item whose body paragraph ``text`` shows source chunk ``anchor``."""
    item = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=_body(*(text for text, _ in paragraphs)),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.LLM_PARSED,
        ),
        source_anchor=_GOVERNING,
    )
    return AlignedItem(item, tuple(anchor for _, anchor in paragraphs))


def _released(aligned: AlignedItem) -> ReleasedChunks:
    return release_governing_chunks(_CHUNKS, ((aligned, (_GOVERNING, _STEM)),), (), _GOVERNED)


def _only_item(released: ReleasedChunks) -> AlignedItem:
    ((aligned, anchors),) = released.accepted
    assert anchors == (_STEM,)
    assert aligned.item.source_anchor == _STEM
    return aligned


def _instructions(released: ReleasedChunks) -> tuple[ProducedMetadata, ...]:
    return released.instructions


def test_a_reworded_governing_line_the_aligner_ties_to_the_chunk_leaves_the_item() -> None:
    # The reply rewords the instruction; the real aligner still ties the line to its chunk,
    # so the line leaves the item although no text match against the source would find it.
    produced = ProducedItem.model_validate(
        {
            "source_anchors": [_GOVERNING, _STEM],
            "outcome": "converted",
            "review_reason": None,
            "kind": "free_text",
            "key_source": None,
            "facit_text": None,
            "body": [
                {"segments": [_text("Läs texten och svara på frågorna 1–3.")]},
                {"segments": [_text(_QUESTION)]},
            ],
            "points": 1,
            "choices": [],
        }
    )
    aligned = aligned_native_item(produced, chunks=_CHUNKS[1:], language="sv")
    assert aligned.chunks == (_GOVERNING, _STEM)
    assert aligned.item.plain_text_lines()[0] != _INSTRUCTION

    released = _released(aligned)

    item = _only_item(released)
    assert item.item.plain_text_lines() == (_QUESTION,)
    assert item.chunks == (_STEM,)
    assert released.events == ()
    assert _instructions(released) == (
        ProducedMetadata(text=_INSTRUCTION, source_anchors=(_GOVERNING,)),
    )


def test_governing_wording_inside_a_stem_paragraph_stays_in_the_stem() -> None:
    # The stem paragraph opens with the instruction's exact wording, but it is aligned to the
    # stem chunk: it is the question's text and keeps every word.
    stem = f"{_INSTRUCTION} {_QUESTION}"
    released = _released(_aligned((stem, _STEM)))

    item = _only_item(released)
    assert item.item.plain_text_lines() == (stem,)
    assert released.events == ()


def test_governing_wording_in_an_unaligned_paragraph_stays() -> None:
    # A reply line that copies the instruction but is aligned to no unique source paragraph
    # is reply wording, not the chunk.
    released = _released(_aligned((_INSTRUCTION, None), (_QUESTION, _STEM)))

    item = _only_item(released)
    assert item.item.plain_text_lines() == (_INSTRUCTION, _QUESTION)
    assert item.chunks == (None, _STEM)
    assert released.events == ()


def test_a_reply_that_omits_the_governing_chunk_keeps_its_item_and_reports_nothing() -> None:
    released = _released(_aligned((_QUESTION, _STEM)))

    item = _only_item(released)
    assert item.item.plain_text_lines() == (_QUESTION,)
    assert released.events == ()
    assert _instructions(released) == (
        ProducedMetadata(text=_INSTRUCTION, source_anchors=(_GOVERNING,)),
    )


def test_a_governing_chunk_that_is_the_whole_body_is_kept_and_reported() -> None:
    released = _released(_aligned(("Läs texten.", _GOVERNING), ("och svara.", _GOVERNING)))

    item = _only_item(released)
    assert item.item.plain_text_lines() == ("Läs texten.", "och svara.")
    assert [(e.code, e.anchors) for e in released.events] == [
        ("governing_text_kept", (_GOVERNING,))
    ]


def test_every_paragraph_aligned_to_the_governing_chunk_leaves_wherever_it_stands() -> None:
    released = _released(
        _aligned(("Läs texten.", _GOVERNING), (_QUESTION, _STEM), ("Svara kort.", _GOVERNING))
    )

    assert _only_item(released).item.plain_text_lines() == (_QUESTION,)


_LEFT_OUT = DocxChunk("body:0004", "paragraph", "Motivera ditt svar.", "Motivera ditt svar.")


def test_a_left_out_chunk_whose_wording_stands_in_another_chunks_paragraph_is_marked() -> None:
    aligned = _aligned((f"{_QUESTION} Motivera ditt svar.", _STEM))

    assert left_out_chunks(aligned, (_LEFT_OUT,)) == (_LEFT_OUT,)


def test_a_left_out_chunk_a_reworded_paragraph_is_aligned_to_is_shown() -> None:
    aligned = _aligned((_QUESTION, _STEM), ("Ge skäl för svaret.", _LEFT_OUT.anchor))

    assert left_out_chunks(aligned, (_LEFT_OUT,)) == ()


def test_a_left_out_chunk_printed_only_as_a_choice_is_marked() -> None:
    # Choices carry no chunk alignment, so their wording is no evidence the item shows it.
    aligned = _aligned((_QUESTION, _STEM))
    item = aligned.item.model_copy(
        update={
            "kind": NativeExamItemKind.SINGLE_CHOICE,
            "choices": (NativeChoice(choice_id="choice_001", body=_body("Motivera ditt svar.")),),
        }
    )

    assert left_out_chunks(AlignedItem(item, aligned.chunks), (_LEFT_OUT,)) == (_LEFT_OUT,)
