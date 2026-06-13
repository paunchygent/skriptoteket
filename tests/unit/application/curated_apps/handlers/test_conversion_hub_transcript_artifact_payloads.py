"""Tests for persisted transcript formatter artifact payloads.

Domain purpose:
  Prove replay completion persists validated producer bytes that later power
  Skriptoteket download and Mina filer save actions.

Relationships:
  - Covers the PR-0349 replay-complete/download contract.
  - Complements replay parser tests by exercising handlers through repositories.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from skriptoteket.application.curated_apps.conversion_hub_transcript_replay import (
    TRANSCRIPT_FORMATTER_REPLAY_ARTIFACT_BASE64_MAX_CHARS,
    TRANSCRIPT_FORMATTER_REPLAY_TOTAL_ARTIFACT_MAX_BYTES,
    ConversionHubTranscriptFormatterArtifactKey,
    ConversionHubTranscriptFormatterArtifactPayload,
    ConversionHubTranscriptFormatterReplayCompleteRequest,
)
from skriptoteket.application.curated_apps.handlers import (
    conversion_hub_transcript_artifact_actions as artifact_action_handlers,
)
from skriptoteket.application.curated_apps.handlers import (
    conversion_hub_transcript_formatter_replay as replay_handlers,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.scripting.vault import VaultFile, VaultUsage
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.curated_apps.handlers import (
    test_conversion_hub_transcript_artifact_actions as artifact_action_fixtures,
)
from tests.unit.application.curated_apps.handlers import (
    test_conversion_hub_transcript_formatter_replay as replay_fixtures,
)
from tests.unit.application.curated_apps.handlers.test_conversion_hub_transcript_saves import (
    FixedClock,
    FixedIdGenerator,
    InMemoryConversionHubJobRepository,
    InMemorySavedTranscriptRepository,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_replay_complete_payload_powers_download_and_mina_save() -> None:
    actor = make_user()
    transcript_id = uuid4()
    replay_job_id = uuid4()
    content = b"Anna: overlay-aware transcript\n"
    receipt_authority = replay_fixtures.SignedArtifactReceiptAuthority(
        now=datetime(2026, 6, 13, 12, 1, tzinfo=timezone.utc),
    )
    jobs = InMemoryConversionHubJobRepository()
    transcripts = InMemorySavedTranscriptRepository()
    transcripts.records[transcript_id] = replay_fixtures._saved_transcript(
        owner_user_id=actor.id,
        transcript_id=transcript_id,
    )
    artifacts = artifact_action_fixtures.InMemoryTranscriptFormatterArtifactRepository()
    complete_handler = replay_handlers.CompleteConversionHubTranscriptFormatterReplayHandler(
        jobs=jobs,
        transcripts=transcripts,
        artifacts=artifacts,
        receipt_verifier=receipt_authority.verifier,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 13, 12, 1, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(replay_job_id),
    )

    await complete_handler.handle(
        actor=actor,
        authenticated_huleedu_subject="teacher-subject-1",
        transcript_id=transcript_id,
        request=_complete_request(
            content=content,
            receipt_authority=receipt_authority,
        ),
    )
    download_handler = (
        artifact_action_handlers.DownloadConversionHubTranscriptFormatterArtifactHandler(
            jobs=jobs,
            transcripts=transcripts,
            artifacts=artifacts,
            uow=FakeUow(),
        )
    )
    downloaded = await download_handler.handle(
        actor=actor,
        transcript_id=transcript_id,
        artifact_key=ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT,
        correlation_id="corr-download-1",
    )

    assert downloaded.content == content
    assert downloaded.content_type == "text/plain"

    file_id = uuid4()
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    vault_files.create.side_effect = lambda *, file: file
    vault_usage = AsyncMock(spec=VaultUsageRepositoryProtocol)
    vault_usage.get_for_update.return_value = VaultUsage(
        user_id=actor.id,
        bytes_total=0,
        updated_at=datetime(2026, 6, 13, tzinfo=timezone.utc),
    )
    vault_storage = AsyncMock(spec=VaultStorageProtocol)
    save_handler = artifact_action_handlers.SaveConversionHubTranscriptFormatterArtifactHandler(
        jobs=jobs,
        transcripts=transcripts,
        artifacts=artifacts,
        vault_files=vault_files,
        vault_usage=vault_usage,
        vault_storage=vault_storage,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 13, 12, 2, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(file_id),
        settings=Settings.model_construct(
            VAULT_MAX_FILE_BYTES=1_000_000,
            VAULT_MAX_TOTAL_BYTES=2_000_000,
        ),
    )

    saved = await save_handler.handle(
        actor=actor,
        transcript_id=transcript_id,
        artifact_key=ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT,
        correlation_id="corr-save-1",
    )

    saved_file = vault_files.create.call_args.kwargs["file"]
    assert isinstance(saved_file, VaultFile)
    assert saved_file.source_artifact_id == (
        f"documents.conversion_hub:transcript-replay:{replay_job_id}:transcript_txt"
    )
    vault_storage.store_file.assert_awaited_once_with(
        user_id=actor.id,
        file_id=file_id,
        content=content,
    )
    assert saved.vault_artifact.file_id == file_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_replay_complete_rejects_browser_self_consistent_artifact_payload() -> None:
    actor = make_user()
    transcript_id = uuid4()
    jobs = InMemoryConversionHubJobRepository()
    transcripts = InMemorySavedTranscriptRepository()
    transcripts.records[transcript_id] = replay_fixtures._saved_transcript(
        owner_user_id=actor.id,
        transcript_id=transcript_id,
    )
    artifacts = artifact_action_fixtures.InMemoryTranscriptFormatterArtifactRepository()
    receipt_authority = replay_fixtures.SignedArtifactReceiptAuthority(
        now=datetime(2026, 6, 13, 12, 1, tzinfo=timezone.utc),
    )
    handler = replay_handlers.CompleteConversionHubTranscriptFormatterReplayHandler(
        jobs=jobs,
        transcripts=transcripts,
        artifacts=artifacts,
        receipt_verifier=receipt_authority.verifier,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 13, 12, 1, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(uuid4()),
    )
    forged_content = b"forged but self-consistent transcript\n"

    with pytest.raises(DomainError):
        await handler.handle(
            actor=actor,
            authenticated_huleedu_subject="teacher-subject-1",
            transcript_id=transcript_id,
            request=_complete_request(
                content=forged_content,
                receipt_authority=receipt_authority,
                receipt_signature="rs256=not-a-valid-signature",
            ),
        )

    assert artifacts.records == {}
    assert jobs.jobs == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_replay_complete_rejects_receipt_for_different_huleedu_subject() -> None:
    actor = make_user()
    transcript_id = uuid4()
    jobs = InMemoryConversionHubJobRepository()
    transcripts = InMemorySavedTranscriptRepository()
    transcripts.records[transcript_id] = replay_fixtures._saved_transcript(
        owner_user_id=actor.id,
        transcript_id=transcript_id,
    )
    artifacts = artifact_action_fixtures.InMemoryTranscriptFormatterArtifactRepository()
    receipt_authority = replay_fixtures.SignedArtifactReceiptAuthority(
        now=datetime(2026, 6, 13, 12, 1, tzinfo=timezone.utc),
    )
    handler = replay_handlers.CompleteConversionHubTranscriptFormatterReplayHandler(
        jobs=jobs,
        transcripts=transcripts,
        artifacts=artifacts,
        receipt_verifier=receipt_authority.verifier,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 13, 12, 1, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(uuid4()),
    )

    with pytest.raises(DomainError):
        await handler.handle(
            actor=actor,
            authenticated_huleedu_subject="teacher-subject-2",
            transcript_id=transcript_id,
            request=_complete_request(
                content=b"Anna: overlay-aware transcript\n",
                receipt_authority=receipt_authority,
            ),
        )

    assert artifacts.records == {}
    assert jobs.jobs == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_replay_complete_rejects_bad_base64_payload() -> None:
    receipt_authority = replay_fixtures.SignedArtifactReceiptAuthority(
        now=datetime(2026, 6, 13, 12, 1, tzinfo=timezone.utc),
    )
    payload = _artifact_payload(receipt_authority=receipt_authority)
    payload["content_base64"] = "%%%not-base64%%%"

    await _assert_payload_rejected(receipt_authority=receipt_authority, artifact_payloads=[payload])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_replay_complete_rejects_duplicate_and_missing_payload_keys() -> None:
    receipt_authority = replay_fixtures.SignedArtifactReceiptAuthority(
        now=datetime(2026, 6, 13, 12, 1, tzinfo=timezone.utc),
    )
    payload = _artifact_payload(receipt_authority=receipt_authority)

    await _assert_payload_rejected(
        receipt_authority=receipt_authority,
        artifact_payloads=[payload, payload],
    )
    await _assert_payload_rejected(
        receipt_authority=receipt_authority,
        artifact_payloads=[payload],
        requested_artifacts=["txt", "md"],
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_replay_complete_rejects_payload_content_type_size_and_checksum_mismatch() -> None:
    receipt_authority = replay_fixtures.SignedArtifactReceiptAuthority(
        now=datetime(2026, 6, 13, 12, 1, tzinfo=timezone.utc),
    )
    content = b"Anna: overlay-aware transcript\n"

    wrong_type = _artifact_payload(receipt_authority=receipt_authority, content=content)
    wrong_type["content_type"] = "application/json"
    await _assert_payload_rejected(
        receipt_authority=receipt_authority,
        artifact_payloads=[wrong_type],
    )

    wrong_size = _artifact_payload(receipt_authority=receipt_authority, content=content)
    wrong_size["content_base64"] = base64.b64encode(content + b"x").decode("ascii")
    await _assert_payload_rejected(
        receipt_authority=receipt_authority,
        artifact_payloads=[wrong_size],
    )

    wrong_checksum = _artifact_payload(receipt_authority=receipt_authority, content=content)
    wrong_checksum["content_base64"] = base64.b64encode(b"B" * len(content)).decode("ascii")
    await _assert_payload_rejected(
        receipt_authority=receipt_authority,
        artifact_payloads=[wrong_checksum],
    )


@pytest.mark.unit
def test_replay_payload_rejects_base64_above_per_artifact_budget_before_decode() -> None:
    with pytest.raises(ValidationError):
        ConversionHubTranscriptFormatterArtifactPayload(
            artifact_key="transcript_txt",
            content_type="text/plain",
            content_base64="A" * (TRANSCRIPT_FORMATTER_REPLAY_ARTIFACT_BASE64_MAX_CHARS + 1),
            receipt={
                "receipt_version": 1,
                "payload": "receipt-payload",
                "key_id": "gateway-identity-rs256-v1",
                "signature": "rs256=signature",
            },
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_replay_complete_rejects_total_payload_byte_budget_before_persistence() -> None:
    receipt_authority = replay_fixtures.SignedArtifactReceiptAuthority(
        now=datetime(2026, 6, 13, 12, 1, tzinfo=timezone.utc),
    )
    content = b"a" * ((TRANSCRIPT_FORMATTER_REPLAY_TOTAL_ARTIFACT_MAX_BYTES // 4) + 1)
    payloads = [
        receipt_authority.artifact_payload(
            artifact_key=artifact_key,
            filename=f"{artifact_key.value}.txt",
            content_type="text/plain",
            content=content,
        )
        for artifact_key in [
            ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT,
            ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_MD,
            ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_VTT,
            ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_SRT,
        ]
    ]

    await _assert_payload_rejected(
        receipt_authority=receipt_authority,
        artifact_payloads=payloads,
        requested_artifacts=["txt", "md", "vtt", "srt"],
    )


async def _assert_payload_rejected(
    *,
    receipt_authority: replay_fixtures.SignedArtifactReceiptAuthority,
    artifact_payloads: list[dict[str, object]],
    requested_artifacts: list[str] | None = None,
) -> None:
    actor = make_user()
    transcript_id = uuid4()
    jobs = InMemoryConversionHubJobRepository()
    transcripts = InMemorySavedTranscriptRepository()
    transcripts.records[transcript_id] = replay_fixtures._saved_transcript(
        owner_user_id=actor.id,
        transcript_id=transcript_id,
    )
    artifacts = artifact_action_fixtures.InMemoryTranscriptFormatterArtifactRepository()
    handler = replay_handlers.CompleteConversionHubTranscriptFormatterReplayHandler(
        jobs=jobs,
        transcripts=transcripts,
        artifacts=artifacts,
        receipt_verifier=receipt_authority.verifier,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 13, 12, 1, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(uuid4()),
    )

    with pytest.raises(DomainError):
        await handler.handle(
            actor=actor,
            authenticated_huleedu_subject="teacher-subject-1",
            transcript_id=transcript_id,
            request=_complete_request(
                content=b"Anna: overlay-aware transcript\n",
                receipt_authority=receipt_authority,
                artifact_payloads=artifact_payloads,
                requested_artifacts=requested_artifacts,
            ),
        )

    assert artifacts.records == {}
    assert jobs.jobs == {}


def _complete_request(
    *,
    content: bytes,
    receipt_authority: replay_fixtures.SignedArtifactReceiptAuthority,
    receipt_signature: str | None = None,
    artifact_payloads: list[dict[str, object]] | None = None,
    requested_artifacts: list[str] | None = None,
) -> ConversionHubTranscriptFormatterReplayCompleteRequest:
    payload = _artifact_payload(receipt_authority=receipt_authority, content=content)
    if artifact_payloads is None:
        artifact_payloads = [payload]
    if receipt_signature is not None:
        receipt = artifact_payloads[0]["receipt"]
        assert isinstance(receipt, dict)
        receipt["signature"] = receipt_signature
    return ConversionHubTranscriptFormatterReplayCompleteRequest(
        sir_convert_job_id="sir-replay-job-1",
        correlation_id="corr-replay-1",
        status="succeeded",
        requested_artifacts=requested_artifacts or ["txt"],
        result={
            "api_version": "v2",
            "job_id": "sir-replay-job-1",
            "status": "succeeded",
            "result": {
                "artifact": {
                    "filename": "transcript_replay_bundle_manifest.json",
                    "format": "transcript_bundle",
                    "content_type": "application/json",
                    "size_bytes": 32,
                    "sha256": "manifest-digest",
                },
                "conversion_metadata": {
                    "pipeline_used": "transcript_json_to_transcript_bundle_replay_v2",
                    "options_fingerprint": "sha256:replay-options",
                },
                "warnings": [],
            },
        },
        artifact_payloads=artifact_payloads,
    )


def _artifact_payload(
    *,
    receipt_authority: replay_fixtures.SignedArtifactReceiptAuthority,
    content: bytes = b"Anna: overlay-aware transcript\n",
) -> dict[str, object]:
    return receipt_authority.artifact_payload(
        artifact_key=ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT,
        filename="transcript_txt.txt",
        content_type="text/plain",
        content=content,
    )
