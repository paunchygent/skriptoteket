"""One-family batches see the section run whose instruction they own (U4).

Real recorded input: the corpus chunks and the live grouping of the final Svenska 2 exam.
In that grouping one unplaced heading ("Fråga 1. Flervalsfrågor") stays with the first
family, one section instruction ("Skriv rätt bokstav.") governs questions 1-15 as read-only
context, and a section points line follows question 15.
"""

from __future__ import annotations

from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import (
    pack_batches,
    question_families,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import manifest_from_output
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    corpus_chunks,
    recording,
)

_EXAM = "svenska_2_kursavslutande_prov_med_facit"
_SECTION_INSTRUCTION = "body:0009"


def _one_family_batches() -> dict[str, tuple[frozenset[str], frozenset[str]]]:
    chunks = corpus_chunks(_EXAM)
    manifest = manifest_from_output(recording(_EXAM, "docx_grouping_1"), chunks)
    families = question_families(manifest, chunks)
    kinds = {f.question_id: NativeExamItemKind.FREE_TEXT for f in families}
    batches = pack_batches(families, kinds, families_per_batch=1, prefix="w1-")
    return {b.question_ids[0]: (b.claims, b.reads) for b in batches}


def _question_anchors(numbers: range) -> set[str]:
    return {f"body:{10 + 3 * (n - 1):04d}" for n in numbers} | {
        f"body:{11 + 3 * (n - 1):04d}" for n in numbers
    }


def test_the_family_owning_the_section_heading_reads_the_rest_of_the_section():
    claims, reads = _one_family_batches()["q1"]

    assert {"body:0008", "body:0009"} <= claims
    assert _question_anchors(range(2, 16)) <= reads


def test_the_family_owning_the_section_points_line_reads_the_rest_of_the_section():
    claims, reads = _one_family_batches()["q15"]

    assert "body:0055" in claims
    assert _question_anchors(range(1, 15)) <= reads


def test_other_questions_answer_keys_never_reach_a_batch_as_context():
    batches = _one_family_batches()
    keys = {f"body:{12 + 3 * (n - 1):04d}" for n in range(1, 16)}

    for qid in ("q1", "q15"):
        claims, reads = batches[qid]
        assert not reads & keys
        assert not reads & claims


def test_a_question_inside_the_run_reads_only_the_shared_instruction():
    _, reads = _one_family_batches()["q7"]

    # The current grouping marks only "Skriv rätt bokstav." as shared context; the unplaced
    # heading above it stays with q1 and is not read by q7.
    assert reads == {_SECTION_INSTRUCTION}
    assert "body:0008" not in reads


def test_a_question_whose_instruction_governs_it_alone_reads_nothing_more():
    _, reads = _one_family_batches()["q17"]

    assert reads == set()
