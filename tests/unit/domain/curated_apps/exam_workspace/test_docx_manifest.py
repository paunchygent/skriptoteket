"""Adversarial grouping outputs against the anchors of a real corpus DOCX."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ManifestInvalid,
    manifest_from_output,
    question_source,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_markdown import (  # noqa: E501
    PythonDocxLabelerMarkdown,
)

_CORPUS = Path("tests/fixtures/exam_conversion/docx_corpus")
_DOCX = _CORPUS / "svenska_2_grammatik_omprov_variant_1_med_facit.docx"


def _b(number: int) -> str:
    return f"body:{number:04d}"


@pytest.fixture(scope="module")
def chunks() -> tuple[DocxChunk, ...]:
    return PythonDocxExamChunker().chunk(content=_DOCX.read_bytes())


def _question(
    question_id: str,
    anchors: list[str],
    subparts: list[str] | None = None,
    keys: list[str] | None = None,
) -> dict[str, JsonValue]:
    return {
        "id": question_id,
        "anchors": list(anchors),
        "subpart_anchors": list(subparts or []),
        "answer_key_anchors": list(keys or []),
    }


def _context(
    anchor: str,
    scope: str = "section_instruction",
    owner: str = "exam",
    governs: list[str] | None = None,
) -> dict[str, JsonValue]:
    return {"anchor": anchor, "scope": scope, "owner": owner, "governs": list(governs or [])}


def _raw(
    questions: list[dict[str, JsonValue]],
    contexts: list[dict[str, JsonValue]] | None = None,
    title: list[str] | None = None,
    header: list[dict[str, JsonValue]] | None = None,
) -> dict[str, JsonValue]:
    return {
        "title_anchors": list(title or []),
        "questions": list(questions),
        "shared_contexts": list(contexts or []),
        "header_anchors": list(header or []),
    }


Q1 = [_b(8), _b(9), _b(10)]
Q2 = [_b(16), _b(17), _b(18)]


def test_unknown_anchor_is_dropped_and_recorded(chunks: tuple[DocxChunk, ...]) -> None:
    manifest = manifest_from_output(
        _raw([_question("q1", [*Q1, "body:9999"], keys=["nope"])], title=["x"]), chunks
    )
    assert manifest.questions[0].anchors == tuple(Q1)
    assert manifest.questions[0].key_anchors == ()
    assert manifest.invalid_anchors == ("body:9999", "nope", "x")


def test_anchor_claimed_by_two_questions_goes_to_first(chunks: tuple[DocxChunk, ...]) -> None:
    manifest = manifest_from_output(
        _raw([_question("q1", Q1), _question("q2", [_b(10), *Q2])]), chunks
    )
    assert manifest.duplicate_anchors == (_b(10),)
    assert manifest.question("q1").anchors == tuple(Q1)
    assert manifest.question("q2").anchors == tuple(Q2)


def test_anchor_in_question_and_context_stays_in_question(chunks: tuple[DocxChunk, ...]) -> None:
    manifest = manifest_from_output(
        _raw([_question("q1", Q1)], contexts=[_context(_b(9), governs=["q1"])]), chunks
    )
    assert manifest.contexts == ()
    assert manifest.duplicate_anchors == (_b(9),)


def test_duplicate_question_id_drops_later_question_to_unplaced(
    chunks: tuple[DocxChunk, ...],
) -> None:
    manifest = manifest_from_output(_raw([_question("q1", Q1), _question("q1", Q2)]), chunks)
    assert [q.question_id for q in manifest.questions] == ["q1"]
    assert manifest.duplicate_anchors == ()
    assert set(Q2) <= set(manifest.unplaced_anchors)


def test_question_with_only_invalid_anchors_is_dropped_and_keys_unplaced(
    chunks: tuple[DocxChunk, ...],
) -> None:
    manifest = manifest_from_output(
        _raw([_question("q1", Q1), _question("q2", ["ghost"], keys=[_b(22)])]), chunks
    )
    assert [q.question_id for q in manifest.questions] == ["q1"]
    assert manifest.invalid_anchors == ("ghost",)
    assert _b(22) in manifest.unplaced_anchors


def test_out_of_order_questions_and_anchors_are_sorted_by_position(
    chunks: tuple[DocxChunk, ...],
) -> None:
    manifest = manifest_from_output(
        _raw(
            [
                _question("q2", [_b(18), _b(16), _b(17)], subparts=[_b(18), _b(17), _b(9)]),
                _question("q1", [_b(10), _b(8)], keys=[_b(13), _b(11)]),
            ]
        ),
        chunks,
    )
    assert [q.question_id for q in manifest.questions] == ["q1", "q2"]
    assert manifest.questions[0].anchors == (_b(8), _b(10))
    assert manifest.questions[0].key_anchors == (_b(11), _b(13))
    assert manifest.questions[1].anchors == (_b(9), *Q2)
    assert manifest.questions[1].subpart_anchors == (_b(9), _b(17), _b(18))


def test_a_subpart_listed_only_as_a_subpart_is_owned_unless_placed_elsewhere(
    chunks: tuple[DocxChunk, ...],
) -> None:
    manifest = manifest_from_output(
        _raw(
            [_question("q1", [_b(8)], subparts=[_b(9), _b(10)]), _question("q2", Q2)],
            header=[{"anchor": _b(10), "kind": "part_total", "governs": ["q1"]}],
        ),
        chunks,
    )
    assert manifest.questions[0].anchors == (_b(8), _b(9))
    assert manifest.questions[0].subpart_anchors == (_b(9),)
    assert [(h.anchor, h.kind, h.governs) for h in manifest.header] == [
        (_b(10), "part_total", ("q1",))
    ]
    assert manifest.duplicate_anchors == ()
    assert _b(9) not in manifest.unplaced_anchors


def test_owner_and_governs_naming_missing_question_are_normalised(
    chunks: tuple[DocxChunk, ...],
) -> None:
    manifest = manifest_from_output(
        _raw(
            [_question("q1", Q1), _question("q2", Q2)],
            contexts=[_context(_b(6), owner="q9", governs=["q2", "q9", "q1"])],
        ),
        chunks,
    )
    context = manifest.contexts[0]
    assert (context.owner, context.governs) == ("exam", ("q1", "q2"))


def test_invalid_scope_is_manifest_shape(chunks: tuple[DocxChunk, ...]) -> None:
    with pytest.raises(ManifestInvalid) as error:
        manifest_from_output(
            _raw([_question("q1", Q1)], contexts=[_context(_b(6), scope="bogus")]), chunks
        )
    assert error.value.code == "manifest_shape"


def test_exam_total_is_no_header_kind(chunks: tuple[DocxChunk, ...]) -> None:
    raw = _raw(
        [_question("q1", Q1)],
        header=[{"anchor": _b(6), "kind": "exam_total", "governs": []}],
    )
    with pytest.raises(ManifestInvalid) as error:
        manifest_from_output(raw, chunks)
    assert error.value.code == "manifest_shape"


def test_zero_questions_is_manifest_empty(chunks: tuple[DocxChunk, ...]) -> None:
    with pytest.raises(ManifestInvalid) as error:
        manifest_from_output(_raw([]), chunks)
    assert error.value.code == "manifest_empty"


def test_missing_key_is_manifest_shape(chunks: tuple[DocxChunk, ...]) -> None:
    raw = _raw([_question("q1", Q1)])
    del raw["header_anchors"]
    with pytest.raises(ManifestInvalid) as error:
        manifest_from_output(raw, chunks)
    assert error.value.code == "manifest_shape"
    bad = _raw([_question("q1", Q1)])
    keyless: dict[str, JsonValue] = {"id": "q1", "anchors": list(Q1), "subpart_anchors": []}
    bad["questions"] = [keyless]
    with pytest.raises(ManifestInvalid) as error:
        manifest_from_output(bad, chunks)
    assert error.value.code == "manifest_shape"


def test_unplaced_anchors_are_all_unclaimed_chunks_in_order(
    chunks: tuple[DocxChunk, ...],
) -> None:
    manifest = manifest_from_output(
        _raw(
            [_question("q1", Q1)],
            title=[_b(2)],
            header=[{"anchor": _b(4), "kind": "course", "governs": []}],
        ),
        chunks,
    )
    everything = [chunk.anchor for chunk in chunks]
    claimed = {*Q1, _b(2), _b(4)}
    assert manifest.unplaced_anchors == tuple(a for a in everything if a not in claimed)


def test_question_source_has_section_heading_and_instruction_but_no_metadata() -> None:
    labeler_chunks = PythonDocxLabelerMarkdown().source(content=_DOCX.read_bytes()).chunks
    marked = {chunk.anchor: chunk.marked_text for chunk in labeler_chunks}
    own = [_b(n) for n in (10, 11, 12, 13)]
    manifest = manifest_from_output(
        _raw(
            [_question("q1", own), _question("q2", Q2)],
            contexts=[
                _context(_b(9), governs=["q1"]),
                _context(_b(4), scope="exam_metadata", governs=["q1"]),
            ],
            title=[_b(2)],
            header=[{"anchor": _b(6), "kind": "course", "governs": []}],
        ),
        labeler_chunks,
    )
    source = question_source(manifest, labeler_chunks, "q1")
    assert source.split("\n") == [marked[_b(n)] for n in (8, 9, 10, 11, 12, 13)]
    assert marked[_b(4)] not in source


def test_an_own_chunk_the_question_also_lists_as_its_key_keeps_both_marks(
    chunks: tuple[DocxChunk, ...],
) -> None:
    # Live Diagnostic 2026-10-16: the grouping listed each facit line among the question's own
    # chunks and as its key; admission decides by whether the converted item holds it.
    manifest = manifest_from_output(
        _raw([_question("q1", Q1, keys=[_b(10), _b(11)]), _question("q2", Q2, keys=[_b(10)])]),
        chunks,
    )
    assert manifest.questions[0].anchors == tuple(Q1)
    assert manifest.questions[0].key_anchors == (_b(10), _b(11))
    assert manifest.questions[1].key_anchors == ()
    assert manifest.duplicate_anchors == (_b(10),)
