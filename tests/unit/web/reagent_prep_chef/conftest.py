from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI

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
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.identity import CurrentUserProviderProtocol, SessionRepositoryProtocol
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
from skriptoteket.web.dishka_compat import setup_dishka
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.unit.web.reagent_prep_chef.test_support import (
    FixedClock,
    StubActorCommandHandler,
    StubActorHandler,
    StubCuratedAppRegistry,
    StubCurrentUserProvider,
    StubSdsStore,
    StubSessionRepository,
)


class ReagentPrepChefApiProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        clock: ClockProtocol,
        current_user_provider: CurrentUserProviderProtocol,
        sessions: SessionRepositoryProtocol,
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
        self._settings = settings
        self._clock = clock
        self._current_user_provider = current_user_provider
        self._sessions = sessions
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
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.APP)
    def clock(self) -> ClockProtocol:
        return self._clock

    @provide(scope=Scope.REQUEST)
    def current_user_provider(self) -> CurrentUserProviderProtocol:
        return self._current_user_provider

    @provide(scope=Scope.REQUEST)
    def sessions(self) -> SessionRepositoryProtocol:
        return self._sessions

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
def settings() -> Settings:
    return Settings()


@pytest.fixture
def clock(now: datetime) -> ClockProtocol:
    return FixedClock(now=now)


@pytest.fixture
def current_user_provider() -> StubCurrentUserProvider:
    return StubCurrentUserProvider()


@pytest.fixture
def sessions() -> StubSessionRepository:
    return StubSessionRepository()


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
    current_user_provider: CurrentUserProviderProtocol,
    sessions: SessionRepositoryProtocol,
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
        ReagentPrepChefApiProvider(
            settings=settings,
            clock=clock,
            current_user_provider=current_user_provider,
            sessions=sessions,
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
