"""Header placement must not leak source metadata or silently discard exam text."""

from __future__ import annotations

from collections import Counter

import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import (
    pack_batches,
    question_families,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ManifestInvalid,
    manifest_from_output,
    question_source_anchors,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)


def _chunk(anchor: str, text: str, *, heading: bool = False) -> DocxChunk:
    return DocxChunk(
        anchor=anchor, kind="heading" if heading else "paragraph", text=text, marked_text=text
    )


def _question(question_id: str, *anchors: str) -> dict[str, JsonValue]:
    return {
        "id": question_id,
        "anchors": list(anchors),
        "subpart_anchors": [],
        "answer_key_anchors": [],
    }


def _header(anchor: str, kind: str, *governs: str) -> dict[str, JsonValue]:
    return {"anchor": anchor, "kind": kind, "governs": list(governs)}


def _grouping(
    headers: list[dict[str, JsonValue]],
    *,
    questions: list[dict[str, JsonValue]] | None = None,
) -> dict[str, JsonValue]:
    return {
        "title_anchors": [],
        "header_anchors": list(headers),
        "questions": list(questions) if questions is not None else [_question("q1", "question")],
        "shared_contexts": [],
    }


@pytest.mark.parametrize("kind", ["course", "exam_total", "part_total"])
def test_header_never_enters_family_or_batch_even_when_it_heads_a_section(kind: str) -> None:
    chunks = (
        _chunk("instruction", "Besvara båda frågorna."),
        _chunk("q1", "1. Ange ett verb."),
        _chunk("header", "Poäng: 15 poäng", heading=True),
        _chunk("q2", "2. Ange ett substantiv."),
    )
    raw = _grouping(
        [_header("header", kind, "q1", "q2")],
        questions=[_question("q1", "q1"), _question("q2", "q2")],
    )
    raw["shared_contexts"] = [
        {
            "anchor": "instruction",
            "scope": "section_instruction",
            "owner": "exam",
            "governs": ["q1", "q2"],
        }
    ]
    manifest = manifest_from_output(raw, chunks)
    families = question_families(manifest, chunks)
    assert "header" not in manifest.unplaced_anchors
    for family in families:
        assert "header" not in family.claims | family.reads
        assert "header" not in question_source_anchors(manifest, chunks, family.question_id)
    batches = pack_batches(
        families,
        {"q1": NativeExamItemKind.FREE_TEXT, "q2": NativeExamItemKind.SINGLE_CHOICE},
        families_per_batch=1,
        prefix="test",
    )
    assert len(batches) == 2
    assert all("header" not in batch.claims | batch.reads for batch in batches)
    assert "instruction" in families[1].reads
    assert "q2" in families[0].reads


def test_unknown_header_kind_is_a_manifest_shape_error() -> None:
    chunks = (_chunk("header", "Namn:"), _chunk("question", "1. Svara."))
    with pytest.raises(ManifestInvalid) as error:
        manifest_from_output(_grouping([_header("header", "student_name")]), chunks)
    assert error.value.code == "manifest_shape"


def test_question_first_claim_wins_over_a_conflicting_header_classification() -> None:
    chunks = (_chunk("heading", "2. Tempus (3 p)", heading=True), _chunk("q2", "Svara."))
    manifest = manifest_from_output(
        _grouping(
            [_header("heading", "part_total", "q1", "q2")],
            questions=[_question("q1", "heading"), _question("q2", "q2")],
        ),
        chunks,
    )
    assert manifest.header == ()
    assert manifest.duplicate_anchors == ("heading",)
    assert manifest.question("q1").anchors == ("heading",)
    families = question_families(manifest, chunks)
    assert [family.question_id for family in families if "heading" in family.claims] == ["q1"]
    assert "heading" in question_source_anchors(manifest, chunks, "q1")


def test_part_total_governs_only_surviving_questions_in_source_order() -> None:
    chunks = (
        _chunk("header", "Poäng: 15 poäng"),
        _chunk("q1", "1. Svara."),
        _chunk("q2", "2. Svara."),
    )
    manifest = manifest_from_output(
        _grouping(
            [_header("header", "part_total", "q2", "missing", "q1", "q2")],
            questions=[_question("q2", "q2"), _question("q1", "q1")],
        ),
        chunks,
    )
    assert manifest.header[0].governs == ("q1", "q2")


@pytest.mark.parametrize("kind", ["course", "exam_total"])
def test_exam_level_header_cannot_become_part_scoped(kind: str) -> None:
    chunks = (_chunk("header", "Svenska 2"), _chunk("question", "1. Svara."))
    manifest = manifest_from_output(_grouping([_header("header", kind, "q1")]), chunks)
    assert manifest.header[0].governs == ()


def test_unclassified_chunks_still_have_exactly_one_family_owner() -> None:
    chunks = (
        _chunk("title", "Prov", heading=True),
        _chunk("header", "Svenska 2", heading=True),
        _chunk("orphan_before", "En viktig upplysning."),
        _chunk("q1", "1. Svara."),
        _chunk("orphan_points", "(3 p)"),
        _chunk("context", "Läs texten inför båda svaren."),
        _chunk("q2", "2. Svara."),
        _chunk("key", "Facit: exempel"),
        _chunk("orphan_after", "Avslutande upplysning."),
    )
    q2 = _question("q2", "q2")
    q2["answer_key_anchors"] = ["key"]
    raw = _grouping([_header("header", "course")], questions=[_question("q1", "q1"), q2])
    raw["title_anchors"] = ["title"]
    raw["shared_contexts"] = [
        {
            "anchor": "context",
            "scope": "shared_passage",
            "owner": "exam",
            "governs": ["q1", "q2"],
        }
    ]
    manifest = manifest_from_output(raw, chunks)
    assert set(manifest.unplaced_anchors) == {"orphan_before", "orphan_points", "orphan_after"}
    families = question_families(manifest, chunks)
    claims = Counter(anchor for family in families for anchor in family.claims)
    assert claims == Counter({chunk.anchor: 1 for chunk in chunks if chunk.anchor != "header"})
    assert "orphan_before" in families[0].claims
    assert "orphan_points" in families[0].claims
    assert "orphan_after" in families[1].claims
    assert "key" in families[1].claims
    assert "key" not in families[0].reads
