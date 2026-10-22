"""Adversarial section-share probe: an unrepresentable tick uses source review, not zero.

This is a constructed boundary input, not a live-provider conversion recording.
"""

from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedMatchPair,
    ProducedMetadata,
    ProducedParagraph,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_item import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    native_export_blockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text

pytestmark = pytest.mark.unit


def test_impossible_section_tick_share_keeps_source_as_blocking_review_item():
    rows = tuple(f"Rad {number}" for number in range(1, 102))
    text = "Kategorisera varje rad.\n" + "\n".join(rows)
    chunks = (
        DocxChunk("body:0001", "heading", "Kategorisering (1 poäng)", "Kategorisering (1 poäng)"),
        DocxChunk("body:0002", "table", text, text),
    )
    produced = ProducedItem(
        source_anchors=("body:0002",),
        outcome="converted",
        review_reason=None,
        kind=NativeExamItemKind.MATCHING,
        key_source="copied",
        facit_text="Alla rader hör till kategori A.",
        body=(
            ProducedParagraph(
                segments=(
                    ProducedSegment(
                        kind="text",
                        text="Kategorisera varje rad.",
                        accepted_values=(),
                    ),
                )
            ),
        ),
        points=None,
        choices=(),
        match_left=rows,
        match_right=("Kategori A", "Kategori B"),
        match_pairs=tuple(ProducedMatchPair(left=row, right="Kategori A") for row in rows),
    )
    state = DocxBuildState(
        origin_kind="docx_import",
        job_id=uuid4(),
        document_id=uuid4(),
        filename="gransprov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(("body:0002",),),
    )
    state.accepted.append(
        (aligned_native_item(produced, language="sv", foreign_chunks=()), ("body:0002",))
    )
    state.claimed.update(chunk.anchor for chunk in chunks)
    state.instructions = (
        ProducedMetadata(text=chunks[0].text, points=1, source_anchors=("body:0001",)),
    )

    result = state.result()

    (item,) = result.document.items
    assert item.kind is NativeExamItemKind.FREE_TEXT
    assert item.tick_points is None
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    assert "0,01" in " ".join(item.review.reasons)
    assert body_plain_text(item.body) == text
    assert any(event.code == "invalid_tick_value" for event in result.events)
    assert any(
        blocker.reason == "unbuilt_question" for blocker in native_export_blockers(result.document)
    )
