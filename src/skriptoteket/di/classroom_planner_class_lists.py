"""DI bindings for classroom planner class-list import.

Class-list document extraction, heuristic parsing, and the import preview
handler.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.application.curated_apps.classroom_planner.handlers.imports import (
    CreateClassListImportPreviewHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.classroom_planner.import_heuristics import (
    ClassListHeuristicParser,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner import (
    class_list_document_extractor as class_list_document_extractor_module,
)
from skriptoteket.protocols.classroom_planner_imports import (
    ClassListHeuristicParserProtocol,
    DocumentTextExtractorProtocol,
)
from skriptoteket.protocols.sir_convert_a_lot_v2 import SirConvertALotClientV2Protocol


class ClassroomPlannerClassListProvider(Provider):
    """Provide classroom planner class-list import bindings."""

    @provide(scope=Scope.APP)
    def class_list_document_extractor(
        self, settings: Settings, client: SirConvertALotClientV2Protocol
    ) -> DocumentTextExtractorProtocol:
        return class_list_document_extractor_module.ClassListDocumentExtractor(
            settings=settings,
            sir_convert=client,
        )

    @provide(scope=Scope.APP)
    def class_list_heuristic_parser(self) -> ClassListHeuristicParserProtocol:
        return ClassListHeuristicParser()

    @provide(scope=Scope.REQUEST)
    def create_class_list_import_preview_handler(
        self,
        extractor: DocumentTextExtractorProtocol,
        parser: ClassListHeuristicParserProtocol,
    ) -> CreateClassListImportPreviewHandler:
        return CreateClassListImportPreviewHandler(extractor=extractor, parser=parser)
