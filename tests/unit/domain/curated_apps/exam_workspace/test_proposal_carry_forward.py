"""Pending proposal carry-forward rules for TASK-SKRIPT-39-04-04."""

from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    AnswerKeyViewKind,
    WorkspaceAnswerKeyProposalRecord,
    WorkspaceAnswerKeyProposalsPayload,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKeyOrigin,
    NativeExamDocument,
    NativeExamItem,
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.proposal_carry_forward import (
    carry_pending_proposal_records,
)
from tests.unit.scripts.exam_conversion_corpus_support import replayed

pytestmark = pytest.mark.unit


@pytest.fixture
def document() -> NativeExamDocument:
    return NativeExamDocument.model_validate(
        {
            "document_id": uuid4(),
            "revision": 3,
            "title": "Grammar",
            "origin": {"kind": "created"},
            "items": [
                {
                    "item_id": "item_001",
                    "sequence": 1,
                    "kind": "single_choice",
                    "title": "Choose a noun",
                    "body": [{"segments": [{"kind": "text", "text": "Which is a noun?"}]}],
                    "points": 1,
                    "choices": [
                        {"choice_id": "choice_001", "text": "house"},
                        {"choice_id": "choice_002", "text": "run"},
                    ],
                    "answer_key": {"origin": "absent"},
                    "review": {"state": "review_required", "parse_origin": "teacher_created"},
                },
                {
                    "item_id": "item_002",
                    "sequence": 2,
                    "kind": "gap_fill",
                    "title": "Complete the sentence",
                    "body": [
                        {
                            "segments": [
                                {"kind": "text", "text": "She "},
                                {"kind": "gap", "gap_id": "gap_001"},
                                {"kind": "text", "text": " home."},
                            ]
                        }
                    ],
                    "points": 1,
                    "gaps": [{"gap_id": "gap_001"}],
                    "answer_key": {"origin": "absent"},
                    "review": {"state": "review_required", "parse_origin": "teacher_created"},
                },
            ],
        }
    )


@pytest.fixture
def payload(document: NativeExamDocument) -> WorkspaceAnswerKeyProposalsPayload:
    metadata = {
        "provider_profile_id": "provider-original",
        "model": "model-original",
        "prompt_template_version": "prompt-original",
    }
    return WorkspaceAnswerKeyProposalsPayload(
        lineage_id=document.document_id,
        document_revision=document.revision,
        items=(
            WorkspaceAnswerKeyProposalRecord(
                item_id="item_001",
                kind=AnswerKeyViewKind.CHOICE,
                correct_choice_ids=("choice_001",),
                **metadata,
            ),
            WorkspaceAnswerKeyProposalRecord(
                item_id="item_002",
                kind=AnswerKeyViewKind.GAP_FILL,
                gap_accepted_values={"gap_001": ("walks", "goes")},
                **metadata,
            ),
        ),
    )


def _save(document: NativeExamDocument, *items: NativeExamItem) -> NativeExamDocument:
    data = document.model_dump()
    data["revision"] += 1
    if items:
        data["items"] = [item.model_dump() for item in items]
    return NativeExamDocument.model_validate(data)


def _carry(
    previous: NativeExamDocument,
    saved: NativeExamDocument,
    payload: WorkspaceAnswerKeyProposalsPayload,
    rejected: frozenset[str] = frozenset(),
) -> tuple[WorkspaceAnswerKeyProposalRecord, ...]:
    return carry_pending_proposal_records(
        previous_document=previous,
        document=saved,
        payload=payload,
        rejected_item_ids=rejected,
    )


def test_retains_original_records_without_mutating_documents(
    document: NativeExamDocument, payload: WorkspaceAnswerKeyProposalsPayload
) -> None:
    saved = _save(document)
    before = (document.model_dump(), saved.model_dump(), payload.model_dump())

    carried = _carry(document, saved, payload)

    assert carried == payload.items
    assert (document.model_dump(), saved.model_dump(), payload.model_dump()) == before


def test_points_review_and_item_reordering_preserve_proposals(
    document: NativeExamDocument, payload: WorkspaceAnswerKeyProposalsPayload
) -> None:
    first, second = document.items
    edited = first.model_dump()
    edited["points"] = 7
    edited["sequence"] = 2
    edited["review"]["state"] = "review_complete"
    edited["review"]["reasons"] = ["teacher_review"]
    saved = _save(
        document,
        second.model_copy(update={"sequence": 1}),
        NativeExamItem.model_validate(edited),
    )

    assert _carry(document, saved, payload) == payload.items


def test_rejected_item_drops_only_its_proposal(
    document: NativeExamDocument, payload: WorkspaceAnswerKeyProposalsPayload
) -> None:
    assert _carry(document, _save(document), payload, frozenset({"item_001"})) == (
        payload.items[1],
    )


@pytest.mark.parametrize("origin", ["teacher_authored", "reviewed_advisory", "source_provided"])
def test_trusted_key_drops_proposal(
    document: NativeExamDocument, payload: WorkspaceAnswerKeyProposalsPayload, origin: str
) -> None:
    first = document.items[0].model_dump()
    first["answer_key"] = {"origin": origin, "correct_choice_ids": ["choice_002"]}
    saved = _save(document, NativeExamItem.model_validate(first), document.items[1])

    assert _carry(document, saved, payload) == (payload.items[1],)


def test_untrusted_machine_proposed_key_keeps_proposal(
    document: NativeExamDocument, payload: WorkspaceAnswerKeyProposalsPayload
) -> None:
    # "Redigera förslaget" places the proposal in the editor without a decision.
    first = document.items[0].model_dump()
    first["answer_key"] = {"origin": "machine_proposed", "correct_choice_ids": ["choice_001"]}
    saved = _save(document, NativeExamItem.model_validate(first), document.items[1])

    assert _carry(document, saved, payload) == payload.items


@pytest.mark.parametrize("change", ["question", "title", "kind", "choice_id", "choice_text"])
def test_answer_relevant_choice_changes_drop_proposal(
    document: NativeExamDocument, payload: WorkspaceAnswerKeyProposalsPayload, change: str
) -> None:
    first = document.items[0].model_dump()
    if change == "question":
        first["body"][0]["segments"][0]["text"] = "Which is a verb?"
    elif change == "title":
        first["title"] = "Choose a verb"
    elif change == "kind":
        first["kind"] = "multiple_response"
    elif change == "choice_id":
        first["choices"][1]["choice_id"] = "choice_003"
    else:
        first["choices"][1]["text"] = "jump"
    saved = _save(document, NativeExamItem.model_validate(first), document.items[1])

    assert _carry(document, saved, payload) == (payload.items[1],)


def test_gap_id_change_drops_proposal(
    document: NativeExamDocument, payload: WorkspaceAnswerKeyProposalsPayload
) -> None:
    gap = document.items[1].model_dump()
    gap["body"][0]["segments"][1]["gap_id"] = "gap_002"
    gap["gaps"][0]["gap_id"] = "gap_002"
    saved = _save(document, document.items[0], NativeExamItem.model_validate(gap))

    assert _carry(document, saved, payload) == (payload.items[0],)


def test_deleted_item_drops_proposal(
    document: NativeExamDocument, payload: WorkspaceAnswerKeyProposalsPayload
) -> None:
    assert _carry(document, _save(document, document.items[0]), payload) == (payload.items[0],)


@pytest.mark.parametrize(
    "mismatch",
    ["payload_lineage", "payload_revision", "document_id", "same_revision", "skipped_revision"],
)
def test_lineage_or_revision_mismatch_drops_all_proposals(
    document: NativeExamDocument, payload: WorkspaceAnswerKeyProposalsPayload, mismatch: str
) -> None:
    saved = _save(document)
    if mismatch == "payload_lineage":
        payload = payload.model_copy(update={"lineage_id": uuid4()})
    elif mismatch == "payload_revision":
        payload = payload.model_copy(update={"document_revision": document.revision - 1})
    elif mismatch == "document_id":
        saved = saved.model_copy(update={"document_id": uuid4()})
    elif mismatch == "same_revision":
        saved = document
    else:
        saved = saved.model_copy(update={"revision": document.revision + 2})

    assert _carry(document, saved, payload) == ()


def test_item_missing_from_previous_document_drops_proposal(
    document: NativeExamDocument, payload: WorkspaceAnswerKeyProposalsPayload
) -> None:
    previous = NativeExamDocument.model_validate(
        {**document.model_dump(), "items": [document.items[0].model_dump()]}
    )

    assert _carry(previous, _save(document), payload) == (payload.items[0],)


def test_unkeyed_kind_drops_proposal(
    document: NativeExamDocument, payload: WorkspaceAnswerKeyProposalsPayload
) -> None:
    first = document.items[0].model_dump()
    first["kind"] = "free_text"
    first["choices"] = []
    first["answer_key"] = {"origin": NativeAnswerKeyOrigin.NOT_APPLICABLE}
    previous = NativeExamDocument.model_validate(
        {**document.model_dump(), "items": [first, document.items[1].model_dump()]}
    )

    assert _carry(previous, _save(previous), payload) == (payload.items[1],)


@pytest.fixture
def corpus_proposals() -> tuple[NativeExamDocument, WorkspaceAnswerKeyProposalsPayload]:
    """Pending keys use the recorded corpus answers, with the saved keys cleared."""
    document, _ = replayed("sa24_solid_gold_3_unit_3_discuss_and_argue_med_facit")
    records = tuple(
        WorkspaceAnswerKeyProposalRecord(
            item_id=item.item_id,
            kind=AnswerKeyViewKind.GAP_FILL,
            gap_accepted_values={gap.gap_id: gap.accepted_values for gap in item.gaps},
            provider_profile_id="recorded-corpus",
            model="recorded-corpus",
            prompt_template_version="recorded-corpus",
        )
        for item in document.items
        if item.kind is NativeExamItemKind.GAP_FILL
    )
    assert records
    assert all(record.gap_accepted_values for record in records)
    data = document.model_dump()
    for item in data["items"]:
        if item["kind"] is NativeExamItemKind.GAP_FILL:
            item["answer_key"] = {"origin": "absent"}
            for gap in item["gaps"]:
                gap["accepted_values"] = []
    previous = NativeExamDocument.model_validate(data)
    return previous, WorkspaceAnswerKeyProposalsPayload(
        lineage_id=previous.document_id,
        document_revision=previous.revision,
        items=records,
    )


def test_unchanged_corpus_parent_context_preserves_pending_proposals(
    corpus_proposals: tuple[NativeExamDocument, WorkspaceAnswerKeyProposalsPayload],
) -> None:
    previous, pending = corpus_proposals
    saved = _save(previous)
    before = (previous.model_dump(), saved.model_dump(), pending.model_dump())

    assert _carry(previous, saved, pending) == pending.items
    assert (previous.model_dump(), saved.model_dump(), pending.model_dump()) == before


@pytest.mark.parametrize(
    "removed_text",
    ["Three of the words will not be used.", "herbal"],
    ids=["governing-directions", "candidate-bank"],
)
def test_changed_corpus_parent_instruction_drops_only_its_children_proposals(
    corpus_proposals: tuple[NativeExamDocument, WorkspaceAnswerKeyProposalsPayload],
    removed_text: str,
) -> None:
    previous, pending = corpus_proposals
    parent = previous.parent_of("item_046")
    assert parent is not None
    assert any(removed_text in line for line in parent.instruction)
    data = _save(previous).model_dump()
    for entry in data["parents"]:
        if entry["parent_id"] == parent.parent_id:
            entry["instruction"] = [line.replace(removed_text, "") for line in entry["instruction"]]
    saved = NativeExamDocument.model_validate(data)
    assert saved.items == previous.items
    assert saved.parent_of("item_046") != parent
    affected_ids = set(parent.item_ids)
    affected = tuple(record for record in pending.items if record.item_id in affected_ids)
    unaffected = tuple(record for record in pending.items if record.item_id not in affected_ids)
    assert affected and unaffected
    before = (previous.model_dump(), saved.model_dump(), pending.model_dump())

    assert _carry(previous, saved, pending) == unaffected
    assert (previous.model_dump(), saved.model_dump(), pending.model_dump()) == before
