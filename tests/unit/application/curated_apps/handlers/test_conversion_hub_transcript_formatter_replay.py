"""Tests for Conversion Hub transcript formatter replay handlers.

Domain purpose:
  Prove saved transcript JSON plus speaker overlays can prepare producer replay
  requests and persist validated formatter artifact refs.

Relationships:
  - Exercises `conversion_hub_transcript_formatter_replay` handlers.
  - Shares in-memory repository fixtures with transcript save tests.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from skriptoteket.application.curated_apps.conversion_hub_transcript_artifact_actions import (
    ConversionHubTranscriptFormatterArtifactRecord,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_replay import (
    ConversionHubTranscriptFormatterArtifactKey,
    ConversionHubTranscriptFormatterReplayPrepareRequest,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_saves import (
    ConversionHubSavedTranscript,
    ConversionHubTranscriptSpeakerOverlay,
)
from skriptoteket.application.curated_apps.handlers import (
    conversion_hub_transcript_formatter_replay as transcript_replay_handlers,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.internal_identity_context import (
    INTERNAL_IDENTITY_SIGNATURE_PREFIX,
)
from skriptoteket.infrastructure.security.huleedu_artifact_receipts import (
    HuleEduArtifactReceiptVerifier,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.curated_apps.handlers.test_conversion_hub_transcript_saves import (
    FixedIdGenerator,
    InMemorySavedTranscriptRepository,
    InMemoryTranscriptSpeakerOverlayRepository,
)


def _now() -> datetime:
    return datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)


_TXT_CONTENT = b"Anna: transcript text\n"
_MD_CONTENT = b"## Transcript\n\nAnna: transcript text\n"
_RECEIPT_KEY_ID = "gateway-identity-rs256-v1"


class InMemoryTranscriptFormatterArtifactRepository:
    def __init__(self) -> None:
        self.records: dict[
            tuple[UUID, UUID, ConversionHubTranscriptFormatterArtifactKey],
            (ConversionHubTranscriptFormatterArtifactRecord),
        ] = {}

    async def replace_for_replay(
        self,
        *,
        records: list[ConversionHubTranscriptFormatterArtifactRecord],
    ) -> list[ConversionHubTranscriptFormatterArtifactRecord]:
        if not records:
            return []
        owner_user_id = records[0].owner_user_id
        transcript_id = records[0].transcript_id
        await self.delete_for_transcript(
            owner_user_id=owner_user_id,
            transcript_id=transcript_id,
        )
        for record in records:
            self.records[(record.owner_user_id, record.transcript_id, record.artifact_key)] = record
        return records

    async def get_by_owner_transcript_and_key(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
        artifact_key: ConversionHubTranscriptFormatterArtifactKey,
    ) -> ConversionHubTranscriptFormatterArtifactRecord | None:
        return self.records.get((owner_user_id, transcript_id, artifact_key))

    async def delete_for_transcript(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
    ) -> None:
        self.records = {
            key: record
            for key, record in self.records.items()
            if not (record.owner_user_id == owner_user_id and record.transcript_id == transcript_id)
        }


class SignedArtifactReceiptAuthority:
    """Issue and verify test receipts with the production verifier implementation."""

    def __init__(self, *, now: datetime) -> None:
        self._now = now
        self._private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.verifier = HuleEduArtifactReceiptVerifier(
            Settings.model_construct(
                HULEEDU_INTERNAL_IDENTITY_ISSUER="api_gateway_service",
                HULEEDU_INTERNAL_IDENTITY_SIGNING_KEY_ID=_RECEIPT_KEY_ID,
                HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY=public_key.decode("utf-8"),
                HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH=None,
                HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON=None,
                HULEEDU_INTERNAL_IDENTITY_TTL_SECONDS=60,
                HULEEDU_INTERNAL_IDENTITY_ALLOWED_CLOCK_SKEW_SECONDS=5,
            )
        )

    def artifact_payload(
        self,
        *,
        artifact_key: ConversionHubTranscriptFormatterArtifactKey,
        filename: str,
        content_type: str,
        content: bytes,
        job_id: str = "sir-replay-job-1",
        subject: str = "teacher-subject-1",
    ) -> dict[str, object]:
        encoded_payload = _b64url_json(
            {
                "schema_version": "huleedu.sir_convert_artifact_receipt.v1",
                "iss": "api_gateway_service",
                "aud": "skriptoteket",
                "sub": subject,
                "source_app": "skriptoteket",
                "active_app": "skriptoteket",
                "sir_convert_job_id": job_id,
                "artifact_key": artifact_key.value,
                "filename": filename,
                "content_type": content_type,
                "size_bytes": len(content),
                "sha256": sha256(content).hexdigest(),
                "retrieval_path": f"/v2/convert/jobs/{job_id}/artifacts/{artifact_key.value}",
                "iat": int(self._now.timestamp()),
                "exp": int(self._now.timestamp()) + 30,
                "jti": f"receipt-{artifact_key.value}",
            }
        )
        signature = self._private_key.sign(
            encoded_payload.encode("ascii"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return {
            "artifact_key": artifact_key.value,
            "content_type": f"{content_type}; charset=utf-8",
            "content_base64": base64.b64encode(content).decode("ascii"),
            "receipt": {
                "receipt_version": 1,
                "payload": encoded_payload,
                "key_id": _RECEIPT_KEY_ID,
                "signature": f"{INTERNAL_IDENTITY_SIGNATURE_PREFIX}{_b64url_bytes(signature)}",
            },
        }


def _saved_transcript(*, owner_user_id: UUID, transcript_id: UUID) -> ConversionHubSavedTranscript:
    return ConversionHubSavedTranscript(
        id=transcript_id,
        owner_user_id=owner_user_id,
        conversion_hub_job_id=uuid4(),
        sir_convert_job_id="sir-transcript-job-1",
        artifact_key="transcript_json",
        source_filename="seminarium.m4a",
        transcript_schema_version="transcript_json_v1",
        language_code="sv",
        diarization_mode="known_speaker_count",
        speaker_count=2,
        speaker_min=None,
        speaker_max=None,
        generated_at=_now(),
        correlation_id="corr-transcript-1",
        transcript_json={
            "schema_version": "transcript_json_v1",
            "transcript": {
                "text": "Hej från seminariet.",
                "segments": [
                    {
                        "id": "seg_1",
                        "start_seconds": 0,
                        "end_seconds": 2,
                        "speaker_label": "SPEAKER_00",
                        "text": "Hej från seminariet.",
                    },
                    {
                        "id": "seg_2",
                        "start_seconds": 3,
                        "end_seconds": 4,
                        "speaker_label": "SPEAKER_01",
                        "text": "Välkomna.",
                    },
                ],
            },
            "diarization": {"status": "succeeded"},
        },
        created_at=_now(),
        updated_at=_now(),
    )


def _overlay(
    *,
    owner_user_id: UUID,
    transcript_id: UUID,
    canonical_speaker_label: str,
    display_name: str,
) -> ConversionHubTranscriptSpeakerOverlay:
    return ConversionHubTranscriptSpeakerOverlay(
        id=uuid4(),
        owner_user_id=owner_user_id,
        transcript_id=transcript_id,
        canonical_speaker_label=canonical_speaker_label,
        display_name=display_name,
        created_at=_now(),
        updated_at=_now(),
    )


def _manifest(*, job_id: str = "sir-replay-job-1") -> dict[str, object]:
    return {
        "api_version": "v2",
        "job_id": job_id,
        "output_format": "transcript_bundle",
        "artifacts": [
            {
                "artifact_key": "transcript_txt",
                "availability": "available",
                "content_type": "text/plain",
                "filename": "transcript_txt.txt",
                "size_bytes": len(_TXT_CONTENT),
                "sha256": sha256(_TXT_CONTENT).hexdigest(),
                "retrieval_path": f"/v2/convert/jobs/{job_id}/artifacts/transcript_txt",
            },
            {
                "artifact_key": "transcript_md",
                "availability": "available",
                "content_type": "text/markdown",
                "filename": "transcript_md.md",
                "size_bytes": len(_MD_CONTENT),
                "sha256": sha256(_MD_CONTENT).hexdigest(),
                "retrieval_path": f"/v2/convert/jobs/{job_id}/artifacts/transcript_md",
            },
        ],
    }


def _manifest_artifacts(manifest: dict[str, object]) -> list[object]:
    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, list)
    return artifacts


def _artifact_payloads(
    receipt_authority: SignedArtifactReceiptAuthority,
) -> list[dict[str, object]]:
    return [
        receipt_authority.artifact_payload(
            artifact_key=ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT,
            filename="transcript_txt.txt",
            content_type="text/plain",
            content=_TXT_CONTENT,
        ),
        receipt_authority.artifact_payload(
            artifact_key=ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_MD,
            filename="transcript_md.md",
            content_type="text/markdown",
            content=_MD_CONTENT,
        ),
    ]


def _b64url_json(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return _b64url_bytes(encoded.encode("utf-8"))


def _b64url_bytes(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _result(*, job_id: str = "sir-replay-job-1") -> dict[str, object]:
    return {
        "api_version": "v2",
        "job_id": job_id,
        "status": "succeeded",
        "result": {
            "artifact": {
                "filename": "transcript_replay_bundle_manifest.json",
                "format": "transcript_bundle",
                "content_type": "application/json",
                "size_bytes": 512,
                "sha256": "c" * 64,
            },
            "conversion_metadata": {
                "pipeline_used": "transcript_json_to_transcript_bundle_replay_v2",
                "backend_used": None,
                "acceleration_used": None,
                "options_fingerprint": "sha256:replay",
            },
            "warnings": [],
        },
    }


async def _seed_transcript_with_overlays(
    *,
    owner_id: UUID,
    transcript_id: UUID,
    transcripts: InMemorySavedTranscriptRepository,
    overlays: InMemoryTranscriptSpeakerOverlayRepository,
) -> None:
    transcripts.records[transcript_id] = _saved_transcript(
        owner_user_id=owner_id,
        transcript_id=transcript_id,
    )
    await overlays.replace_for_transcript(
        owner_user_id=owner_id,
        transcript_id=transcript_id,
        overlays=[
            _overlay(
                owner_user_id=owner_id,
                transcript_id=transcript_id,
                canonical_speaker_label="SPEAKER_00",
                display_name="Anna Andersson",
            ),
            _overlay(
                owner_user_id=owner_id,
                transcript_id=transcript_id,
                canonical_speaker_label="SPEAKER_01",
                display_name="Bo Berg",
            ),
        ],
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_replay_builds_strict_gateway_job_spec_from_saved_overlay() -> None:
    actor = make_user()
    transcript_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    overlays = InMemoryTranscriptSpeakerOverlayRepository()
    replay_correlation_id = uuid4()
    await _seed_transcript_with_overlays(
        owner_id=actor.id,
        transcript_id=transcript_id,
        transcripts=transcripts,
        overlays=overlays,
    )
    handler = transcript_replay_handlers.PrepareConversionHubTranscriptFormatterReplayHandler(
        transcripts=transcripts,
        speaker_overlays=overlays,
        uow=FakeUow(),
        id_generator=FixedIdGenerator(replay_correlation_id),
    )

    prepared = await handler.handle(
        actor=actor,
        transcript_id=transcript_id,
        request=ConversionHubTranscriptFormatterReplayPrepareRequest(
            requested_artifacts=["txt", "md"]
        ),
        correlation_id=None,
    )

    assert prepared.correlation_id == (
        f"corr_skriptoteket_transcript_replay_{replay_correlation_id}"
    )
    assert prepared.content_type == "application/json"
    assert prepared.gateway_filename == f"saved-transcript-{transcript_id}.json"
    assert prepared.job_spec.source.format == "transcript_json"
    assert prepared.job_spec.conversion.output_format == "transcript_bundle"
    assert prepared.job_spec.transcript_formatter_options.schema_version == (
        "transcript_formatter_replay_v1"
    )
    assert prepared.job_spec.transcript_formatter_options.requested_artifacts == ["txt", "md"]
    assert [
        entry.model_dump()
        for entry in prepared.job_spec.transcript_formatter_options.speaker_label_overrides
    ] == [
        {"canonical_speaker_label": "SPEAKER_00", "display_name": "Anna Andersson"},
        {"canonical_speaker_label": "SPEAKER_01", "display_name": "Bo Berg"},
    ]
    assert prepared.job_spec.retention.pin is False
    assert prepared.transcript_json == transcripts.records[transcript_id].transcript_json


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_replay_rejects_missing_overlay_without_canonical_label_fallback() -> None:
    actor = make_user()
    transcript_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    transcripts.records[transcript_id] = _saved_transcript(
        owner_user_id=actor.id,
        transcript_id=transcript_id,
    )
    handler = transcript_replay_handlers.PrepareConversionHubTranscriptFormatterReplayHandler(
        transcripts=transcripts,
        speaker_overlays=InMemoryTranscriptSpeakerOverlayRepository(),
        uow=FakeUow(),
        id_generator=FixedIdGenerator(uuid4()),
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(
            actor=actor,
            transcript_id=transcript_id,
            request=ConversionHubTranscriptFormatterReplayPrepareRequest(),
            correlation_id="corr-replay-1",
        )

    assert exc.value.code is ErrorCode.VALIDATION_ERROR
