"""The type_conflict resend keeps the question's answer-key chunks (O2, 39-05-08).

Synthetic: a conflicted family's facit anchors are released with the family, so the
resent batch can claim them and the resent item can carry accepted values or a marking
guide. Facit anchors of other families stay held by the batch that admitted them.
"""

from uuid import uuid4

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build import (
    BatchOutcome,
    _release_conflicts,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
    TypeConflict,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import QuestionFamily
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)


def _chunk(anchor: str) -> DocxChunk:
    return DocxChunk(anchor=anchor, kind="paragraph", text=anchor, marked_text=anchor)


def test_conflicted_family_releases_its_answer_key_chunks_for_the_resend() -> None:
    chunks = tuple(_chunk(f"body:000{number}") for number in range(1, 6))
    state = DocxBuildState(
        origin_kind="docx_import",
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
    )
    # The first reply admitted both questions' facit chunks as answer keys, then
    # reported question 15 (body:0001 question text, body:0002 its facit) as a conflict.
    state.key_anchors = {"body:0002", "body:0004"}
    state.conflicts = [TypeConflict(("body:0001",), NativeExamItemKind.GAP_FILL)]
    families = {
        "q15": QuestionFamily(
            question_id="q15",
            position=0,
            question_anchors=("body:0001",),
            claims=frozenset({"body:0001", "body:0002"}),
            reads=frozenset(),
        ),
        "q16": QuestionFamily(
            question_id="q16",
            position=1,
            question_anchors=("body:0003",),
            claims=frozenset({"body:0003", "body:0004"}),
            reads=frozenset(),
        ),
    }
    outcome = BatchOutcome(state)

    _release_conflicts(state, families, outcome)

    assert outcome.conflicts == {"q15": NativeExamItemKind.GAP_FILL}
    assert outcome.released["q15"] == frozenset({"body:0001", "body:0002"})
    assert "body:0002" not in state.key_anchors
    assert "body:0004" in state.key_anchors
