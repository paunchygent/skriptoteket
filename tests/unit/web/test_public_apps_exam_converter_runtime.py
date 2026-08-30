"""Route tests for the public Exam Converter runtime lane."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI, Request, Response
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.handlers.public_exam_converter_jobs import (
    PublicExamConverterRuntimeHandler,
)
from skriptoteket.application.curated_apps.public_exam_converter import (
    PublicExamConverterJobStatus,
    PublicExamConverterSubmittedJob,
    PublicExamConverterTarget,
    PublicExamConverterUpload,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_schema_versions import (
    DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
    DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
)
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
    PublicExamConverterJobStoreProtocol,
    PublicExamConverterLocalExecutorProtocol,
)
from skriptoteket.protocols.public_helpers import PublicHelperThrottleProtocol
from skriptoteket.web.api.v1 import public_apps_exam_converter as api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.public_exam_converter_runtime import local_public_exam_artifact


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FixedIdGenerator:
    def new_uuid(self) -> UUID:
        return UUID("4f27d43f-7c2e-4c9c-a4df-2d799f88527a")


class FakeLocalExecutor:
    def __init__(
        self,
        *,
        store: PublicExamConverterJobStoreProtocol,
        complete_immediately: bool = True,
    ) -> None:
        self.requests: list[
            tuple[
                PublicExamConverterSubmittedJob,
                PublicExamConverterUpload,
                PublicExamConverterUpload | None,
                str,
            ]
        ] = []
        self._store = store
        self._complete_immediately = complete_immediately

    @property
    def store(self) -> PublicExamConverterJobStoreProtocol:
        return self._store

    async def enqueue(
        self,
        *,
        job: PublicExamConverterSubmittedJob,
        source_dxe: PublicExamConverterUpload,
        graded_result_pdf: PublicExamConverterUpload | None,
        correlation_id: str,
    ) -> None:
        self.requests.append((job, source_dxe, graded_result_pdf, correlation_id))
        if not self._complete_immediately:
            return
        await self._store.update(
            job=replace(
                job,
                status=PublicExamConverterJobStatus.SUCCEEDED,
                artifact=local_public_exam_artifact(source_dxe=source_dxe),
                result={
                    "conversion_metadata": {
                        "route_key": "digiexam_dxe_to_examnet_migration_bundle",
                        "bundle_schema_version": DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
                        "target_readiness_report_artifact_key": "target_readiness_report",
                    }
                },
            )
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
        executor: PublicExamConverterLocalExecutorProtocol,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._clock = clock
        self._registry = registry
        self._throttle = throttle
        self._store = store
        self._executor = executor

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
    def executor(self) -> PublicExamConverterLocalExecutorProtocol:
        return self._executor

    @provide(scope=Scope.APP)
    def id_generator(self) -> IdGeneratorProtocol:
        return FixedIdGenerator()

    @provide(scope=Scope.REQUEST)
    def handler(self) -> PublicExamConverterRuntimeHandler:
        return PublicExamConverterRuntimeHandler(
            store=self._store,
            executor=self._executor,
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
def local_executor() -> FakeLocalExecutor:
    store = public_exam_converter_store.InMemoryPublicExamConverterJobStore()
    return FakeLocalExecutor(store=store)


@pytest.fixture
def app(
    settings: Settings,
    now: datetime,
    registry: CuratedAppRegistryProtocol,
    local_executor: FakeLocalExecutor,
) -> FastAPI:
    app = FastAPI()

    @app.middleware("http")
    async def attach_correlation_id(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        header_value = request.headers.get("X-Correlation-ID")
        if header_value:
            request.state.correlation_id = UUID(header_value)
        return await call_next(request)

    app.middleware("http")(error_handler_middleware)
    app.include_router(api.router)
    store = local_executor.store
    container = make_async_container(
        RuntimeProvider(
            settings=settings,
            clock=FixedClock(now=now),
            registry=registry,
            throttle=InMemoryPublicHelperRequestThrottle(),
            store=store,
            executor=local_executor,
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
async def test_public_exam_converter_submit_poll_manifest_and_download_use_local_executor(
    client: httpx.AsyncClient,
    local_executor: FakeLocalExecutor,
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
    assert payload["status"] == "queued"
    assert payload["requested_targets"] == ["examnet_pdf"]
    job, source_dxe, graded_result_pdf, correlation_id = local_executor.requests[0]
    assert job.local_job_id == UUID("4f27d43f-7c2e-4c9c-a4df-2d799f88527a")
    assert job.requested_targets == (PublicExamConverterTarget.EXAMNET_PDF,)
    assert source_dxe.filename == "exam.dxe"
    assert graded_result_pdf is not None
    assert graded_result_pdf.filename == "graded-result.pdf"
    assert correlation_id == "53f6d262-789c-4af4-a2c2-5ff5044d452f"
    assert "grant_token" not in PublicExamConverterSubmittedJob.__dataclass_fields__
    assert "upstream_job_id" not in PublicExamConverterSubmittedJob.__dataclass_fields__

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
    assert manifest["warnings"] == {
        "count": 1,
        "items": [
            {
                "code": "unsupported_source_fragment",
                "message": "One source fragment requires review.",
            }
        ],
    }
    assert manifest["artifacts"][0]["download_url"].endswith(
        "/jobs/4f27d43f-7c2e-4c9c-a4df-2d799f88527a/artifacts/examnet_pdf/download"
    )
    assert "/v2/convert" not in manifest["artifacts"][0]["download_url"]
    assert artifact_response.status_code == 200
    assert artifact_response.headers["content-type"] == "application/pdf"
    assert artifact_response.content.startswith(b"%PDF")
    assert artifact_response.headers.get("set-cookie") is None


@pytest.mark.asyncio
async def test_public_exam_converter_rejects_invalid_target_before_local_enqueue(
    client: httpx.AsyncClient,
    local_executor: FakeLocalExecutor,
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
    assert local_executor.requests == []


@pytest.mark.asyncio
async def test_public_exam_converter_rejects_unsupported_source_file_type(
    client: httpx.AsyncClient,
    local_executor: FakeLocalExecutor,
) -> None:
    response = await client.post(
        "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs",
        files={"source_dxe": ("exam.pdf", b"%PDF", "application/pdf")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["details"]["reason_code"] == (
        "public_exam_converter_unsupported_file_type"
    )
    assert local_executor.requests == []


@pytest.mark.asyncio
async def test_public_exam_converter_rate_limits_anonymous_submit(
    now: datetime,
    registry: CuratedAppRegistryProtocol,
) -> None:
    store = public_exam_converter_store.InMemoryPublicExamConverterJobStore()
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(api.router)
    container = make_async_container(
        RuntimeProvider(
            settings=Settings(PUBLIC_EXAM_CONVERTER_RATE_LIMIT_MAX_REQUESTS=1),
            clock=FixedClock(now=now),
            registry=registry,
            throttle=InMemoryPublicHelperRequestThrottle(),
            store=store,
            executor=FakeLocalExecutor(store=store),
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


@pytest.mark.asyncio
async def test_public_exam_converter_queued_job_remains_pollable_and_enforces_concurrency_limit(
    now: datetime,
    registry: CuratedAppRegistryProtocol,
) -> None:
    store = public_exam_converter_store.InMemoryPublicExamConverterJobStore()
    executor = FakeLocalExecutor(store=store, complete_immediately=False)
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(api.router)
    container = make_async_container(
        RuntimeProvider(
            settings=Settings(PUBLIC_EXAM_CONVERTER_CONCURRENCY_LIMIT=1),
            clock=FixedClock(now=now),
            registry=registry,
            throttle=InMemoryPublicHelperRequestThrottle(),
            store=store,
            executor=executor,
        )
    )
    setup_dishka(container, app)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as queued_client:
        first = await queued_client.post(
            "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs",
            files={"source_dxe": ("exam.dxe", b"{}", "application/octet-stream")},
        )
        public_job_id = first.json()["public_job_id"]
        status = await queued_client.get(
            f"/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/{public_job_id}"
        )
        result = await queued_client.get(
            f"/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/{public_job_id}/result"
        )
        manifest = await queued_client.get(
            f"/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/{public_job_id}/artifacts"
        )
        download = await queued_client.get(
            "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs/"
            f"{public_job_id}/artifacts/examnet_pdf/download"
        )
        second = await queued_client.post(
            "/api/v1/public/apps/documents.conversion_hub/exam-converter/jobs",
            files={"source_dxe": ("another-exam.dxe", b"{}", "application/octet-stream")},
        )

    assert first.status_code == 200
    assert first.json()["status"] == "queued"
    assert status.status_code == 200
    assert status.json()["status"] == "queued"
    assert result.status_code == 200
    assert result.json()["status"] == "queued"
    assert result.json()["result"] is None
    assert result.json()["artifact_manifest_url"] is None
    assert manifest.status_code == 200
    assert manifest.json()["status"] == "queued"
    assert manifest.json()["artifacts"] == []
    assert download.status_code == 422
    assert download.json()["error"]["details"]["reason_code"] == (
        "public_exam_converter_artifact_not_ready"
    )
    assert second.status_code == 429
    assert second.json()["error"]["details"]["reason_code"] == (
        "public_exam_converter_concurrency_limited"
    )
