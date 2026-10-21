"""Nested part lines over the same questions open one parent (review-3 N1 reproduction 2, N3b).

A part's line is never exam-wide text. When an outer part ("Del 1: Grammatik (10 p)") and an
inner part ("Uppgift 1.1: Subjekt (4 p)", inner because 1.2 and 1.3 print no total) cover the
same questions, they form one parent whose instruction holds the outer line, then the inner.
"""

from uuid import uuid4

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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeParseOrigin,
)

pytestmark = pytest.mark.unit


def _entry(anchor: str, text: str, label: str) -> dict[str, JsonValue]:
    return {
        "source_anchors": [anchor],
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "free_text",
        "key_source": None,
        "facit_text": None,
        "printed_label": label,
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


@pytest.mark.parametrize("later_kind", ["paragraph", "heading"])
def test_nested_part_lines_over_the_same_questions_open_one_parent(later_kind: str) -> None:
    lines = (
        ("heading", "Del 1: Grammatik (10 p)"),
        ("heading", "Uppgift 1.1: Subjekt (4 p)"),
        ("paragraph", "Stryk under subjektet."),
        (later_kind, "Uppgift 1.2: Förklara predikat."),
        (later_kind, "Uppgift 1.3: Förklara objekt."),
    )
    chunks = tuple(
        DocxChunk(f"body:{index + 1:04d}", kind, text, text)
        for index, (kind, text) in enumerate(lines)
    )
    manifest = ExamManifest(
        questions=tuple(
            ManifestQuestion(f"q{number + 1}", tuple(chunks[i].anchor for i in own), (), ())
            for number, own in enumerate(((1, 2), (3,), (4,)))
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
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=manifest_questions(assign_points_lines(manifest, chunks)),
    )
    entries: list[JsonValue] = [
        _entry("body:0003", "Stryk under subjektet.", "1.1"),
        _entry("body:0004", "Förklara predikat.", "1.2"),
        _entry("body:0005", "Förklara objekt.", "1.3"),
    ]

    admit_batch({"items": entries}, state)
    document = state.result().document

    items = sorted(document.items, key=lambda item: item.sequence)
    assert [item.source_anchor for item in items] == ["body:0003", "body:0004", "body:0005"]
    assert all(item.review.parse_origin is NativeParseOrigin.LLM_PARSED for item in items)
    # How q1's points are shared is a separate decision; this unit keeps it.
    assert [item.points for item in items] == [2, 1, 1]
    assert not _texts(document.instructions)
    [parent] = document.parents
    assert parent.item_ids == tuple(item.item_id for item in items)
    assert parent.printed_total == 10
    assert _texts(parent.instruction) == ["Del 1: Grammatik", "Uppgift 1.1: Subjekt"]
