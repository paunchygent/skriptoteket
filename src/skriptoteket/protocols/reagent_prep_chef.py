"""Protocols for the Reagent Prep Chef curated app.

These protocols define the DI seams between layers:
- application handlers (prep, defaults, risk assessment, exports)
- SDS corpus access and risk template retrieval
- PDF rendering and storage

Related:
  - `src/skriptoteket/application/curated_apps/reagent_prep_chef.py` (request/response models)
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/` (implementations)
"""

from __future__ import annotations

from typing import Protocol

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
from skriptoteket.domain.curated_apps.reagent_prep_chef.models import (
    HazardEntry,
    SdsCorpusEntry,
)
from skriptoteket.domain.curated_apps.reagent_prep_chef.risk_assessment import (
    RiskTemplates,
)
from skriptoteket.domain.identity.models import User


class ReagentPrepChefHazardStoreProtocol(Protocol):
    def lookup(self, *, formula_clean: str) -> HazardEntry | None: ...

    def list_all(self) -> list[HazardEntry]: ...


class ReagentPrepChefPdfRendererProtocol(Protocol):
    def render_html(self, *, html: str) -> bytes: ...


class ReagentPrepChefPrepHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: ReagentPrepChefPrepRequest,
    ) -> ReagentPrepChefPrepResult: ...


class ReagentPrepChefExportPdfHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: ReagentPrepChefPrepRequest,
    ) -> bytes: ...


class ReagentPrepChefChemicalsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
    ) -> ReagentPrepChefChemicalsResult: ...


class ReagentPrepChefGetDefaultsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
    ) -> ReagentPrepChefDefaultsResult: ...


class ReagentPrepChefUpdateDefaultsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: ReagentPrepChefUpdateDefaultsRequest,
    ) -> ReagentPrepChefDefaultsResult: ...


class ReagentPrepChefSavePdfHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: ReagentPrepChefSavePdfRequest,
    ) -> ReagentPrepChefSavePdfResult: ...


class ReagentPrepChefSaveDefaultsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: ReagentPrepChefSaveDefaultsRequest,
    ) -> ReagentPrepChefSaveDefaultsResult: ...


class ReagentPrepChefLoadDefaultsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: ReagentPrepChefLoadDefaultsRequest,
    ) -> ReagentPrepChefDefaultsResult: ...


class ReagentPrepChefRiskTemplateStoreProtocol(Protocol):
    def get(self) -> RiskTemplates: ...


class ReagentPrepChefRiskAssessmentHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: ReagentPrepChefRiskAssessmentRequest,
    ) -> ReagentPrepChefRiskAssessmentResult: ...


class ReagentPrepChefExportRiskPdfHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: ReagentPrepChefRiskAssessmentRequest,
    ) -> bytes: ...


class ReagentPrepChefSaveRiskPdfHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: ReagentPrepChefRiskAssessmentRequest,
    ) -> ReagentPrepChefSavePdfResult: ...


class ReagentPrepChefSdsStoreProtocol(Protocol):
    def get_entry(self, *, sds_ref: str) -> SdsCorpusEntry: ...

    def get_markdown(self, *, sds_ref: str) -> tuple[SdsCorpusEntry, str]: ...

    def get_pdf(self, *, sds_ref: str) -> tuple[str, bytes, str]: ...
