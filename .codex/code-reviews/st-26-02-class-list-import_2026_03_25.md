# Ruthless Review: ST-26-02 Class-list Import

## 0) Establish Scope and Governing Surface

### Files Changed
- `src/skriptoteket/application/curated_apps/classroom_planner/import_contracts.py` (New)
- `src/skriptoteket/protocols/classroom_planner_imports.py` (New)
- `src/skriptoteket/application/curated_apps/classroom_planner/handlers/imports.py` (New)
- `src/skriptoteket/domain/curated_apps/classroom_planner/import_heuristics.py` (New)
- `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/class_list_document_extractor.py` (New)
- `src/skriptoteket/protocols/sir_convert_a_lot_v2.py` (Modified)
- `src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/sir_convert_client_v2.py` (Modified)
- `src/skriptoteket/di/curated_apps.py` (Modified)
- `src/skriptoteket/web/api/v1/apps_classroom_planner.py` (Modified)
- `frontend/apps/skriptoteket/src/views/apps/useClassListImportFlow.ts` (New)
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerImportAction.vue` (New)
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerImportPreviewModal.vue` (New)
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRosterOverviewPanel.vue` (Modified)

### Public Surface Affected
- **HTTP Endpoints:**
  - `POST /api/v1/apps/classroom.group-seating-studio/rosters/import-preview` (New)
    - Multipart upload (`file`).
    - Returns `ClassListImportPreview` JSON.
- **Protocols:**
  - `SirConvertALotClientV2Protocol` gained `extract_text_direct`.
  - New `DocumentTextExtractorProtocol` and `ClassListHeuristicParserProtocol`.

### Compatibility Posture
- **Additive**: New endpoint and components do not affect existing roster or room flows.

## 1) Contract and Compatibility Checks
- Response model `ClassListImportPreview` is strictly typed and frozen.
- PDF extraction is delegated to Sir Convert-a-Lot v2 via a new direct text extraction contract, avoiding local engine bloat.

## 2) Architecture and Boundary Checks
- **Domain Purity**: `import_heuristics.py` contains pure Python logic with zero framework dependencies.
- **SRP**: Document extraction (infrastructure) is separated from name parsing (domain).
- **DI**: All dependencies are wired via `typing.Protocol` in Dishka; concrete `httpx.AsyncClient` usage was removed in favor of protocol-level extraction.

## 3) Correctness and Operational Safety
- **Defensive Parsing**: Heuristics categorize uncertain data into `ambiguous_rows` for manual teacher review.
- **Encoding Safety**: Infrastructure layer handles multiple text encodings with fallbacks.
- **Fail Closed**: API requires valid user session and CSRF token.

## 4) Typing Discipline
- **Zero Restricted Patterns**: All `cast`, `Any`, `any` (types), and `type: ignore` have been eliminated.
- **Strict TypeScript**: `useClassListImportFlow.ts` uses `unknown` and narrowing for error handling; components have fully typed emits.

## 5) Tests and Verification
- **Domain Unit Tests**: `tests/unit/domain/curated_apps/classroom_planner/test_import_heuristics.py` covers 5 scenarios (simple text, comma-separated, class detection, row parsing, accumulation).
- **Web API Unit Tests**: `tests/unit/web/test_apps_classroom_planner_imports.py` covers Auth, CSRF, and Success paths.

## Findings

### low: useClassListImportFlow.ts
- Type narrowing for Axios-like errors is functional but uses structural typing literals.
- Fix: Consider a shared `isApiError` guard if this pattern repeats across the SPA.

## Decision: `approved`
