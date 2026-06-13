"""HuleEdu artifact receipt verification for producer-owned formatter bytes.

Domain purpose:
  Verify signed HuleEdu Gateway receipts that bind Sir Convert artifact
  metadata to an owner-authorized browser-session artifact read.

Relationships:
  - Implements the Conversion Hub receipt verifier protocol.
  - Reuses the HuleEdu internal identity trust key set for detached RS256
    verification.
  - Feeds replay completion so browser-forwarded bytes are only accepted when
    paired with backend-verifiable Gateway authority.
"""

from __future__ import annotations

import base64
import binascii
import json

from pydantic import ValidationError

from skriptoteket.application.curated_apps.conversion_hub_transcript_replay import (
    ConversionHubTranscriptFormatterArtifactReceipt,
    ConversionHubTranscriptFormatterArtifactReceiptPayload,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import validation_error
from skriptoteket.infrastructure.security.huleedu_internal_identity import (
    verify_huleedu_detached_rs256_signature,
)
from skriptoteket.protocols.conversion_hub import (
    ConversionHubTranscriptFormatterArtifactReceiptVerifierProtocol,
)


class HuleEduArtifactReceiptVerifier(
    ConversionHubTranscriptFormatterArtifactReceiptVerifierProtocol
):
    """Verify HuleEdu-signed artifact receipts against local trust settings."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def verify(
        self,
        *,
        receipt: ConversionHubTranscriptFormatterArtifactReceipt,
        now_ts: int,
    ) -> ConversionHubTranscriptFormatterArtifactReceiptPayload:
        """Return a verified artifact receipt payload or fail closed."""
        try:
            verify_huleedu_detached_rs256_signature(
                settings=self._settings,
                key_id=receipt.key_id,
                encoded_payload=receipt.payload,
                signature=receipt.signature,
            )
            payload = _decode_receipt_payload(receipt.payload)
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError, ValidationError) as exc:
            raise validation_error("Replay artifact receipt is invalid.") from exc

        expected_issuer = self._settings.HULEEDU_INTERNAL_IDENTITY_ISSUER
        if payload.iss != expected_issuer:
            raise validation_error("Replay artifact receipt issuer is invalid.")

        if payload.exp < payload.iat:
            raise validation_error("Replay artifact receipt timestamps are invalid.")

        max_ttl_seconds = self._settings.HULEEDU_INTERNAL_IDENTITY_TTL_SECONDS
        if (payload.exp - payload.iat) > max_ttl_seconds:
            raise validation_error("Replay artifact receipt TTL is invalid.")

        allowed_clock_skew = self._settings.HULEEDU_INTERNAL_IDENTITY_ALLOWED_CLOCK_SKEW_SECONDS
        if payload.iat > now_ts + allowed_clock_skew:
            raise validation_error("Replay artifact receipt was issued in the future.")
        if payload.exp <= now_ts - allowed_clock_skew:
            raise validation_error("Replay artifact receipt is expired.")

        return payload


def _decode_receipt_payload(
    encoded_payload: str,
) -> ConversionHubTranscriptFormatterArtifactReceiptPayload:
    decoded = _b64url_decode(encoded_payload)
    payload = json.loads(decoded.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Artifact receipt payload must be a JSON object")
    return ConversionHubTranscriptFormatterArtifactReceiptPayload.model_validate(payload)


def _b64url_decode(encoded: str) -> bytes:
    padding_length = (-len(encoded)) % 4
    try:
        return base64.urlsafe_b64decode(f"{encoded}{'=' * padding_length}")
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid base64url value") from exc
