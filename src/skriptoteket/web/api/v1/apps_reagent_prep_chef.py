from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends
from fastapi.responses import Response

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
    ReagentPrepChefSdsMarkdownResult,
    ReagentPrepChefUpdateDefaultsRequest,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.identity.role_guards import require_at_least_role
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
from skriptoteket.web.auth.api_dependencies import require_csrf_token, require_user_api

APP_ID = "chemistry.reagent_prep_chef"

router = APIRouter(prefix=f"/api/v1/apps/{APP_ID}", tags=["apps"])


def _require_app_access(*, registry: CuratedAppRegistryProtocol, user: User) -> None:
    app = registry.get_by_app_id(app_id=APP_ID)
    if app is None:
        raise not_found("CuratedApp", APP_ID)
    require_at_least_role(user=user, role=app.min_role)


@router.get("/chemicals", response_model=ReagentPrepChefChemicalsResult)
@inject
async def list_chemicals(
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ReagentPrepChefChemicalsHandlerProtocol],
    user: User = Depends(require_user_api),
) -> ReagentPrepChefChemicalsResult:
    _require_app_access(registry=registry, user=user)
    return await handler.handle(actor=user)


@router.post("/prep", response_model=ReagentPrepChefPrepResult)
@inject
async def prep(
    command: ReagentPrepChefPrepRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ReagentPrepChefPrepHandlerProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> ReagentPrepChefPrepResult:
    _require_app_access(registry=registry, user=user)
    return await handler.handle(actor=user, command=command)


@router.post("/risk-assessment", response_model=ReagentPrepChefRiskAssessmentResult)
@inject
async def risk_assessment(
    command: ReagentPrepChefRiskAssessmentRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ReagentPrepChefRiskAssessmentHandlerProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> ReagentPrepChefRiskAssessmentResult:
    _require_app_access(registry=registry, user=user)
    return await handler.handle(actor=user, command=command)


@router.post("/export-pdf")
@inject
async def export_pdf(
    command: ReagentPrepChefPrepRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ReagentPrepChefExportPdfHandlerProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> Response:
    _require_app_access(registry=registry, user=user)
    pdf_bytes = await handler.handle(actor=user, command=command)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="reagensberedning.pdf"'},
    )


@router.post("/export-risk-pdf")
@inject
async def export_risk_pdf(
    command: ReagentPrepChefRiskAssessmentRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ReagentPrepChefExportRiskPdfHandlerProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> Response:
    _require_app_access(registry=registry, user=user)
    pdf_bytes = await handler.handle(actor=user, command=command)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="riskbedomning.pdf"'},
    )


@router.post("/save-pdf", response_model=ReagentPrepChefSavePdfResult)
@inject
async def save_pdf(
    command: ReagentPrepChefSavePdfRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ReagentPrepChefSavePdfHandlerProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> ReagentPrepChefSavePdfResult:
    _require_app_access(registry=registry, user=user)
    return await handler.handle(actor=user, command=command)


@router.post("/save-risk-pdf", response_model=ReagentPrepChefSavePdfResult)
@inject
async def save_risk_pdf(
    command: ReagentPrepChefRiskAssessmentRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ReagentPrepChefSaveRiskPdfHandlerProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> ReagentPrepChefSavePdfResult:
    _require_app_access(registry=registry, user=user)
    return await handler.handle(actor=user, command=command)


@router.post("/save-defaults", response_model=ReagentPrepChefSaveDefaultsResult)
@inject
async def save_defaults(
    command: ReagentPrepChefSaveDefaultsRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ReagentPrepChefSaveDefaultsHandlerProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> ReagentPrepChefSaveDefaultsResult:
    _require_app_access(registry=registry, user=user)
    return await handler.handle(actor=user, command=command)


@router.post("/load-defaults", response_model=ReagentPrepChefDefaultsResult)
@inject
async def load_defaults(
    command: ReagentPrepChefLoadDefaultsRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ReagentPrepChefLoadDefaultsHandlerProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> ReagentPrepChefDefaultsResult:
    _require_app_access(registry=registry, user=user)
    return await handler.handle(actor=user, command=command)


@router.get("/defaults", response_model=ReagentPrepChefDefaultsResult)
@inject
async def get_defaults(
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ReagentPrepChefGetDefaultsHandlerProtocol],
    user: User = Depends(require_user_api),
) -> ReagentPrepChefDefaultsResult:
    _require_app_access(registry=registry, user=user)
    return await handler.handle(actor=user)


@router.put("/defaults", response_model=ReagentPrepChefDefaultsResult)
@inject
async def update_defaults(
    command: ReagentPrepChefUpdateDefaultsRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ReagentPrepChefUpdateDefaultsHandlerProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> ReagentPrepChefDefaultsResult:
    _require_app_access(registry=registry, user=user)
    return await handler.handle(actor=user, command=command)


@router.get("/sds/{sds_ref}")
@inject
async def get_sds(
    sds_ref: str,
    registry: FromDishka[CuratedAppRegistryProtocol],
    store: FromDishka[ReagentPrepChefSdsStoreProtocol],
    user: User = Depends(require_user_api),
) -> Response:
    _require_app_access(registry=registry, user=user)
    filename, content, media_type = store.get_pdf(sds_ref=sds_ref)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/sds/{sds_ref}/markdown", response_model=ReagentPrepChefSdsMarkdownResult)
@inject
async def get_sds_markdown(
    sds_ref: str,
    registry: FromDishka[CuratedAppRegistryProtocol],
    store: FromDishka[ReagentPrepChefSdsStoreProtocol],
    user: User = Depends(require_user_api),
) -> ReagentPrepChefSdsMarkdownResult:
    _require_app_access(registry=registry, user=user)
    entry, markdown = store.get_markdown(sds_ref=sds_ref)
    return ReagentPrepChefSdsMarkdownResult(
        sds_ref=entry.sds_ref,
        provider=entry.provider,
        revision=entry.revision,
        markdown=markdown,
        pdf_available=True,
    )
