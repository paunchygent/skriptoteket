"""A chunk between a question's own anchors belongs to that question."""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    ManifestQuestion,
    SharedContext,
    claim_inner_chunks,
)

pytestmark = pytest.mark.unit


def _chunks(count: int) -> tuple[DocxChunk, ...]:
    return tuple(
        DocxChunk(
            anchor=f"a{i}",
            kind="table" if i == 3 else "paragraph",
            text=f"t{i}",
            marked_text=f"t{i}",
        )
        for i in range(count)
    )


def _q(question_id: str, *indexes: int) -> ManifestQuestion:
    return ManifestQuestion(question_id, tuple(f"a{i}" for i in indexes), (), ())


def _manifest(
    questions: tuple[ManifestQuestion, ...],
    unplaced: tuple[int, ...],
    contexts: tuple[SharedContext, ...] = (),
) -> ExamManifest:
    return ExamManifest(
        questions=questions,
        contexts=contexts,
        title_anchors=(),
        header=(),
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=tuple(f"a{i}" for i in unplaced),
    )


def test_a_table_between_anchors_joins_the_question() -> None:
    manifest = _manifest((_q("q1", 1, 2, 4, 5),), unplaced=(0, 3, 6))
    result = claim_inner_chunks(manifest, _chunks(7))
    assert result.questions[0].anchors == ("a1", "a2", "a3", "a4", "a5")
    assert result.unplaced_anchors == ("a0", "a6")


def test_chunks_before_first_and_after_last_anchor_stay_unplaced() -> None:
    manifest = _manifest((_q("q1", 2, 4),), unplaced=(1, 5))
    assert claim_inner_chunks(manifest, _chunks(7)) == manifest


def test_a_context_inside_a_span_is_not_moved() -> None:
    context = SharedContext("a3", "shared_passage", "exam", ("q1",))
    manifest = _manifest((_q("q1", 1, 5),), unplaced=(), contexts=(context,))
    assert claim_inner_chunks(manifest, _chunks(7)) == manifest


def test_overlapping_spans_move_nothing() -> None:
    manifest = _manifest((_q("q1", 1, 5), _q("q2", 2, 6)), unplaced=(3,))
    assert claim_inner_chunks(manifest, _chunks(8)) == manifest


def test_a_chunk_only_one_overlapping_span_holds_still_joins_that_question() -> None:
    manifest = _manifest((_q("q1", 1, 5), _q("q2", 4, 7)), unplaced=(2, 3))
    result = claim_inner_chunks(manifest, _chunks(8))
    assert result.questions[0].anchors == ("a1", "a2", "a3", "a5")
    assert result.unplaced_anchors == ()
