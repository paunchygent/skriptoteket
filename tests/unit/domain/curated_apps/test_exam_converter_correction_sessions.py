"""Tests for the Exam Converter correction-session aggregate.

Purpose:
  Prove ADR-0087 current-set semantics before API, replay, or frontend layers
  consume durable correction-session truth.

Relationships:
  - Covers `domain.curated_apps.exam_converter_correction_sessions`.
  - Guards PR-0333 backend aggregate behavior for ST-21-04.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_converter_correction_sessions import (
    ExamConverterCorrectionIntentKind,
    ExamConverterCorrectionSession,
    ExamConverterCorrectionSourceBinding,
    ExamConverterCorrectionTarget,
    SourceBoundCorrectionIntent,
    correction_kind_from_value,
)
from skriptoteket.domain.errors import DomainError, ErrorCode


def _binding(
    source_state_sha256: str = "sha256:source-state",
) -> ExamConverterCorrectionSourceBinding:
    return ExamConverterCorrectionSourceBinding(
        source_authoring_schema_version="exam_authoring_ir_v1",
        source_bundle_id="bundle-001",
        source_file_sha256="sha256:source-file",
        source_state_sha256=source_state_sha256,
        source_state_signature="signed-source-state",
    )


def _session(
    *, binding: ExamConverterCorrectionSourceBinding | None = None
) -> ExamConverterCorrectionSession:
    return ExamConverterCorrectionSession(
        id=uuid4(),
        owner_user_id=uuid4(),
        conversion_hub_job_id=uuid4(),
        source_binding=binding or _binding(),
        session_version=0,
    )


def _intent(
    *,
    intent_id: UUID | None = None,
    item_id: str = "item-001",
    sequence: int = 1,
    kind: ExamConverterCorrectionIntentKind = ExamConverterCorrectionIntentKind.POINT_CORRECTION,
    binding: ExamConverterCorrectionSourceBinding | None = None,
) -> SourceBoundCorrectionIntent:
    source_binding = binding or _binding()
    target = ExamConverterCorrectionTarget()
    payload: dict[str, object] = {"kind": kind.value}
    if kind is ExamConverterCorrectionIntentKind.MANUAL_CHOICE_ANSWER_KEY:
        target = ExamConverterCorrectionTarget(interaction_id=f"choice-{item_id}")
        payload = {
            "kind": kind.value,
            "interaction_id": f"choice-{item_id}",
            "correct_choice_ids": ["choice-001"],
        }
    elif kind is ExamConverterCorrectionIntentKind.MANUAL_GAP_OPEN_CLOZE_ANSWER_KEY:
        target = ExamConverterCorrectionTarget(interaction_id=f"gap-{item_id}")
        payload = {
            "kind": kind.value,
            "interaction_id": f"gap-{item_id}",
            "gap_answers": [{"gap_id": "gap-001", "accepted_values": ["answer"]}],
        }
    elif kind is ExamConverterCorrectionIntentKind.ITEM_TEXT_PATCH:
        target = ExamConverterCorrectionTarget(text_field="prompt_lines")
        payload = {
            "kind": kind.value,
            "patches": [{"field": "prompt_lines", "value": "Updated prompt"}],
        }
    elif kind is ExamConverterCorrectionIntentKind.REVIEW_DECISION:
        target = ExamConverterCorrectionTarget(accepted_target_family="answer_key")
        payload = {
            "kind": kind.value,
            "accepted_targets": ["examnet_pdf", "qti_package"],
        }
    elif kind is ExamConverterCorrectionIntentKind.CANDIDATE_SUPPRESSION:
        target = ExamConverterCorrectionTarget(
            candidate_lineage_id="lineage-001",
            candidate_payload_digest="sha256:candidate",
        )
        payload = {"kind": kind.value, "candidate_lineage_id": "lineage-001"}
    elif kind is ExamConverterCorrectionIntentKind.POINT_CORRECTION:
        payload = {"kind": kind.value, "max_score": 2}

    return SourceBoundCorrectionIntent(
        intent_id=intent_id or uuid4(),
        entry_id=f"entry-{kind.value}-{item_id}",
        source_binding=source_binding,
        item_id=item_id,
        sequence=sequence,
        item_type="multiple_choice",
        source_item_fingerprint=f"sha256:{item_id}",
        kind=kind,
        target=target,
        payload=payload,
    )


def test_replace_supersedes_existing_target_and_increments_version() -> None:
    session = _session()
    first = _intent(intent_id=uuid4(), binding=session.source_binding)
    second = _intent(intent_id=uuid4(), binding=session.source_binding)

    saved = session.replace_intent(intent=first, expected_session_version=0)
    replaced = saved.replace_intent(intent=second, expected_session_version=1)

    assert replaced.session_version == 2
    assert replaced.active_replay_intents() == (second,)


def test_revert_removes_target_from_replay_set() -> None:
    session = _session()
    intent = _intent(binding=session.source_binding)
    saved = session.replace_intent(intent=intent, expected_session_version=0)

    reverted = saved.revert_target(target_key=intent.target_key, expected_session_version=1)

    assert reverted.session_version == 2
    assert reverted.active_replay_intents() == ()


def test_stale_session_version_raises_conflict() -> None:
    session = _session()
    saved = session.replace_intent(
        intent=_intent(binding=session.source_binding),
        expected_session_version=0,
    )

    with pytest.raises(DomainError) as exc:
        saved.replace_intent(
            intent=_intent(binding=saved.source_binding),
            expected_session_version=0,
        )

    assert exc.value.code is ErrorCode.CONFLICT
    assert exc.value.details["current_session_version"] == 1


def test_duplicate_targets_in_one_batch_are_rejected() -> None:
    session = _session()
    first = _intent(binding=session.source_binding)
    duplicate = first.model_copy(update={"intent_id": uuid4(), "entry_id": "entry-duplicate"})

    with pytest.raises(DomainError) as exc:
        session.replace_intents(
            intents=(first, duplicate),
            expected_session_version=0,
        )

    assert exc.value.code is ErrorCode.VALIDATION_ERROR
    assert "Duplicate active correction target" in exc.value.message


def test_answer_key_and_review_decision_can_coexist_without_superseding_facit() -> None:
    session = _session()
    choice = _intent(
        kind=ExamConverterCorrectionIntentKind.MANUAL_CHOICE_ANSWER_KEY,
        binding=session.source_binding,
    )
    review = _intent(
        kind=ExamConverterCorrectionIntentKind.REVIEW_DECISION,
        binding=session.source_binding,
    )

    saved = session.replace_intents(intents=(choice, review), expected_session_version=0)

    assert saved.active_replay_intents() == (review, choice)


def test_review_decision_does_not_supersede_prior_answer_key() -> None:
    session = _session()
    choice = _intent(
        kind=ExamConverterCorrectionIntentKind.MANUAL_CHOICE_ANSWER_KEY,
        binding=session.source_binding,
    )
    review = _intent(
        kind=ExamConverterCorrectionIntentKind.REVIEW_DECISION,
        binding=session.source_binding,
    )

    saved = session.replace_intent(intent=choice, expected_session_version=0)
    updated = saved.replace_intent(intent=review, expected_session_version=1)

    assert updated.active_replay_intents() == (review, choice)


def test_replay_order_is_deterministic() -> None:
    session = _session()
    point = _intent(
        kind=ExamConverterCorrectionIntentKind.POINT_CORRECTION,
        binding=session.source_binding,
    )
    suppression = _intent(
        kind=ExamConverterCorrectionIntentKind.CANDIDATE_SUPPRESSION,
        binding=session.source_binding,
    )
    text = _intent(
        kind=ExamConverterCorrectionIntentKind.ITEM_TEXT_PATCH,
        binding=session.source_binding,
    )
    later_choice = _intent(
        item_id="item-002",
        sequence=2,
        kind=ExamConverterCorrectionIntentKind.MANUAL_CHOICE_ANSWER_KEY,
        binding=session.source_binding,
    )

    saved = session.replace_intents(
        intents=(later_choice, point, text, suppression),
        expected_session_version=0,
    )

    assert [intent.kind for intent in saved.active_replay_intents()] == [
        ExamConverterCorrectionIntentKind.CANDIDATE_SUPPRESSION,
        ExamConverterCorrectionIntentKind.ITEM_TEXT_PATCH,
        ExamConverterCorrectionIntentKind.POINT_CORRECTION,
        ExamConverterCorrectionIntentKind.MANUAL_CHOICE_ANSWER_KEY,
    ]


def test_intent_source_binding_must_match_session() -> None:
    session = _session()
    stale = _intent(binding=_binding("sha256:stale-source-state"))

    with pytest.raises(DomainError) as exc:
        session.replace_intent(intent=stale, expected_session_version=0)

    assert exc.value.code is ErrorCode.VALIDATION_ERROR
    assert "source binding does not match" in exc.value.message


def test_matching_kind_is_not_supported() -> None:
    with pytest.raises(DomainError) as exc:
        correction_kind_from_value("manual_matching_answer_key")

    assert exc.value.code is ErrorCode.VALIDATION_ERROR
