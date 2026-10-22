"""A part opener's Word kind never changes a lead-in label decision (review-3 N3b residual).

A heading between two instruction lines labels a stretch of a lead-in only when neither
neighbour is section structure. Every plan part opener is section structure whatever its Word
kind, so a paragraph part opener after such a heading decides the heading's role exactly as
the same opener printed as a Word heading does.
"""

from uuid import UUID

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    ManifestQuestion,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import (
    assign_points_lines,
    manifest_questions,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)

pytestmark = pytest.mark.unit

_INSTRUCTION = "Läs texten nedan och svara på frågorna."
_OWN = (1, 2, 6)


def _entry(anchor: str, text: str) -> dict[str, JsonValue]:
    return {
        "source_anchors": [anchor],
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "free_text",
        "key_source": None,
        "facit_text": None,
        "printed_label": None,
        "body": [{"segments": [{"kind": "text", "text": text, "accepted_values": []}]}],
        "points": 2,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }


def _texts(paragraphs: tuple[NativeParagraph, ...]) -> list[str]:
    return [
        segment.text
        for paragraph in paragraphs
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]


def _placed(opener_kind: str) -> tuple[object, ...]:
    """The built document's instructions, parents and items, with the DEL 2 opener as
    ``opener_kind``."""
    lines = (
        ("heading", "DEL 1: Ordklasser (4 p)"),
        ("paragraph", "1. Förklara vad ett substantiv är."),
        ("paragraph", "2. Förklara vad ett adjektiv är."),
        ("paragraph", _INSTRUCTION),
        ("heading", "Texten"),
        (opener_kind, "DEL 2: Läsförståelse (2 p)"),
        ("paragraph", "3. Vem är huvudpersonen?"),
    )
    chunks = tuple(
        DocxChunk(f"body:{index + 1:04d}", kind, text, text)
        for index, (kind, text) in enumerate(lines)
    )
    manifest = ExamManifest(
        questions=tuple(
            ManifestQuestion(f"q{number + 1}", (chunks[index].anchor,), (), ())
            for number, index in enumerate(_OWN)
        ),
        contexts=(),
        title_anchors=(),
        header=(),
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=(),
    )
    state = DocxBuildState(
        origin_kind="docx_import",
        job_id=UUID(int=1),
        document_id=UUID(int=2),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=manifest_questions(assign_points_lines(manifest, chunks)),
    )
    instructions: list[JsonValue] = [
        {"text": chunks[index].text, "source_anchors": [chunks[index].anchor]}
        for index in (3, 4, 5)
    ]
    admit_batch(
        {
            "items": [_entry(chunks[index].anchor, chunks[index].text) for index in _OWN],
            "instructions": instructions,
        },
        state,
    )
    document = state.result().document
    anchor_of = {item.item_id: item.source_anchor for item in document.items}
    return (
        tuple(_texts(document.instructions)),
        tuple(
            (
                parent.printed_total,
                tuple(anchor_of[i] for i in parent.item_ids),
                tuple(_texts(parent.instruction)),
            )
            for parent in document.parents
        ),
        tuple(
            (item.source_anchor, item.points, item.plain_text_lines())
            for item in sorted(document.items, key=lambda item: item.sequence)
        ),
    )


def test_a_paragraph_part_opener_decides_a_lead_in_label_as_a_heading_opener_does() -> None:
    # Before the fix the paragraph opener let "Texten" label the lead-in, so the instruction
    # left the document's instructions and joined the DEL 2 question's item.
    assert _placed("paragraph") == _placed("heading")
