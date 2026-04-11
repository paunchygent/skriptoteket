"""Verify HuleEdu Gateway signed internal identity headers.

Purpose:
    Implement the concrete `InternalIdentityContextV1` trust boundary used by
    Skriptoteket app-local continuation after HuleEdu owns browser sessions.

Relationships:
    - Mirrors HuleEdu's accepted detached RS256 header semantics.
    - Implements `HuleEduInternalIdentityVerifierProtocol` for FastAPI
      dependencies and focused verifier tests.
"""

from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Mapping
from functools import lru_cache
from os import R_OK, access
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from pydantic import ValidationError

from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.internal_identity_context import (
    INTERNAL_IDENTITY_CONTEXT_HEADER,
    INTERNAL_IDENTITY_CONTEXT_VERSION,
    INTERNAL_IDENTITY_CONTEXT_VERSION_HEADER,
    INTERNAL_IDENTITY_KEY_ID_HEADER,
    INTERNAL_IDENTITY_SIGNATURE_HEADER,
    INTERNAL_IDENTITY_SIGNATURE_PREFIX,
    InternalIdentityContextV1,
)
from skriptoteket.protocols.identity import HuleEduInternalIdentityVerifierProtocol


def _unauthorized(reason: str, message: str = "Invalid HuleEdu internal identity") -> DomainError:
    return DomainError(
        code=ErrorCode.UNAUTHORIZED,
        message=message,
        details={"reason": reason},
    )


def _b64url_decode(encoded: str) -> bytes:
    padding_length = (-len(encoded)) % 4
    try:
        return base64.urlsafe_b64decode(f"{encoded}{'=' * padding_length}")
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid base64url value") from exc


@lru_cache(maxsize=32)
def _load_public_key(public_key_text: str) -> rsa.RSAPublicKey:
    loaded_key = serialization.load_pem_public_key(public_key_text.encode("utf-8"))
    if not isinstance(loaded_key, rsa.RSAPublicKey):
        raise ValueError("Internal identity verification key must be an RSA public key")
    return loaded_key


def _normalize_key_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty when configured")
    return normalized


def _read_key_text(path_value: str, *, field_name: str) -> str:
    path = Path(path_value).expanduser()
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"{field_name} does not exist: {path_value}") from exc
    if not resolved.is_file():
        raise ValueError(f"{field_name} must point to a regular file: {path_value}")
    if not access(resolved, R_OK):
        raise ValueError(f"{field_name} is not readable: {path_value}")
    return _normalize_key_text(resolved.read_text(encoding="utf-8"), field_name=field_name)


def _trusted_public_keys(settings: Settings) -> dict[str, str]:
    trusted_public_keys: dict[str, str] = {}

    configured_json = settings.HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON
    if configured_json and configured_json.strip():
        decoded = json.loads(configured_json)
        if not isinstance(decoded, dict):
            raise ValueError("HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON must be an object")
        for key_id, public_key in decoded.items():
            if not isinstance(key_id, str) or not isinstance(public_key, str):
                raise ValueError(
                    "HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON must map strings to strings"
                )
            normalized_key_id = _normalize_key_text(
                key_id,
                field_name="HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON key",
            )
            trusted_public_keys[normalized_key_id] = _normalize_key_text(
                public_key,
                field_name=(
                    f"HULEEDU_INTERNAL_IDENTITY_TRUSTED_PUBLIC_KEYS_JSON[{normalized_key_id!r}]"
                ),
            )

    inline_public_key: str | None = None
    if settings.HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY:
        inline_public_key = _normalize_key_text(
            settings.HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY,
            field_name="HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY",
        )
    elif settings.HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH:
        inline_public_key = _read_key_text(
            settings.HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH,
            field_name="HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH",
        )

    if inline_public_key is not None:
        signing_key_id = _normalize_key_text(
            settings.HULEEDU_INTERNAL_IDENTITY_SIGNING_KEY_ID,
            field_name="HULEEDU_INTERNAL_IDENTITY_SIGNING_KEY_ID",
        )
        trusted_public_keys.setdefault(signing_key_id, inline_public_key)

    if not trusted_public_keys:
        raise ValueError("No HuleEdu internal identity public keys configured")
    return trusted_public_keys


def _decode_context(encoded_context: str) -> InternalIdentityContextV1:
    raw_payload = _b64url_decode(encoded_context)
    payload = json.loads(raw_payload.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Internal identity payload must decode to a JSON object")
    return InternalIdentityContextV1.model_validate(payload)


class HuleEduInternalIdentityVerifier(HuleEduInternalIdentityVerifierProtocol):
    """Verify HuleEdu Gateway signed identity context headers."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def verify(
        self,
        *,
        headers: Mapping[str, Any],
        now_ts: int,
    ) -> InternalIdentityContextV1:
        """Verify HuleEdu internal identity headers and return the decoded context.

        Raises:
            DomainError: If any required header, signature, payload, or timestamp
                check fails closed.
        """
        version_value = headers.get(INTERNAL_IDENTITY_CONTEXT_VERSION_HEADER)
        encoded_context = headers.get(INTERNAL_IDENTITY_CONTEXT_HEADER)
        key_id_value = headers.get(INTERNAL_IDENTITY_KEY_ID_HEADER)
        signature_value = headers.get(INTERNAL_IDENTITY_SIGNATURE_HEADER)

        if not isinstance(version_value, str):
            raise _unauthorized("missing_internal_identity_headers")
        if not isinstance(encoded_context, str):
            raise _unauthorized("missing_internal_identity_headers")
        if not isinstance(key_id_value, str):
            raise _unauthorized("missing_internal_identity_headers")
        if not isinstance(signature_value, str):
            raise _unauthorized("missing_internal_identity_headers")

        if version_value.strip() != str(INTERNAL_IDENTITY_CONTEXT_VERSION):
            raise _unauthorized("unsupported_internal_identity_version")

        normalized_key_id = key_id_value.strip()
        if not normalized_key_id:
            raise _unauthorized("missing_internal_identity_key_id")

        if not signature_value.startswith(INTERNAL_IDENTITY_SIGNATURE_PREFIX):
            raise _unauthorized("invalid_internal_identity_signature_format")

        try:
            public_keys_by_id = _trusted_public_keys(self._settings)
        except (OSError, ValueError, json.JSONDecodeError):
            raise _unauthorized("internal_identity_trust_not_configured") from None

        public_key = public_keys_by_id.get(normalized_key_id)
        if public_key is None:
            raise _unauthorized("unknown_internal_identity_key_id")

        supplied_signature = signature_value[len(INTERNAL_IDENTITY_SIGNATURE_PREFIX) :]
        try:
            _load_public_key(public_key).verify(
                _b64url_decode(supplied_signature),
                encoded_context.encode("ascii"),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except (InvalidSignature, ValueError, UnicodeEncodeError):
            raise _unauthorized("invalid_internal_identity_signature") from None

        try:
            context = _decode_context(encoded_context)
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError, ValidationError):
            raise _unauthorized("invalid_internal_identity_payload") from None

        expected_issuer = self._settings.HULEEDU_INTERNAL_IDENTITY_ISSUER
        expected_audience = (
            self._settings.HULEEDU_INTERNAL_IDENTITY_AUDIENCE or self._settings.SERVICE_NAME
        )
        if context.iss != expected_issuer:
            raise _unauthorized("invalid_internal_identity_issuer")
        if context.aud != expected_audience:
            raise _unauthorized("invalid_internal_identity_audience")
        if context.exp < context.iat:
            raise _unauthorized("invalid_internal_identity_timestamps")

        max_ttl_seconds = self._settings.HULEEDU_INTERNAL_IDENTITY_TTL_SECONDS
        if (context.exp - context.iat) > max_ttl_seconds:
            raise _unauthorized("internal_identity_ttl_exceeded")

        allowed_clock_skew = self._settings.HULEEDU_INTERNAL_IDENTITY_ALLOWED_CLOCK_SKEW_SECONDS
        if context.iat > now_ts + allowed_clock_skew:
            raise _unauthorized("internal_identity_issued_in_future")
        if context.exp <= now_ts - allowed_clock_skew:
            raise _unauthorized("internal_identity_expired")

        return context
