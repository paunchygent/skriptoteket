"""Question families and type batches for parallel DOCX conversion (TASK-SKRIPT-39-05-04).

A family is one grouped question with its subparts and answer key; it never splits (D2).
Every source chunk has exactly one owning family: its own chunks, the shared instructions
and passages it owns, a points line the grouping left unplaced (the question before it),
and the title, headings and other unplaced chunks (the question after them). A shared
instruction reaches every other family it governs as read-only context. A family that owns
chunks beyond its own question and answer key, such as a section heading or a points line
after the section's last question, also reads the other questions of each section it sits
in, so that it sees which of those chunks serve the whole section. A
batch holds families of one item kind; only single choice and multiple response share a
batch (D3).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import ExamManifest
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import points_line
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)

_CHOICE = frozenset({NativeExamItemKind.SINGLE_CHOICE, NativeExamItemKind.MULTIPLE_RESPONSE})
_EXAM_OWNER = "exam"


@dataclass(frozen=True)
class QuestionFamily:
    """One question in source order with every anchor it owns and reads."""

    question_id: str
    position: int
    question_anchors: tuple[str, ...]
    claims: frozenset[str]
    reads: frozenset[str]


@dataclass(frozen=True)
class ConversionBatch:
    """Families of one kind group converted by one request."""

    batch_id: str
    kinds: frozenset[NativeExamItemKind]
    question_ids: tuple[str, ...]
    claims: frozenset[str]
    reads: frozenset[str]


def kind_group(kind: NativeExamItemKind) -> frozenset[NativeExamItemKind]:
    """The item kinds a batch holding ``kind`` admits."""
    return _CHOICE if kind in _CHOICE else frozenset({kind})


def _nearest_question(
    position: int, starts: list[tuple[int, str]], *, trailing: bool = False
) -> str:
    """The first question starting after a chunk, else the last question before it.

    A trailing chunk, such as a points line, belongs to the last question before it.
    """
    preceding = [qid for start, qid in starts if start <= position]
    if trailing and preceding:
        return preceding[-1]
    following = next((qid for start, qid in starts if start > position), None)
    if following is not None:
        return following
    return preceding[-1]


def question_families(
    manifest: ExamManifest, chunks: tuple[DocxChunk, ...]
) -> tuple[QuestionFamily, ...]:
    """Assign every chunk to exactly one family; shared context is read by its other governees.

    A family owning section-level chunks also reads the own chunks of the other questions
    its multi-question shared contexts govern; their answer keys stay with their owners.
    """
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    starts = [(positions[q.anchors[0]], q.question_id) for q in manifest.questions]
    claims: dict[str, set[str]] = {
        q.question_id: {*q.anchors, *q.key_anchors} for q in manifest.questions
    }
    reads: dict[str, set[str]] = {q.question_id: set() for q in manifest.questions}
    for context in manifest.contexts:
        if context.owner != _EXAM_OWNER:
            owner = context.owner
        elif context.governs:
            owner = min(
                context.governs, key=lambda qid: positions[manifest.question(qid).anchors[0]]
            )
        else:
            owner = _nearest_question(positions[context.anchor], starts)
        claims[owner].add(context.anchor)
        for governed in context.governs:
            if governed != owner:
                reads[governed].add(context.anchor)
    placed = {anchor for owned in claims.values() for anchor in owned}
    for chunk in chunks:
        if chunk.anchor not in placed:
            owner = _nearest_question(
                positions[chunk.anchor], starts, trailing=points_line(chunk.text)
            )
            claims[owner].add(chunk.anchor)
    for q in manifest.questions:
        if claims[q.question_id] <= {*q.anchors, *q.key_anchors}:
            continue
        for context in manifest.contexts:
            if q.question_id in context.governs and len(context.governs) >= 2:
                for governed in context.governs:
                    if governed != q.question_id:
                        reads[q.question_id].update(manifest.question(governed).anchors)
    return tuple(
        QuestionFamily(
            question_id=q.question_id,
            position=index,
            question_anchors=q.anchors,
            claims=frozenset(claims[q.question_id]),
            reads=frozenset(reads[q.question_id] - claims[q.question_id]),
        )
        for index, q in enumerate(manifest.questions)
    )


def pack_batches(
    families: tuple[QuestionFamily, ...],
    kinds: Mapping[str, NativeExamItemKind],
    *,
    families_per_batch: int,
    prefix: str,
) -> tuple[ConversionBatch, ...]:
    """Pack families of one kind group, in source order, at most ``families_per_batch`` each."""
    if families_per_batch < 1:
        raise ValueError("families_per_batch must be at least 1")
    groups: dict[frozenset[NativeExamItemKind], list[QuestionFamily]] = {}
    for family in sorted(families, key=lambda f: f.position):
        groups.setdefault(kind_group(kinds[family.question_id]), []).append(family)
    batches: list[ConversionBatch] = []
    for group, members in groups.items():
        for start in range(0, len(members), families_per_batch):
            chunk = members[start : start + families_per_batch]
            claims = frozenset().union(*(f.claims for f in chunk))
            reads = frozenset().union(*(f.reads for f in chunk)) - claims
            batches.append(
                ConversionBatch(
                    batch_id=f"{prefix}{len(batches) + 1:02d}",
                    kinds=group,
                    question_ids=tuple(f.question_id for f in chunk),
                    claims=claims,
                    reads=reads,
                )
            )
    return tuple(batches)
