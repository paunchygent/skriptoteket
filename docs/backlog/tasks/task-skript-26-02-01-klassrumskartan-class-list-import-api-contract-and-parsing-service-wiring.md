---
type: task
id: TASK-SKRIPT-26-02-01
title: 'Klassrumskartan: class-list import API contract and parsing service wiring'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-26-02
task_kind: story
acceptance_criteria:
- Given a teacher wants to import a roster, when the frontend sends an `XLSX`, `TXT`,
  or `PDF` file, then a new `POST /api/v1/apps/classroom.group-seating-studio/rosters/import-preview`
  endpoint accepts the multipart upload and returns a synchronous JSON preview model
  without saving to the database.
- Given the uploaded file is a PDF, when the backend handles the request, then it
  delegates text extraction to the Sir Convert-a-Lot service via a synchronous API
  call, avoiding heavy PDF parsing libraries like `pdfplumber` in the Skriptoteket
  container.
- Given the import-preview endpoint processes the file content, when extraction completes,
  then it yields a typed `ClassListImportPreview` response containing the suggested
  class name, a list of successfully parsed students, and a list of ambiguous/unparseable
  rows for the teacher to review.
---

## Context
### Problem
Teachers need a way to import class lists from external files, but we cannot safely ingest files without a preview-and-confirm step. Furthermore, Skriptoteket must not take on the burden of heavy document parsing (like PDF text extraction), which is the responsibility of the Sir Convert-a-Lot platform service.

## Decision And Assumption Ledger
The source record did not define a separate section for this package heading.

## Story Contract Slice
### Goal
Establish the backend API contract for class-list import previews and wire up the synchronous text extraction delegation to Sir Convert-a-Lot for PDFs.
### Non-goals
- Implementing the complex heuristic parsing logic (regexes, name extraction) in this slice. This slice only provides the structural scaffolding, the typed Pydantic models, and the PDF delegation. The actual heuristic parser will be injected in the next PR.
- Building the frontend UI for the preview modal.
- Implementing the "confirm and save" endpoint.

## Contract Inputs
The source record did not define a separate section for this package heading.

## Plan
### Locked design decisions
- The import flow is strictly **preview-first**. The backend parses the file and returns a preview model; it does *not* create a roster entity in the database during this step.
- The new route is `POST /api/v1/apps/classroom.group-seating-studio/rosters/import-preview`.
- It accepts a `multipart/form-data` upload with a single `file` field.
- The response model (`ClassListImportPreview`) must clearly distinguish between cleanly parsed student records and ambiguous/error rows so the UI can force the teacher to review them.
- **PDF Delegation:** If the file is a PDF, the backend must make a synchronous HTTP request to Sir Convert-a-Lot's fast text extraction endpoint (to be defined/verified against the Sir Convert-a-Lot contract). We do not use `pdfplumber` or `pypdf` in the Skriptoteket `web` container.
- For `TXT` and `XLSX` (and CSV/TSV), the backend handles text decoding and cell extraction locally using lightweight tools (like `openpyxl` or standard library `csv`).
### Implementation plan
1. Define the Pydantic models in `src/skriptoteket/application/curated_apps/classroom_planner/import_contracts.py`:
   - `ParsedStudentRow` (full_name, given_name, family_name, row_number)
   - `AmbiguousRow` (raw_text, row_number, reason)
   - `ClassListImportPreview` (suggested_class_name, parsed_students, ambiguous_rows, file_name)
2. Create a generic `DocumentTextExtractorProtocol` in `src/skriptoteket/protocols/classroom_planner_imports.py` that takes a file stream and mime-type and returns raw text or tabular rows.
3. Implement `SirConvertPdfExtractor` that calls out to Sir Convert-a-Lot using `Settings.sir_convert_a_lot_v2_api_base_url`.
4. Implement a dummy `ClassListHeuristicParserProtocol` (to be fully implemented in PR-0134) that just returns empty lists for now.
5. Add the `POST /api/v1/apps/classroom.group-seating-studio/rosters/import-preview` route to `apps_classroom_planner.py`.
6. Add dependency injection wiring in `src/skriptoteket/di/curated_apps.py`.
### Test plan
- Unit test the API route to ensure it handles multipart uploads correctly and returns the `ClassListImportPreview` model.
- Unit test the `SirConvertPdfExtractor` adapter with `respx` or `httpx` mocking to ensure it constructs the request correctly and handles service failures gracefully.
- Verify DI wiring via Dishka.
### Rollback plan
- Remove the new endpoint, models, and protocols.

## Implementation Steps
The source record did not define a separate section for this package heading.

## Proof
The source record did not define a separate section for this package heading.

## Validation
The source record did not define a separate section for this package heading.

## Stop Conditions
The source record did not define a separate section for this package heading.

## Lessons Learned
The source record did not define a separate section for this package heading.

## Notes
The source record did not define a separate section for this package heading.

## Plan Document Review
The source record did not define a separate section for this package heading.

## Implementation Review
The source record did not define a separate section for this package heading.
