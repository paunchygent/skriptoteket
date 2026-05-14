"""HuleEdu public Exam Converter grant client.

Purpose:
  Mint server-side public conversion grants for Skriptoteket's anonymous Exam
  Converter lane without exposing grant authority or credentials to browsers.

Relationships:
  - Implements `PublicExamConverterGrantAuthorityProtocol`.
  - Called by `PublicExamConverterRuntimeHandler` before Sir Convert submission.
  - Uses HuleEdu's governed `/v1/public-conversion-grants/exam-converter`
    authority surface when configured.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.public_exam_converter import (
    PublicExamConverterGrant,
    PublicExamConverterGrantRequest,
)


@dataclass(frozen=True, slots=True)
class PublicExamConverterGrantAuthoritySettings:
    base_url: str
    client_id: str
    client_assertion: str
    client_assertion_secret: str
    assertion_audience: str
    timeout_seconds: float
    fallback_artifact_ttl_seconds: int
    client_assertion_ttl_seconds: int = 60


class HuleEduPublicExamConverterGrantAuthority:
    """Mint public conversion grants through the HuleEdu server-to-server edge."""

    def __init__(
        self,
        *,
        settings: PublicExamConverterGrantAuthoritySettings,
        client: httpx.AsyncClient,
    ) -> None:
        self._settings = settings
        self._client = client

    async def mint_conversion_grant(
        self,
        *,
        request: PublicExamConverterGrantRequest,
    ) -> PublicExamConverterGrant:
        self._require_configured()
        response = await self._client.post(
            "/v1/public-conversion-grants/exam-converter",
            headers={"X-Correlation-ID": request.correlation_id},
            json={
                "client_id": self._settings.client_id,
                "client_assertion": self._client_assertion(),
                "assertion_aud": self._settings.assertion_audience,
                "source_app": "skriptoteket",
                "capability": "documents.conversion_hub.exam_converter",
                "route_key": "digiexam_dxe_to_examnet_migration_bundle",
                "source_format": "digiexam_dxe",
                "output_format": "examnet_migration_bundle",
                "allowed_targets": [target.value for target in request.allowed_targets],
                "upload_digest": request.upload_digest,
                "upload_mime_types": list(request.upload_mime_types),
                "aggregate_upload_bytes": request.aggregate_upload_bytes,
            },
        )
        if response.status_code != 200:
            raise self._grant_error(response=response)

        payload: object = response.json()
        if not isinstance(payload, dict):
            raise self._invalid_grant_payload()

        token = _string_payload_value(payload, "public_conversion_grant") or _string_payload_value(
            payload,
            "grant",
        )
        if token is None:
            raise self._invalid_grant_payload()

        ttl = _int_payload_value(payload, "artifact_ttl_seconds")
        expires_at = _datetime_payload_value(payload, "expires_at")
        fallback_ttl = self._settings.fallback_artifact_ttl_seconds
        return PublicExamConverterGrant(
            token=token,
            artifact_ttl_seconds=ttl or fallback_ttl,
            expires_at=expires_at or (datetime.now(UTC) + timedelta(seconds=fallback_ttl)),
        )

    def _client_assertion(self) -> str:
        if self._settings.client_assertion_secret.strip():
            return _signed_client_assertion(self._settings)
        return self._settings.client_assertion

    def _require_configured(self) -> None:
        missing = [
            field
            for field, value in {
                "HULEEDU_PUBLIC_EXAM_CONVERTER_GRANT_BASE_URL": self._settings.base_url,
                "HULEEDU_PUBLIC_EXAM_CONVERTER_CLIENT_ID": self._settings.client_id,
                "HULEEDU_PUBLIC_EXAM_CONVERTER_CLIENT_ASSERTION_OR_SECRET": (
                    self._settings.client_assertion or self._settings.client_assertion_secret
                ),
                "HULEEDU_PUBLIC_EXAM_CONVERTER_ASSERTION_AUDIENCE": (
                    self._settings.assertion_audience
                ),
            }.items()
            if not value.strip()
        ]
        if not missing:
            return
        raise DomainError(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Public Exam Converter grant authority is not configured.",
            details={
                "reason_code": "public_exam_converter_grant_authority_unconfigured",
                "missing_settings": missing,
            },
        )

    def _grant_error(self, *, response: httpx.Response) -> DomainError:
        reason_code = "public_exam_converter_grant_authority_failed"
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict) and isinstance(error.get("code"), str):
                reason_code = str(error["code"])
        return DomainError(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Public Exam Converter grant authority rejected the request.",
            details={
                "reason_code": reason_code,
                "upstream_status_code": response.status_code,
            },
        )

    def _invalid_grant_payload(self) -> DomainError:
        return DomainError(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Public Exam Converter grant authority returned an invalid payload.",
            details={"reason_code": "public_exam_converter_invalid_grant_payload"},
        )


def build_public_exam_converter_grant_http_client(
    *,
    settings: PublicExamConverterGrantAuthoritySettings,
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.base_url or "http://127.0.0.1", timeout=settings.timeout_seconds
    )


def _string_payload_value(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) and value.strip() else None


def _int_payload_value(payload: dict[str, object], key: str) -> int | None:
    value = payload.get(key)
    return value if isinstance(value, int) and value > 0 else None


def _datetime_payload_value(payload: dict[str, object], key: str) -> datetime | None:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _signed_client_assertion(settings: PublicExamConverterGrantAuthoritySettings) -> str:
    now = int(datetime.now(UTC).timestamp())
    payload = {
        "iss": settings.client_id,
        "sub": settings.client_id,
        "aud": settings.assertion_audience,
        "iat": now,
        "exp": now + settings.client_assertion_ttl_seconds,
        "jti": f"skriptoteket_public_exam_converter_{uuid4().hex}",
    }
    header = {"alg": "HS256", "typ": "JWT"}
    header_segment = _b64url(json.dumps(header, sort_keys=True).encode("utf-8"))
    payload_segment = _b64url(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = hmac.new(
        settings.client_assertion_secret.strip().encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    return f"{header_segment}.{payload_segment}.{_b64url(signature)}"


def _b64url(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
