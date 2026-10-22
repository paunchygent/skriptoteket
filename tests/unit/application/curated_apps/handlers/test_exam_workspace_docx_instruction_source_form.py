"""An instruction an item shows stands in its source form, and nothing else of the item moves.

Review 7a083063 of TASK-SKRIPT-39-04-13 (F1-F3): replies that pass real admission, put
through assembly. Restoring an instruction's source form must never remove another chunk's
text, never drop a response gap the item placed in it, and never reorder the instruction's
own chunks. The inputs are synthetic adversarial replies, not recorded exams.
"""

from base64 import b64decode
from uuid import uuid4

from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildEnvelope
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
    DocxSourceParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_asset_ids

_PICTURE = DocxImage(
    b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jJ1kAAAAASUVORK5CYII="
    ),
    "image/png",
)


def _text(value: str) -> dict[str, JsonValue]:
    return {"kind": "text", "text": value, "asset_id": None, "accepted_values": []}


def _picture() -> dict[str, JsonValue]:
    return {"kind": "asset", "text": None, "asset_id": _PICTURE.asset_id, "accepted_values": []}


def _gap() -> dict[str, JsonValue]:
    return {"kind": "gap", "text": None, "asset_id": None, "accepted_values": []}


def _assembled(
    wordings: tuple[str, ...],
    instruction: tuple[int, ...],
    body: list[list[dict[str, JsonValue]]],
    *,
    kind: str = "free_text",
    picture_in: int | None = None,
) -> NativeExamItem:
    """The one question's assembled item when the reply lists ``instruction`` (1-based
    chunk numbers) as an instruction and every other chunk as its item."""
    chunks = tuple(
        DocxChunk(
            f"body:{n:04d}",
            "paragraph",
            wording,
            wording,
            (_PICTURE,) if n == picture_in else (),
            paragraphs=(DocxSourceParagraph(0, wording),),
        )
        for n, wording in enumerate(wordings, 1)
    )
    state = DocxBuildState(
        origin_kind="docx_import",
        job_id=uuid4(),
        document_id=uuid4(),
        filename="instruktion.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(tuple(chunk.anchor for chunk in chunks),),
    )
    listed: list[JsonValue] = [f"body:{n:04d}" for n in instruction]
    held: list[JsonValue] = [
        chunk.anchor for n, chunk in enumerate(chunks, 1) if n not in instruction
    ]
    paragraphs: list[JsonValue] = [{"segments": list(segments)} for segments in body]
    content: dict[str, JsonValue] = {
        "title": None,
        "instructions": [
            {
                "text": "\n".join(wordings[n - 1] for n in instruction) or "Betrakta bilden.",
                "source_anchors": listed,
                "points": None,
            }
        ],
        "answer_key_anchors": [],
        "items": [
            {
                "source_anchors": held,
                "outcome": "converted",
                "review_reason": None,
                "kind": kind,
                "key_source": None,
                "facit_text": None,
                "body": paragraphs,
                "points": None,
                "choices": [],
                "printed_label": None,
                "conflict_kind": None,
                "match_left": [],
                "match_right": [],
                "match_pairs": [],
                "criteria": [],
            }
        ],
    }
    DocxBuildEnvelope.model_validate(content)
    admit_batch(content, state)
    ((admitted, _),) = state.accepted
    assert admitted.item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    (item,) = state.result().document.items
    return item


def test_a_picture_only_instruction_sharing_a_line_with_the_stem_keeps_the_stem() -> None:
    item = _assembled(
        ("1. Undersök bilden.", "", "Vilket djur visas?"),
        (2,),
        [[_text("1. Undersök bilden.")], [_picture(), _text("Vilket djur visas?")]],
        picture_in=2,
    )

    assert item.plain_text_lines() == ("1. Undersök bilden.", "Vilket djur visas?")
    assert body_asset_ids(item.body) == (_PICTURE.asset_id,)


def test_a_captioned_instruction_picture_sharing_a_line_with_the_stem_keeps_both() -> None:
    item = _assembled(
        ("1. Undersök bilden.", "Se bilden.", "Vilket djur visas?"),
        (2,),
        [[_text("1. Undersök bilden.")], [_picture(), _text("Vilket djur visas?")]],
        picture_in=2,
    )

    assert item.plain_text_lines() == ("1. Undersök bilden.", "Se bilden.", "Vilket djur visas?")
    assert body_asset_ids(item.body) == (_PICTURE.asset_id,)


def test_one_reply_line_around_an_omitted_caption_keeps_the_stem() -> None:
    # One reply paragraph prints the opening, the instruction's picture and the stem; the
    # caption between them is omitted. Each emitted piece carries the source paragraph it
    # was projected from, never the caption by its ordinal (rereview 7a083063 F1).
    item = _assembled(
        ("1. Undersök bilden.", "Se bilden.", "Vilket djur visas?"),
        (2,),
        [[_text("1. Undersök bilden. "), _picture(), _text("Vilket djur visas?")]],
        picture_in=2,
    )

    assert item.plain_text_lines() == ("1. Undersök bilden.", "Se bilden.", "Vilket djur visas?")
    assert body_asset_ids(item.body) == (_PICTURE.asset_id,)


def test_a_gap_the_item_placed_in_an_instruction_chunk_stays_at_its_source_blank() -> None:
    item = _assembled(
        ("1. Fyll i meningen.", "Sveriges huvudstad är ___.", "Kontrollera stavningen."),
        (2,),
        [
            [_text("1. Fyll i meningen.")],
            [_text("Sveriges huvudstad är "), _gap(), _text(".")],
            [_text("Kontrollera stavningen.")],
        ],
        kind="gap_fill",
    )

    (gap,) = item.gaps
    assert [
        (segment.text if isinstance(segment, NativeTextSegment) else segment.gap_id)
        for segment in item.body[1].segments
        if isinstance(segment, NativeTextSegment | NativeGapSegment)
    ] == ["Sveriges huvudstad är ", gap.gap_id, "."]
    assert item.plain_text_lines()[0] == "1. Fyll i meningen."
    assert item.plain_text_lines()[-1] == "Kontrollera stavningen."


def test_a_partly_shown_instruction_keeps_its_chunks_in_source_order() -> None:
    item = _assembled(
        (
            "1. Läs texten om vulkaner.",
            "Läs först hela texten.",
            "Skriv sedan ditt svar.",
            "a) Vad är magma?",
        ),
        (2, 3),
        [
            [_text("1. Läs texten om vulkaner.")],
            [_text("Skriv sedan ditt svar.")],
            [_text("a) Vad är magma?")],
        ],
    )

    assert item.plain_text_lines() == (
        "1. Läs texten om vulkaner.",
        "Läs först hela texten.",
        "Skriv sedan ditt svar.",
        "a) Vad är magma?",
    )
