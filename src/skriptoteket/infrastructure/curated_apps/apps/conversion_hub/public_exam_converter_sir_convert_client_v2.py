"""Sir Convert client for the public Exam Converter lane.

Purpose:
  Call Sir Convert-a-Lot v2 public Exam Converter endpoints with server-side
  public grants and artifact read leases, separate from the generic v2 client.

Relationships:
  - Implements `PublicExamConverterSirConvertProtocol`.
  - Reuses the generic Sir Convert client settings and response helpers.
  - Used by the public Exam Converter application handler through Dishka DI.
"""

from __future__ import annotations

import io
import json

import httpx

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.sir_convert_client_v2 import (
    SirConvertClientSettingsV2,
    _extract_service_error,
    _read_job_id_and_status,
)
from skriptoteket.protocols.public_exam_converter import (
    PublicExamConverterSirConvertProtocol,
    PublicExamConverterSirConvertSubmitRequest,
    PublicExamConverterSirConvertSubmittedJob,
)
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertArtifactV2,
    SirConvertJobV2,
)


class PublicExamConverterSirConvertClientV2(PublicExamConverterSirConvertProtocol):
    """Sir Convert public grant/read-lease client for Exam Converter jobs."""

    def __init__(self, *, settings: SirConvertClientSettingsV2, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    def _headers(
        self,
        *,
        idempotency_key: str | None = None,
        correlation_id: str,
    ) -> dict[str, str]:
        headers = {"X-API-Key": self._settings.api_key, "X-Correlation-ID": correlation_id}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    def _public_grant_headers(
        self,
        *,
        public_conversion_grant: str,
        idempotency_key: str | None = None,
        correlation_id: str,
    ) -> dict[str, str]:
        headers = self._headers(idempotency_key=idempotency_key, correlation_id=correlation_id)
        headers["X-Public-Conversion-Grant"] = public_conversion_grant
        return headers

    def _public_artifact_headers(
        self,
        *,
        public_conversion_grant: str,
        public_artifact_read_lease: str,
        correlation_id: str,
    ) -> dict[str, str]:
        headers = self._public_grant_headers(
            public_conversion_grant=public_conversion_grant,
            correlation_id=correlation_id,
        )
        headers["X-Public-Artifact-Read-Lease"] = public_artifact_read_lease
        return headers

    async def submit_public_exam_converter_job(
        self,
        *,
        request: PublicExamConverterSirConvertSubmitRequest,
    ) -> PublicExamConverterSirConvertSubmittedJob:
        files: dict[str, tuple[str, io.BytesIO, str]] = {
            "file": (
                request.filename,
                io.BytesIO(request.file_bytes),
                request.content_type,
            )
        }
        if (
            request.graded_result_pdf_filename is not None
            and request.graded_result_pdf_bytes is not None
        ):
            files["graded_result_pdf"] = (
                request.graded_result_pdf_filename,
                io.BytesIO(request.graded_result_pdf_bytes),
                "application/pdf",
            )

        response = await self._client.post(
            "/v2/convert/jobs",
            params={"wait_seconds": request.wait_seconds},
            headers=self._public_grant_headers(
                public_conversion_grant=request.public_conversion_grant,
                idempotency_key=request.idempotency_key,
                correlation_id=request.correlation_id,
            ),
            data={
                "job_spec": json.dumps(request.job_spec, separators=(",", ":"), sort_keys=True),
            },
            files=files,
        )
        if response.status_code not in {200, 202}:
            raise _extract_service_error(
                response,
                message_fallback="Failed to submit public Exam Converter job.",
            )

        payload: object = response.json()
        job_id, status = _read_job_id_and_status(payload)
        idempotent_replay = response.headers.get("X-Idempotent-Replay", "").lower() == "true"
        return PublicExamConverterSirConvertSubmittedJob(
            job_id=job_id,
            status=status,
            idempotent_replay=idempotent_replay,
            manifest_artifact_read_lease_token=_manifest_read_lease_token(payload),
        )

    async def get_public_exam_converter_job(
        self,
        job_id: str,
        *,
        public_conversion_grant: str,
        correlation_id: str,
    ) -> SirConvertJobV2:
        response = await self._client.get(
            f"/v2/convert/jobs/{job_id}",
            headers=self._public_grant_headers(
                public_conversion_grant=public_conversion_grant,
                correlation_id=correlation_id,
            ),
        )
        if response.status_code != 200:
            raise _extract_service_error(
                response,
                message_fallback="Failed to read public Exam Converter job status.",
                job_id=job_id,
            )
        payload: object = response.json()
        current_job_id, status = _read_job_id_and_status(payload)
        return SirConvertJobV2(job_id=current_job_id, status=status)

    async def get_public_exam_converter_result(
        self,
        job_id: str,
        *,
        public_conversion_grant: str,
        correlation_id: str,
    ) -> dict[str, object]:
        response = await self._client.get(
            f"/v2/convert/jobs/{job_id}/result",
            headers=self._public_grant_headers(
                public_conversion_grant=public_conversion_grant,
                correlation_id=correlation_id,
            ),
        )
        if response.status_code not in {200, 202}:
            raise _extract_service_error(
                response,
                message_fallback="Failed to read public Exam Converter job result.",
                job_id=job_id,
            )
        return _object_payload(response=response, job_id=job_id, payload_name="result")

    async def get_public_exam_converter_artifact_manifest(
        self,
        job_id: str,
        *,
        public_conversion_grant: str,
        public_artifact_read_lease: str,
        correlation_id: str,
    ) -> dict[str, object]:
        response = await self._client.get(
            f"/v2/convert/jobs/{job_id}/artifacts",
            headers=self._public_artifact_headers(
                public_conversion_grant=public_conversion_grant,
                public_artifact_read_lease=public_artifact_read_lease,
                correlation_id=correlation_id,
            ),
        )
        if response.status_code not in {200, 202}:
            raise _extract_service_error(
                response,
                message_fallback="Failed to read public Exam Converter artifact manifest.",
                job_id=job_id,
            )
        return _object_payload(response=response, job_id=job_id, payload_name="manifest")

    async def download_public_exam_converter_artifact(
        self,
        job_id: str,
        *,
        artifact_key: str,
        public_conversion_grant: str,
        public_artifact_read_lease: str,
        correlation_id: str,
    ) -> SirConvertArtifactV2:
        response = await self._client.get(
            f"/v2/convert/jobs/{job_id}/artifacts/{artifact_key}",
            headers=self._public_artifact_headers(
                public_conversion_grant=public_conversion_grant,
                public_artifact_read_lease=public_artifact_read_lease,
                correlation_id=correlation_id,
            ),
        )
        if response.status_code != 200:
            raise _extract_service_error(
                response,
                message_fallback="Failed to download public Exam Converter artifact.",
                job_id=job_id,
            )
        return SirConvertArtifactV2(
            filename=_filename_from_response(response=response, fallback=artifact_key),
            content_type=response.headers.get("Content-Type", "application/octet-stream"),
            content=response.content,
        )


def _object_payload(
    *,
    response: httpx.Response,
    job_id: str,
    payload_name: str,
) -> dict[str, object]:
    payload: object = response.json()
    if isinstance(payload, dict):
        return payload
    raise DomainError(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message=f"Sir Convert-a-Lot v2 returned an invalid public {payload_name} payload.",
        details={"job_id": job_id},
    )


def _manifest_read_lease_token(payload: object) -> str:
    if isinstance(payload, dict):
        lease_obj = payload.get("public_artifact_read_lease")
        if isinstance(lease_obj, dict):
            token = lease_obj.get("token")
            if isinstance(token, str) and token.strip():
                return token
        if isinstance(lease_obj, str) and lease_obj.strip():
            return lease_obj
    raise DomainError(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message="Sir Convert-a-Lot v2 response is missing public artifact read lease.",
        details={"reason_code": "public_exam_converter_missing_manifest_read_lease"},
    )


def _filename_from_response(*, response: httpx.Response, fallback: str) -> str:
    disposition = response.headers.get("Content-Disposition", "")
    if "filename=" not in disposition:
        return fallback
    _, _, after = disposition.partition("filename=")
    return after.strip().strip('"') or fallback
