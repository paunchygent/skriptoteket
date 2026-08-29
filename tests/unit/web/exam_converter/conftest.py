from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.conversion_hub import ConversionHubJob
from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
)
from skriptoteket.application.curated_apps.exam_conversion import ExamConverterConversionLane
from skriptoteket.application.curated_apps.exam_conversion_producers import (
    InProcessExamConversionProducer,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
    DownloadConversionHubArtifactHandler,
    GetConversionHubJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_converter_conversions import (
    CreateExamConverterConversionJobsHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    CuratedAppUiMode,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_conversion_artifacts import (
    FilesystemExamConversionArtifactStore,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_conversion import ExamConversionArtifactStoreProtocol
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertALotClientV2Protocol,
    SirConvertArtifactOutcomeV2,
    SirConvertJobV2,
    SirConvertSubmitRequestV2,
    SirConvertSubmittedJobV2,
    SirConvertWebhookSubscriptionSummaryV2,
    SirConvertWebhookSubscriptionV2,
)
from skriptoteket.web.api.v1 import apps_conversion_hub as conversion_hub_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.profile_app_continuation_support import (
    ClockStub,
    IdGeneratorStub,
    ProfileContinuationApiProvider,
    ProfileRepositoryStub,
    UnitOfWorkStub,
    UserRepositoryStub,
    seed_huleedu_projection,
    signed_huleedu_headers,
)


class InMemoryConversionHubJobRepository:
    def __init__(self) -> None:
        self.jobs: dict[UUID, ConversionHubJob] = {}

    async def create(self, *, job: ConversionHubJob) -> ConversionHubJob:
        self.jobs[job.id] = job
        return job

    async def get_by_id(self, *, job_id: UUID) -> ConversionHubJob | None:
        return self.jobs.get(job_id)

    async def get_by_upstream_job_id(self, *, upstream_job_id: str) -> ConversionHubJob | None:
        for job in self.jobs.values():
            if job.upstream_job_id == upstream_job_id:
                return job
        return None

    async def update(self, *, job: ConversionHubJob) -> ConversionHubJob:
        self.jobs[job.id] = job
        return job


class RefusingSirConvertClient(SirConvertALotClientV2Protocol):
    """Fail loudly if the in-process lane ever reaches the Sir Convert client."""

    async def extract_text_direct(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        correlation_id: str | None = None,
    ) -> str:
        raise AssertionError("Sir Convert client must not be called.")

    async def submit_job(
        self,
        *,
        request: SirConvertSubmitRequestV2,
    ) -> SirConvertSubmittedJobV2:
        raise AssertionError("Sir Convert client must not be called.")

    async def get_job(self, job_id: str, *, correlation_id: str | None) -> SirConvertJobV2:
        raise AssertionError("Sir Convert client must not be called.")

    async def download_artifact(
        self, job_id: str, *, correlation_id: str | None
    ) -> SirConvertArtifactOutcomeV2:
        raise AssertionError("Sir Convert client must not be called.")

    async def download_named_artifact(
        self,
        job_id: str,
        artifact_key: str,
        *,
        correlation_id: str | None,
    ) -> SirConvertArtifactOutcomeV2:
        raise AssertionError("Sir Convert client must not be called.")

    async def create_webhook_subscription(
        self,
        *,
        callback_url: str,
        event_types: list[str],
        correlation_id: str | None,
    ) -> SirConvertWebhookSubscriptionV2:
        raise AssertionError("Sir Convert client must not be called.")

    async def list_webhook_subscriptions(
        self,
        *,
        correlation_id: str | None,
    ) -> list[SirConvertWebhookSubscriptionSummaryV2]:
        raise AssertionError("Sir Convert client must not be called.")

    async def delete_webhook_subscription(
        self,
        subscription_id: str,
        *,
        correlation_id: str | None,
    ) -> None:
        raise AssertionError("Sir Convert client must not be called.")


class RefusingEnrichmentJobRepository:
    """Enrichment-job repository stub for lanes where enrichment is disabled."""

    async def create(self, *, job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob:
        raise AssertionError("Enrichment jobs must not be created in this lane.")

    async def update(self, *, job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob:
        raise AssertionError("Enrichment jobs must not be updated in this lane.")

    async def get_by_id(self, *, job_id: UUID) -> ExamAnswerKeyEnrichmentJob | None:
        return None

    async def claim_next(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        return None


class _StubCuratedAppRegistry(CuratedAppRegistryProtocol):
    def __init__(self, *, app: CuratedAppDefinition) -> None:
        self._app = app

    def list_all(self) -> list[CuratedAppDefinition]:
        return [self._app]

    def get_by_app_id(self, *, app_id: str) -> CuratedAppDefinition | None:
        return self._app if self._app.app_id == app_id else None

    def get_by_tool_id(self, *, tool_id: UUID) -> CuratedAppDefinition | None:
        return self._app if self._app.tool_id == tool_id else None


class ExamConverterConversionsApiProvider(Provider):
    def __init__(
        self,
        *,
        curated_apps: CuratedAppRegistryProtocol,
        jobs: InMemoryConversionHubJobRepository,
        lane: ExamConverterConversionLane,
        artifacts: ExamConversionArtifactStoreProtocol,
        clock: ClockProtocol,
    ) -> None:
        super().__init__()
        self._curated_apps = curated_apps
        self._jobs = jobs
        self._lane = lane
        self._artifacts = artifacts
        self._app_clock = clock

    @provide(scope=Scope.APP)
    def curated_app_registry(self) -> CuratedAppRegistryProtocol:
        return self._curated_apps

    @provide(scope=Scope.REQUEST)
    def create_exam_converter_conversion_jobs_handler(
        self,
    ) -> CreateExamConverterConversionJobsHandler:
        return CreateExamConverterConversionJobsHandler(
            jobs=self._jobs,
            lane=self._lane,
            producer=InProcessExamConversionProducer(
                qti_writer=ExamNetQtiPackageWriter(),
                pdf_renderer=WeasyPrintExamNetPdfRenderer(),
            ),
            artifacts=self._artifacts,
            enrichment_jobs=RefusingEnrichmentJobRepository(),
            enrichment_enabled=False,
            uow=UnitOfWorkStub(),
            clock=self._app_clock,
            id_generator=IdGeneratorStub(),
        )

    @provide(scope=Scope.REQUEST)
    def get_conversion_hub_job_handler(self) -> GetConversionHubJobHandler:
        return GetConversionHubJobHandler(
            jobs=self._jobs,
            client=self._refusing_client(),
            uow=UnitOfWorkStub(),
            clock=self._app_clock,
        )

    @provide(scope=Scope.REQUEST)
    def download_conversion_hub_artifact_handler(self) -> DownloadConversionHubArtifactHandler:
        return DownloadConversionHubArtifactHandler(
            jobs=self._jobs,
            client=self._refusing_client(),
            exam_artifacts=self._artifacts,
            uow=UnitOfWorkStub(),
            clock=self._app_clock,
        )

    def _refusing_client(self) -> SirConvertALotClientV2Protocol:
        return RefusingSirConvertClient()


@pytest.fixture
def private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def settings(private_key: rsa.RSAPrivateKey) -> Settings:
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    settings = Settings()
    settings.HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY = public_key.decode("utf-8")
    return settings


@pytest.fixture
def clock(now: datetime) -> ClockProtocol:
    return ClockStub(now=now)


@pytest.fixture
def users() -> UserRepositoryStub:
    return UserRepositoryStub()


@pytest.fixture
def profiles() -> ProfileRepositoryStub:
    return ProfileRepositoryStub()


@pytest.fixture
def auth_user(
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    now: datetime,
) -> User:
    return seed_huleedu_projection(users=users, profiles=profiles, role=Role.USER, now=now)


@pytest.fixture
def auth_headers(
    private_key: rsa.RSAPrivateKey,
    clock: ClockProtocol,
    auth_user: User,
) -> dict[str, str]:
    del auth_user
    return signed_huleedu_headers(private_key=private_key, clock=clock)


@pytest.fixture
def curated_apps() -> CuratedAppRegistryProtocol:
    app = CuratedAppDefinition(
        app_id=conversion_hub_api.APP_ID,
        tool_id=curated_app_tool_id(app_id=conversion_hub_api.APP_ID),
        app_version="test",
        ui_mode=CuratedAppUiMode.BESPOKE_REQUIRED,
        title="Konverteringshubben",
        summary="Test registry entry.",
        min_role=Role.USER,
        placements=[CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt")],
    )
    return _StubCuratedAppRegistry(app=app)


@pytest.fixture
def jobs_repository() -> InMemoryConversionHubJobRepository:
    return InMemoryConversionHubJobRepository()


@pytest.fixture
def lane() -> ExamConverterConversionLane:
    return ExamConverterConversionLane(value="in_process")


@pytest.fixture
def artifact_store(tmp_path: Path) -> ExamConversionArtifactStoreProtocol:
    return FilesystemExamConversionArtifactStore(artifacts_root=tmp_path / "artifacts")


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockProtocol,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    curated_apps: CuratedAppRegistryProtocol,
    jobs_repository: InMemoryConversionHubJobRepository,
    lane: ExamConverterConversionLane,
    artifact_store: ExamConversionArtifactStoreProtocol,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(conversion_hub_api.router)

    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings,
            clock=clock,
            users=users,
            profiles=profiles,
        ),
        ExamConverterConversionsApiProvider(
            curated_apps=curated_apps,
            jobs=jobs_repository,
            lane=lane,
            artifacts=artifact_store,
            clock=clock,
        ),
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
