from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.reagent_prep_chef import (
    ReagentPrepChefChemicalsResult,
    ReagentPrepChefDefaultsResult,
    ReagentPrepChefLoadDefaultsRequest,
    ReagentPrepChefPrepRequest,
    ReagentPrepChefPrepResult,
    ReagentPrepChefRiskAssessmentRequest,
    ReagentPrepChefRiskAssessmentResult,
    ReagentPrepChefSaveDefaultsRequest,
    ReagentPrepChefSaveDefaultsResult,
    ReagentPrepChefSavePdfRequest,
    ReagentPrepChefSavePdfResult,
    ReagentPrepChefUpdateDefaultsRequest,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    CuratedAppUiMode,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.reagent_prep_chef import (
    ReagentPrepChefChemicalsHandlerProtocol,
    ReagentPrepChefExportPdfHandlerProtocol,
    ReagentPrepChefExportRiskPdfHandlerProtocol,
    ReagentPrepChefGetDefaultsHandlerProtocol,
    ReagentPrepChefLoadDefaultsHandlerProtocol,
    ReagentPrepChefPrepHandlerProtocol,
    ReagentPrepChefRiskAssessmentHandlerProtocol,
    ReagentPrepChefSaveDefaultsHandlerProtocol,
    ReagentPrepChefSavePdfHandlerProtocol,
    ReagentPrepChefSaveRiskPdfHandlerProtocol,
    ReagentPrepChefSdsStoreProtocol,
    ReagentPrepChefUpdateDefaultsHandlerProtocol,
)
from skriptoteket.web.api.v1 import apps_reagent_prep_chef as reagent_prep_chef_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.profile_app_continuation_support import (
    ProfileContinuationApiProvider,
    ProfileRepositoryStub,
    UserRepositoryStub,
    seed_huleedu_projection,
    signed_huleedu_headers,
)
from tests.unit.web.reagent_prep_chef.test_support import (
    FixedClock,
    StubActorCommandHandler,
    StubActorHandler,
    StubCuratedAppRegistry,
    StubSdsStore,
)


class ReagentPrepChefApiProvider(Provider):
    def __init__(
        self,
        *,
        curated_apps: CuratedAppRegistryProtocol,
        chemicals_handler: ReagentPrepChefChemicalsHandlerProtocol,
        prep_handler: ReagentPrepChefPrepHandlerProtocol,
        export_pdf_handler: ReagentPrepChefExportPdfHandlerProtocol,
        save_pdf_handler: ReagentPrepChefSavePdfHandlerProtocol,
        risk_assessment_handler: ReagentPrepChefRiskAssessmentHandlerProtocol,
        export_risk_pdf_handler: ReagentPrepChefExportRiskPdfHandlerProtocol,
        save_risk_pdf_handler: ReagentPrepChefSaveRiskPdfHandlerProtocol,
        sds_store: ReagentPrepChefSdsStoreProtocol,
        get_defaults_handler: ReagentPrepChefGetDefaultsHandlerProtocol,
        update_defaults_handler: ReagentPrepChefUpdateDefaultsHandlerProtocol,
        save_defaults_handler: ReagentPrepChefSaveDefaultsHandlerProtocol,
        load_defaults_handler: ReagentPrepChefLoadDefaultsHandlerProtocol,
    ) -> None:
        super().__init__()
        self._curated_apps = curated_apps
        self._chemicals_handler = chemicals_handler
        self._prep_handler = prep_handler
        self._export_pdf_handler = export_pdf_handler
        self._save_pdf_handler = save_pdf_handler
        self._risk_assessment_handler = risk_assessment_handler
        self._export_risk_pdf_handler = export_risk_pdf_handler
        self._save_risk_pdf_handler = save_risk_pdf_handler
        self._sds_store = sds_store
        self._get_defaults_handler = get_defaults_handler
        self._update_defaults_handler = update_defaults_handler
        self._save_defaults_handler = save_defaults_handler
        self._load_defaults_handler = load_defaults_handler

    @provide(scope=Scope.APP)
    def curated_app_registry(self) -> CuratedAppRegistryProtocol:
        return self._curated_apps

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_chemicals_handler(self) -> ReagentPrepChefChemicalsHandlerProtocol:
        return self._chemicals_handler

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_prep_handler(self) -> ReagentPrepChefPrepHandlerProtocol:
        return self._prep_handler

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_export_pdf_handler(self) -> ReagentPrepChefExportPdfHandlerProtocol:
        return self._export_pdf_handler

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_save_pdf_handler(self) -> ReagentPrepChefSavePdfHandlerProtocol:
        return self._save_pdf_handler

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_risk_assessment_handler(
        self,
    ) -> ReagentPrepChefRiskAssessmentHandlerProtocol:
        return self._risk_assessment_handler

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_export_risk_pdf_handler(
        self,
    ) -> ReagentPrepChefExportRiskPdfHandlerProtocol:
        return self._export_risk_pdf_handler

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_save_risk_pdf_handler(
        self,
    ) -> ReagentPrepChefSaveRiskPdfHandlerProtocol:
        return self._save_risk_pdf_handler

    @provide(scope=Scope.APP)
    def reagent_prep_chef_sds_store(self) -> ReagentPrepChefSdsStoreProtocol:
        return self._sds_store

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_get_defaults_handler(self) -> ReagentPrepChefGetDefaultsHandlerProtocol:
        return self._get_defaults_handler

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_update_defaults_handler(
        self,
    ) -> ReagentPrepChefUpdateDefaultsHandlerProtocol:
        return self._update_defaults_handler

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_save_defaults_handler(
        self,
    ) -> ReagentPrepChefSaveDefaultsHandlerProtocol:
        return self._save_defaults_handler

    @provide(scope=Scope.REQUEST)
    def reagent_prep_chef_load_defaults_handler(self) -> ReagentPrepChefLoadDefaultsHandlerProtocol:
        return self._load_defaults_handler


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
    return FixedClock(now=now)


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
        app_id=reagent_prep_chef_api.APP_ID,
        tool_id=curated_app_tool_id(app_id=reagent_prep_chef_api.APP_ID),
        app_version="test",
        ui_mode=CuratedAppUiMode.BESPOKE_REQUIRED,
        title="Reagensberedning",
        summary="Test registry entry.",
        min_role=Role.USER,
        placements=[CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt")],
    )
    return StubCuratedAppRegistry(app=app)


@pytest.fixture
def chemicals_handler() -> StubActorHandler[ReagentPrepChefChemicalsResult]:
    handler = StubActorHandler[ReagentPrepChefChemicalsResult]()
    handler.set_result(ReagentPrepChefChemicalsResult())
    return handler


@pytest.fixture
def prep_handler() -> StubActorCommandHandler[
    ReagentPrepChefPrepRequest, ReagentPrepChefPrepResult
]:
    return StubActorCommandHandler()


@pytest.fixture
def export_pdf_handler() -> StubActorCommandHandler[ReagentPrepChefPrepRequest, bytes]:
    return StubActorCommandHandler()


@pytest.fixture
def save_pdf_handler() -> StubActorCommandHandler[
    ReagentPrepChefSavePdfRequest, ReagentPrepChefSavePdfResult
]:
    return StubActorCommandHandler()


@pytest.fixture
def risk_assessment_handler() -> StubActorCommandHandler[
    ReagentPrepChefRiskAssessmentRequest, ReagentPrepChefRiskAssessmentResult
]:
    return StubActorCommandHandler()


@pytest.fixture
def export_risk_pdf_handler() -> StubActorCommandHandler[
    ReagentPrepChefRiskAssessmentRequest, bytes
]:
    return StubActorCommandHandler()


@pytest.fixture
def save_risk_pdf_handler() -> StubActorCommandHandler[
    ReagentPrepChefRiskAssessmentRequest, ReagentPrepChefSavePdfResult
]:
    return StubActorCommandHandler()


@pytest.fixture
def sds_store() -> StubSdsStore:
    return StubSdsStore()


@pytest.fixture
def get_defaults_handler() -> StubActorHandler[ReagentPrepChefDefaultsResult]:
    handler = StubActorHandler[ReagentPrepChefDefaultsResult]()
    handler.set_result(ReagentPrepChefDefaultsResult(defaults=None, state_rev=0))
    return handler


@pytest.fixture
def update_defaults_handler() -> StubActorCommandHandler[
    ReagentPrepChefUpdateDefaultsRequest, ReagentPrepChefDefaultsResult
]:
    return StubActorCommandHandler()


@pytest.fixture
def save_defaults_handler() -> StubActorCommandHandler[
    ReagentPrepChefSaveDefaultsRequest, ReagentPrepChefSaveDefaultsResult
]:
    return StubActorCommandHandler()


@pytest.fixture
def load_defaults_handler() -> StubActorCommandHandler[
    ReagentPrepChefLoadDefaultsRequest, ReagentPrepChefDefaultsResult
]:
    return StubActorCommandHandler()


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockProtocol,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    curated_apps: CuratedAppRegistryProtocol,
    chemicals_handler: ReagentPrepChefChemicalsHandlerProtocol,
    prep_handler: ReagentPrepChefPrepHandlerProtocol,
    export_pdf_handler: ReagentPrepChefExportPdfHandlerProtocol,
    save_pdf_handler: ReagentPrepChefSavePdfHandlerProtocol,
    risk_assessment_handler: ReagentPrepChefRiskAssessmentHandlerProtocol,
    export_risk_pdf_handler: ReagentPrepChefExportRiskPdfHandlerProtocol,
    save_risk_pdf_handler: ReagentPrepChefSaveRiskPdfHandlerProtocol,
    sds_store: ReagentPrepChefSdsStoreProtocol,
    get_defaults_handler: ReagentPrepChefGetDefaultsHandlerProtocol,
    update_defaults_handler: ReagentPrepChefUpdateDefaultsHandlerProtocol,
    save_defaults_handler: ReagentPrepChefSaveDefaultsHandlerProtocol,
    load_defaults_handler: ReagentPrepChefLoadDefaultsHandlerProtocol,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(reagent_prep_chef_api.router)

    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings,
            clock=clock,
            users=users,
            profiles=profiles,
        ),
        ReagentPrepChefApiProvider(
            curated_apps=curated_apps,
            chemicals_handler=chemicals_handler,
            prep_handler=prep_handler,
            export_pdf_handler=export_pdf_handler,
            save_pdf_handler=save_pdf_handler,
            risk_assessment_handler=risk_assessment_handler,
            export_risk_pdf_handler=export_risk_pdf_handler,
            save_risk_pdf_handler=save_risk_pdf_handler,
            sds_store=sds_store,
            get_defaults_handler=get_defaults_handler,
            update_defaults_handler=update_defaults_handler,
            save_defaults_handler=save_defaults_handler,
            load_defaults_handler=load_defaults_handler,
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
