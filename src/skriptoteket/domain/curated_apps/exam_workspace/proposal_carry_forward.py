"""Filter pending answer-key proposals for the next saved document revision."""

from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    WorkspaceAnswerKeyProposalRecord,
    WorkspaceAnswerKeyProposalsPayload,
    answer_key_item_view,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    item_has_trusted_key,
)


def carry_pending_proposal_records(
    *,
    previous_document: NativeExamDocument,
    document: NativeExamDocument,
    payload: WorkspaceAnswerKeyProposalsPayload,
    rejected_item_ids: frozenset[str],
) -> tuple[WorkspaceAnswerKeyProposalRecord, ...]:
    """Keep original records for unchanged, undecided items in the next revision.

    Records are copied as produced by enrichment; the saved document and
    provider metadata remain untouched. Persistence belongs to the caller.
    """
    if (
        payload.lineage_id != previous_document.document_id
        or payload.document_revision != previous_document.revision
        or document.document_id != previous_document.document_id
        or document.revision != previous_document.revision + 1
    ):
        return ()

    previous_items = {item.item_id: item for item in previous_document.items}
    items = {item.item_id: item for item in document.items}
    carried: list[WorkspaceAnswerKeyProposalRecord] = []
    for record in payload.items:
        previous_item = previous_items.get(record.item_id)
        item = items.get(record.item_id)
        if (
            previous_item is None
            or item is None
            or record.item_id in rejected_item_ids
            or item_has_trusted_key(item)
            or previous_item.kind != item.kind
        ):
            continue
        try:
            previous_view = answer_key_item_view(
                previous_item, previous_document.parent_of(record.item_id)
            )
            if previous_view != answer_key_item_view(item, document.parent_of(record.item_id)):
                continue
        except ValueError:
            continue
        carried.append(record)
    return tuple(carried)
