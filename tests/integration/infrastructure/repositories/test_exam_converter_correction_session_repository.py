"""Integration tests for Exam Converter correction-session persistence.

Purpose:
  Prove PR-0333 owner/job-scoped storage, optimistic versioning, and active
  target constraints for durable teacher correction sessions.

Relationships:
  - Exercises `PostgreSQLExamConverterCorrectionSessionRepository`.
  - Uses the Conversion Hub job ledger as the owner-scoped parent resource.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.curated_apps.exam_converter_correction_sessions import (
    ExamConverterCorrectionIntentKind,
    ExamConverterCorrectionSession,
    ExamConverterCorrectionSourceBinding,
    ExamConverterCorrectionTarget,
    SourceBoundCorrectionIntent,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.infrastructure.db.models.conversion_hub_job import ConversionHubJobModel
from skriptoteket.infrastructure.db.models.exam_converter_correction_session import (
    ExamConverterCorrectionIntentModel,
)
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.exam_converter_correction_sessions import (
    PostgreSQLExamConverterCorrectionSessionRepository,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")


def _binding() -> ExamConverterCorrectionSourceBinding:
    return ExamConverterCorrectionSourceBinding(
        source_authoring_schema_version="exam_authoring_ir_v1",
        source_bundle_id="bundle-001",
        source_file_sha256="sha256:source-file",
        source_state_sha256="sha256:source-state",
        source_state_signature="signed-source-state",
    )


def _new_session(
    *,
    owner_user_id: UUID,
    conversion_hub_job_id: UUID,
) -> ExamConverterCorrectionSession:
    return ExamConverterCorrectionSession(
        id=uuid4(),
        owner_user_id=owner_user_id,
        conversion_hub_job_id=conversion_hub_job_id,
        source_binding=_binding(),
        session_version=0,
    )


def _intent(
    *,
    binding: ExamConverterCorrectionSourceBinding,
    item_id: str = "item-001",
    sequence: int = 1,
    kind: ExamConverterCorrectionIntentKind = ExamConverterCorrectionIntentKind.POINT_CORRECTION,
) -> SourceBoundCorrectionIntent:
    target = ExamConverterCorrectionTarget()
    payload: dict[str, object] = {"kind": kind.value, "max_score": 2}
    if kind is ExamConverterCorrectionIntentKind.MANUAL_CHOICE_ANSWER_KEY:
        target = ExamConverterCorrectionTarget(interaction_id=f"choice-{item_id}")
        payload = {
            "kind": kind.value,
            "interaction_id": f"choice-{item_id}",
            "correct_choice_ids": ["choice-001"],
        }
    return SourceBoundCorrectionIntent(
        intent_id=uuid4(),
        entry_id=f"entry-{kind.value}-{item_id}",
        source_binding=binding,
        item_id=item_id,
        sequence=sequence,
        item_type="multiple_choice",
        source_item_fingerprint=f"sha256:{item_id}",
        kind=kind,
        target=target,
        payload=payload,
    )


async def _create_user(db_session: AsyncSession, *, email_prefix: str) -> UUID:
    now = datetime.now(timezone.utc)
    user_id = uuid4()
    db_session.add(
        UserModel(
            id=user_id,
            email=f"{email_prefix}-{user_id.hex[:8]}@example.com",
            password_hash="hash",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return user_id


async def _create_job(db_session: AsyncSession, *, owner_user_id: UUID) -> UUID:
    now = datetime.now(timezone.utc)
    job_id = uuid4()
    db_session.add(
        ConversionHubJobModel(
            id=job_id,
            owner_user_id=owner_user_id,
            input_filename="exam.dxe",
            source_format="pdf",
            output_format="pdf",
            status="succeeded",
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return job_id


@pytest.mark.integration
async def test_session_roundtrip_preserves_source_binding_and_active_intents(
    db_session: AsyncSession,
) -> None:
    owner_id = await _create_user(db_session, email_prefix="corr-session-owner")
    job_id = await _create_job(db_session, owner_user_id=owner_id)
    repo = PostgreSQLExamConverterCorrectionSessionRepository(db_session)
    session = _new_session(owner_user_id=owner_id, conversion_hub_job_id=job_id)
    intent = _intent(binding=session.source_binding)

    saved = await repo.save(
        session=session.replace_intent(intent=intent, expected_session_version=0),
        expected_session_version=0,
    )

    assert saved.session_version == 1
    assert saved.source_binding == session.source_binding
    assert saved.active_replay_intents()[0].payload == {"kind": "point_correction", "max_score": 2}


@pytest.mark.integration
async def test_owner_scoped_get_and_save_reject_cross_owner_access(
    db_session: AsyncSession,
) -> None:
    owner_id = await _create_user(db_session, email_prefix="corr-session-owner")
    other_owner_id = await _create_user(db_session, email_prefix="corr-session-other")
    job_id = await _create_job(db_session, owner_user_id=owner_id)
    repo = PostgreSQLExamConverterCorrectionSessionRepository(db_session)
    session = _new_session(owner_user_id=owner_id, conversion_hub_job_id=job_id)
    saved = await repo.save(
        session=session.replace_intent(
            intent=_intent(binding=session.source_binding),
            expected_session_version=0,
        ),
        expected_session_version=0,
    )

    assert (
        await repo.get_by_owner_and_job(owner_user_id=other_owner_id, conversion_hub_job_id=job_id)
    ) is None
    with pytest.raises(DomainError) as exc:
        await repo.save(
            session=saved.model_copy(update={"owner_user_id": other_owner_id}),
            expected_session_version=1,
        )
    assert exc.value.code is ErrorCode.NOT_FOUND


@pytest.mark.integration
async def test_repository_rejects_stale_expected_version(db_session: AsyncSession) -> None:
    owner_id = await _create_user(db_session, email_prefix="corr-session-conflict")
    job_id = await _create_job(db_session, owner_user_id=owner_id)
    repo = PostgreSQLExamConverterCorrectionSessionRepository(db_session)
    session = _new_session(owner_user_id=owner_id, conversion_hub_job_id=job_id)
    first = await repo.save(
        session=session.replace_intent(
            intent=_intent(binding=session.source_binding),
            expected_session_version=0,
        ),
        expected_session_version=0,
    )
    second = await repo.save(
        session=first.replace_intent(
            intent=_intent(binding=first.source_binding, item_id="item-002", sequence=2),
            expected_session_version=1,
        ),
        expected_session_version=1,
    )
    stale_update = first.replace_intent(
        intent=_intent(binding=first.source_binding, item_id="item-003", sequence=3),
        expected_session_version=1,
    )

    with pytest.raises(DomainError) as exc:
        await repo.save(session=stale_update, expected_session_version=1)

    assert second.session_version == 2
    assert exc.value.code is ErrorCode.CONFLICT
    assert exc.value.details["current_session_version"] == 2


@pytest.mark.integration
async def test_active_target_database_constraint_rejects_duplicates(
    db_session: AsyncSession,
) -> None:
    owner_id = await _create_user(db_session, email_prefix="corr-session-constraint")
    job_id = await _create_job(db_session, owner_user_id=owner_id)
    repo = PostgreSQLExamConverterCorrectionSessionRepository(db_session)
    session = _new_session(owner_user_id=owner_id, conversion_hub_job_id=job_id)
    intent = _intent(binding=session.source_binding)
    saved = await repo.save(
        session=session.replace_intent(intent=intent, expected_session_version=0),
        expected_session_version=0,
    )

    db_session.add(
        ExamConverterCorrectionIntentModel(
            id=uuid4(),
            session_id=saved.id,
            entry_id="duplicate-active-target",
            correction_kind=intent.kind.value,
            target_key=intent.target_key,
            item_id=intent.item_id,
            sequence=intent.sequence,
            item_type=intent.item_type,
            source_item_fingerprint=intent.source_item_fingerprint,
            source_binding=intent.source_binding.model_dump(mode="json"),
            target=intent.target.model_dump(mode="json", exclude_none=True),
            payload=intent.payload,
            is_active=True,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.integration
async def test_replace_and_revert_persist_current_set(db_session: AsyncSession) -> None:
    owner_id = await _create_user(db_session, email_prefix="corr-session-revert")
    job_id = await _create_job(db_session, owner_user_id=owner_id)
    repo = PostgreSQLExamConverterCorrectionSessionRepository(db_session)
    session = _new_session(owner_user_id=owner_id, conversion_hub_job_id=job_id)
    first = _intent(binding=session.source_binding)
    saved = await repo.save(
        session=session.replace_intent(intent=first, expected_session_version=0),
        expected_session_version=0,
    )
    replacement = _intent(binding=saved.source_binding)
    replaced = await repo.save(
        session=saved.replace_intent(intent=replacement, expected_session_version=1),
        expected_session_version=1,
    )
    reverted = await repo.save(
        session=replaced.revert_target(
            target_key=replacement.target_key,
            expected_session_version=2,
        ),
        expected_session_version=2,
    )

    assert [intent.intent_id for intent in replaced.active_replay_intents()] == [
        replacement.intent_id
    ]
    assert reverted.active_replay_intents() == ()
