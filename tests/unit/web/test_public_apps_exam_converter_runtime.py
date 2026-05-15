"""Route tests for the public Exam Converter runtime lane."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.handlers.public_exam_converter_jobs import (
    PublicExamConverterRuntimeHandler,
)
from skriptoteket.application.curated_apps.sir_convert_contracts import (
    DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
    DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
    DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    CuratedAppPublicAccessProfile,
    CuratedAppPublicCapability,
    CuratedAppPublicRuntimeStatus,
    CuratedAppUiMode,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    public_exam_converter_store,
)
from skriptoteket.infrastructure.security.public_helper_request_throttle import (
    InMemoryPublicHelperRequestThrottle,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.public_exam_converter import (
    PublicExamConverterGrant,
    PublicExamConverterGrantAuthorityProtocol,
    PublicExamConverterGrantRequest,
    PublicExamConverterJobStoreProtocol,
    PublicExamConverterSirConvertSubmitRequest,
    PublicExamConverterSirConvertSubmittedJob,
)
from skriptoteket.protocols.public_helpers import PublicHelperThrottleProtocol
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertArtifactV2,
    SirConvertJobV2,
)
from skriptoteket.web.api.v1 import public_apps_exam_converter as api
from skriptoteket.web.middleware.error_handler import error_handler_middleware


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FixedIdGenerator:
    def new_uuid(self) -> UUID:
        return UUID("4f27d43f-7c2e-4c9c-a4df-2d799f88527a")


class FakeGrantAuthority:
    def __init__(self, *, now: datetime) -> None:
        self.requests: list[PublicExamConverterGrantRequest] = []
        self._now = now

    async def mint_conversion_grant(
        self,
        *,
        request: PublicExamConverterGrantRequest,
    ) -> PublicExamConverterGrant:
        self.requests.append(request)
        return PublicExamConverterGrant(
            token="opaque-public-grant",
            artifact_ttl_seconds=3600,
            expires_at=self._now + timedelta(seconds=3600),
        )


class FakeSirConvertClient:
    def __init__(self) -> None:
        self.submit_requests: list[PublicExamConverterSirConvertSubmitRequest] = []
        self.download_requests: list[tuple[str, str, str]] = []
        self.status = "succeeded"

    async def submit_public_exam_converter_job(
        self,
        *,
        request: PublicExamConverterSirConvertSubmitRequest,
    ) -> PublicExamConverterSirConvertSubmittedJob:
        self.submit_requests.append(request)
        return PublicExamConverterSirConvertSubmittedJob(
            job_id="sir-job-123",
            status=self.status,
            idempotent_replay=False,
            manifest_artifact_read_lease_token="opaque-manifest-lease",
        )

    async def get_public_exam_converter_job(
        self,
        job_id: str,
        *,
        public_conversion_grant: str,
        correlation_id: str,
    ) -> SirConvertJobV2:
        assert public_conversion_grant == "opaque-public-grant"
        assert correlation_id
        return SirConvertJobV2(job_id=job_id, status=self.status)

    async def get_public_exam_converter_result(
        self,
        job_id: str,
        *,
        public_conversion_grant: str,
        correlation_id: str,
    ) -> dict[str, object]:
        assert public_conversion_grant == "opaque-public-grant"
        return {
            "job_id": job_id,
            "result": {
                "conversion_metadata": {
                    "route_key": "digiexam_dxe_to_examnet_migration_bundle",
                    "bundle_schema_version": DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
                    "target_readiness_report_artifact_key": "target_readiness_report",
                }
            },
        }

    async def get_public_exam_converter_artifact_manifest(
        self,
        job_id: str,
        *,
        public_conversion_grant: str,
        public_artifact_read_lease: str,
        correlation_id: str,
    ) -> dict[str, object]:
        assert public_conversion_grant == "opaque-public-grant"
        assert public_artifact_read_lease == "opaque-manifest-lease"
        return {
            "schema_version": DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
            "job_id": job_id,
            "bundle_status": "partial",
            "artifacts": [
                {
                    "artifact_key": "examnet_pdf",
                    "filename": "examnet-import.pdf",
                    "content_type": "application/pdf",
                    "availability": "available",
                    "size_bytes": 16,
                    "sha256": "sha256:abc",
                    "download_path": "/v2/convert/jobs/sir-job-123/artifacts/examnet_pdf",
                    "public_artifact_read_lease": {
                        "token": "opaque-examnet-pdf-lease",
                        "artifact_key": "examnet_pdf",
                    },
                },
                {
                    "artifact_key": "target_readiness_report",
                    "filename": "target-readiness-report.json",
                    "content_type": "application/json",
                    "availability": "available",
                    "public_artifact_read_lease": {
                        "token": "opaque-readiness-lease",
                        "artifact_key": "target_readiness_report",
                    },
                },
                {
                    "artifact_key": "qti_package",
                    "filename": "qti-package.zip",
                    "content_type": "application/zip",
                    "availability": "not_requested",
                },
            ],
            "manual_follow_up": {"required": True, "count": 1},
            "readiness": {
                "artifact_key": "target_readiness_report",
                "exportable_targets": ["examnet_pdf"],
                "review_required": True,
            },
            "source_binding": {
                "source_ir_schema_version": DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION,
                "source_ir_sha256": "sha256:source",
                "effective_exam_schema_version": DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
                "effective_exam_sha256": "sha256:source",
            },
            "warnings": {"count": 0},
        }

    async def download_public_exam_converter_artifact(
        self,
        job_id: str,
        *,
        artifact_key: str,
        public_conversion_grant: str,
        public_artifact_read_lease: str,
        correlation_id: str,
    ) -> SirConvertArtifactV2:
        assert public_conversion_grant == "opaque-public-grant"
        self.download_requests.append((job_id, artifact_key, public_artifact_read_lease))
        return SirConvertArtifactV2(
            filename="examnet-import.pdf",
            content_type="application/pdf",
            content=b"%PDF fake",
        )


class RuntimeProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        clock: ClockProtocol,
        registry: CuratedAppRegistryProtocol,
        throttle: PublicHelperThrottleProtocol,
        store: PublicExamConverterJobStoreProtocol,
        grant_authority: PublicExamConverterGrantAuthorityProtocol,
        sir_convert: FakeSirConvertClient,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._clock = clock
        self._registry = registry
        self._throttle = throttle
        self._store = store
        self._grant_authority = grant_authority
        self._sir_convert = sir_convert

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.APP)
    def clock(self) -> ClockProtocol:
        return self._clock

    @provide(scope=Scope.APP)
    def registry(self) -> CuratedAppRegistryProtocol:
        return self._registry

    @provide(scope=Scope.APP)
    def throttle(self) -> PublicHelperThrottleProtocol:
        return self._throttle

    @provide(scope=Scope.APP)
    def store(self) -> PublicExamConverterJobStoreProtocol:
        return self._store

    @provide(scope=Scope.APP)
    def grant_authority(self) -> PublicExamConverterGrantAuthorityProtocol:
        return self._grant_authority

    @provide(scope=Scope.APP)
    def sir_convert(self) -> FakeSirConvertClient:
        return self._sir_convert

    @provide(scope=Scope.APP)
    def id_generator(self) -> IdGeneratorProtocol:
        return FixedIdGenerator()

    @provide(scope=Scope.REQUEST)
    def handler(self) -> PublicExamConverterRuntimeHandler:
        return PublicExamConverterRuntimeHandler(
            store=self._store,
            grant_authority=self._grant_authority,
            sir_convert=self._sir_convert,
            clock=self._clock,
            id_generator=FixedIdGenerator(),
        )


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 5, 13, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def registry() -> CuratedAppRegistryProtocol:
    class Registry:
        def __init__(self) -> None:
            self._app = CuratedAppDefinition(
                app_id="documents.conversion_hub",
                tool_id=curated_app_tool_id(app_id="documents.conversion_hub"),
                app_version="app:test",
                ui_mode=CuratedAppUiMode.BESPOKE_REQUIRED,
                title="Konvertera dokument",
                summary="Konvertera DigiExam-prov.",
                min_role=Role.USER,
                public_access_profile=CuratedAppPublicAccessProfile.AUTHENTICATED_ONLY,
                public_capabilities=[
                    CuratedAppPublicCapability(
                        scope="exam_converter",
                        profile=CuratedAppPublicAccessProfile.PUBLIC_BROWSER_RUNTIME,
                        runtime_status=CuratedAppPublicRuntimeStatus.ACTIVE,
                    )
                ],
                placements=[CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt")],
            )

        def list_all(self) -> list[CuratedAppDefinition]:
            return [self._app]

        def get_by_app_id(self, *, app_id: str) -> CuratedAppDefinition | None:
            if app_id != "documents.conversion_hub":
                return None
            return self._app

        def get_by_tool_id(self, *, tool_id: UUID) -> CuratedAppDefinition | None:
            if tool_id != self._app.tool_id:
                return None
            return self._app

    return Registry()


@pytest.fixture
def sir_convert() -> FakeSirConvertClient:
    return FakeSirConvertClient()


@pytest.fixture
def grant_authority(now: datetime) -> FakeGrantAuthority:
    return FakeGrantAuthority(now=now)


@pytest.fixture
def app(
    settings: Settings,
    now: datetime,
    registry: CuratedAppRegistryProtocol,
    grant_authority: FakeGrantAuthority,
    sir_convert: FakeSirConvertClient,
) -> FastAPI:
    app = FastAPI()

    @app.middleware("http")
    async def attach_correlation_id(request, call_next):  # type: ignore[no-untyped-def]
        header_value = request.headers.get("X-Correlation-ID")
        if header_value:
            request.state.correlation_id = UUID(header_value)
        return await call_next(request)

    app.middleware("http")(error_handler_middleware)
    app.include_router(api.router)
    container = make_async_container(
        RuntimeProvider(
            settings=settings,
            clock=FixedClock(now=now),
            registry=registry,
            throttle=InMemoryPublicHelperRequestThrottle(),
            store=public_exam_converter_store.InMemoryPublicExamConverterJobStore(),
            grant_authority=grant_authority,
            sir_convert=sir_convert,
        )
    )
    setup_dishka(container, app)
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_public_exam_converter_submit_poll_manifest_and_download_use_opaque_grant(
    client: httpx.AsyncClient,
    grant_authority: FakeGrantAuthority,
    sir_convert: FakeSirConvertClient,
) -> None:
    client.cookies.set("ambient_session", "ignored")
    response = await client.post(
        "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs",
        data={"targets_json": '["examnet_pdf"]'},
        files={
            "source_dxe": ("exam.dxe", b'{"exam": true}', "application/octet-stream"),
            "graded_result_pdf": ("graded-result.pdf", b"%PDF fake", "application/pdf"),
        },
        headers={"X-Correlation-ID": "53f6d262-789c-4af4-a2c2-5ff5044d452f"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["public_job_id"] == "4f27d43f-7c2e-4c9c-a4df-2d799f88527a"
    assert payload["status"] == "succeeded"
    assert payload["requested_targets"] == ["examnet_pdf"]
    assert grant_authority.requests[0].correlation_id == "53f6d262-789c-4af4-a2c2-5ff5044d452f"
    assert grant_authority.requests[0].upload_mime_types == (
        "application/octet-stream",
        "application/pdf",
    )
    submit_request = sir_convert.submit_requests[0]
    assert submit_request.public_conversion_grant == "opaque-public-grant"
    assert submit_request.job_spec["source"] == {
        "kind": "upload",
        "filename": "exam.dxe",
        "format": "digiexam_dxe",
    }
    assert submit_request.job_spec["conversion"] == {
        "output_format": "examnet_migration_bundle",
        "targets": ["examnet_pdf"],
        "artifact_language": "sv",
        "reference_docx_filename": None,
    }

    status_response = await client.get(
        "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/"
        "4f27d43f-7c2e-4c9c-a4df-2d799f88527a"
    )
    result_response = await client.get(
        "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/"
        "4f27d43f-7c2e-4c9c-a4df-2d799f88527a/result"
    )
    manifest_response = await client.get(
        "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/"
        "4f27d43f-7c2e-4c9c-a4df-2d799f88527a/artifacts"
    )
    artifact_response = await client.get(
        "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/"
        "4f27d43f-7c2e-4c9c-a4df-2d799f88527a/artifacts/examnet_pdf/download"
    )

    assert status_response.status_code == 200
    assert status_response.json()["status"] == "succeeded"
    assert result_response.status_code == 200
    assert result_response.json()["result"]["conversion_metadata"]["route_key"] == (
        "digiexam_dxe_to_examnet_migration_bundle"
    )
    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert manifest["schema_version"] == DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION
    assert manifest["readiness"]["artifact_key"] == "target_readiness_report"
    assert manifest["source_binding"]["effective_exam_schema_version"] == (
        DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION
    )
    assert manifest["artifacts"][0]["download_url"].endswith(
        "/jobs/4f27d43f-7c2e-4c9c-a4df-2d799f88527a/artifacts/examnet_pdf/download"
    )
    assert "/v2/convert" not in manifest["artifacts"][0]["download_url"]
    assert artifact_response.status_code == 200
    assert artifact_response.headers["content-type"] == "application/pdf"
    assert artifact_response.content.startswith(b"%PDF")
    assert artifact_response.headers.get("set-cookie") is None
    assert sir_convert.download_requests == [
        ("sir-job-123", "examnet_pdf", "opaque-examnet-pdf-lease")
    ]


@pytest.mark.asyncio
async def test_public_exam_converter_rejects_invalid_target_before_grant_mint(
    client: httpx.AsyncClient,
    grant_authority: FakeGrantAuthority,
    sir_convert: FakeSirConvertClient,
) -> None:
    response = await client.post(
        "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs",
        data={"targets_json": '["editable_docx"]'},
        files={"source_dxe": ("exam.dxe", b"{}", "application/octet-stream")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"]["reason_code"] == (
        "public_exam_converter_invalid_target"
    )
    assert grant_authority.requests == []
    assert sir_convert.submit_requests == []


@pytest.mark.asyncio
async def test_public_exam_converter_rejects_unsupported_source_file_type(
    client: httpx.AsyncClient,
    grant_authority: FakeGrantAuthority,
) -> None:
    response = await client.post(
        "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs",
        files={"source_dxe": ("exam.pdf", b"%PDF", "application/pdf")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["details"]["reason_code"] == (
        "public_exam_converter_unsupported_file_type"
    )
    assert grant_authority.requests == []


@pytest.mark.asyncio
async def test_public_exam_converter_rate_limits_anonymous_submit(
    now: datetime,
    registry: CuratedAppRegistryProtocol,
    grant_authority: FakeGrantAuthority,
    sir_convert: FakeSirConvertClient,
) -> None:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(api.router)
    container = make_async_container(
        RuntimeProvider(
            settings=Settings(PUBLIC_EXAM_CONVERTER_RATE_LIMIT_MAX_REQUESTS=1),
            clock=FixedClock(now=now),
            registry=registry,
            throttle=InMemoryPublicHelperRequestThrottle(),
            store=public_exam_converter_store.InMemoryPublicExamConverterJobStore(),
            grant_authority=grant_authority,
            sir_convert=sir_convert,
        )
    )
    setup_dishka(container, app)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as limited_client:
        first = await limited_client.post(
            "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs",
            files={"source_dxe": ("exam.dxe", b"{}", "application/octet-stream")},
        )
        second = await limited_client.post(
            "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs",
            files={"source_dxe": ("exam.dxe", b"{}", "application/octet-stream")},
        )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["details"]["reason_code"] == (
        "public_exam_converter_rate_limited"
    )
