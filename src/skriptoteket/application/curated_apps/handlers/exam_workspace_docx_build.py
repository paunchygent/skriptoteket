"""Convert one type batch through one Responses call (TASK-SKRIPT-39-05-04).

A batch sends its own chunks and its read-only context once. The strict schema is the only
gate: every schema-valid entry is admitted, and every chunk the response leaves out becomes
a review item. Families reported as type conflicts leave the batch for the pipeline to
resend once with the kind the source shows.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxBuildExchangeProtocol,
    DocxBuildRoundFailure,
    build_batch_request,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import (
    ConversionBatch,
    QuestionFamily,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItemKind,
)

INCOMPLETE_REASON = "AI-tjänstens svar blev ofullständigt. Kontrollera källtexten manuellt."


@dataclass
class BatchOutcome:
    """The batch's state plus the families it handed back as type conflicts."""

    state: DocxBuildState
    conflicts: dict[str, NativeExamItemKind] = field(default_factory=dict)
    released: dict[str, frozenset[str]] = field(default_factory=dict)


def _conflicted_family(anchors: tuple[str, ...], families: dict[str, QuestionFamily]) -> str | None:
    """The family whose own question chunks the conflict names, else whose claims it names."""
    for match in ("question_anchors", "claims"):
        for family in families.values():
            if set(getattr(family, match)).intersection(anchors):
                return family.question_id
    return None


def _release_conflicts(
    state: DocxBuildState, families: dict[str, QuestionFamily], outcome: BatchOutcome
) -> None:
    """Hand conflicted families back; chunks other admitted content holds stay in the batch."""
    for conflict in state.conflicts:
        qid = _conflicted_family(conflict.anchors, families)
        if qid is not None:
            outcome.conflicts.setdefault(qid, conflict.kind)
    state.conflicts.clear()
    if not outcome.conflicts:
        return
    own = frozenset(a for qid in outcome.conflicts for a in families[qid].question_anchors)
    state.accepted = [entry for entry in state.accepted if not own.intersection(entry[1])]
    # The resend keeps the question's answer-key chunks: a conflicted family's facit
    # anchors are released with it, never held back as this batch's key anchors.
    conflicted_claims = frozenset().union(*(families[qid].claims for qid in outcome.conflicts))
    held = {
        *(a for _, anchors in state.accepted for a in anchors),
        *(a for m in (state.title, *state.instructions) if m for a in m.source_anchors),
        *(a for a in state.key_anchors if a not in conflicted_claims),
    }
    for qid in outcome.conflicts:
        outcome.released[qid] = families[qid].claims - held
    released = frozenset().union(*outcome.released.values())
    state.key_anchors -= released
    state.release(released)


async def convert_batch(
    *,
    state: DocxBuildState,
    batch: ConversionBatch,
    families: dict[str, QuestionFamily],
    exchange: DocxBuildExchangeProtocol,
    profile: StructuredLLMProviderProfile,
) -> BatchOutcome:
    """Send the batch once and admit the schema-valid response."""
    outcome = BatchOutcome(state)
    try:
        request = build_batch_request(
            job_id=state.job_id,
            request_id=f"docx_{batch.batch_id}",
            pending=state.pending,
            context=tuple(c for c in state.chunks if c.anchor in batch.reads),
            kinds=batch.kinds,
            profile=profile,
        )
        reply = await exchange.exchange(request, profile)
    except DocxBuildRoundFailure as error:
        state.record("provider", error.code, detail=error.detail)
        state.fail_all_pending(str(error))
        return outcome
    if reply.reconciliation_failure is not None:
        state.record("provider", "token_reconciliation_failed", detail=reply.reconciliation_failure)
    response = reply.response
    state.record_usage(response.usage)
    if response.finish_reason not in {None, "completed"}:
        state.record("provider", "response_incomplete", detail=f"status={response.finish_reason}")
        state.fail_all_pending(INCOMPLETE_REASON)
        return outcome
    admit_batch(response.content, state)
    _release_conflicts(state, families, outcome)
    return outcome
