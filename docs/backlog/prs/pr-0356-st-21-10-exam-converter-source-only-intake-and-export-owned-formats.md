---
type: pr
id: PR-0356
title: "ST-21-10 Exam Converter source-only intake and export-owned formats"
status: done
owners: "agents"
created: 2026-06-15
updated: 2026-06-15
stories:
  - "ST-21-10"
tags:
  - frontend
  - backend
  - conversion-hub
  - exam-converter
  - ux
  - docs
dependencies:
  - "ST-21-03"
  - "ST-21-04"
  - "ST-21-09"
acceptance_criteria:
  - "Given the authenticated Exam Converter intake rail renders, when no conversion has started, then it shows one required source exam upload and no optional marked/result/supporting PDF upload surface."
  - "Given a teacher drops or selects files, when the files are handled locally, then only one governed source `.dxe` file can become the source selection; PDFs/DOCX/extra source files do not become supporting inputs or hidden request state."
  - "Given the teacher starts conversion, when Skriptoteket builds the Sir Convert request, then it uses the configured LLM answer-key suggestion mode, sends no `graded_result_pdf`/supporting-file part, and requests the currently supported target artifacts by default."
  - "Given target formats are export decisions, when intake renders before conversion, then PDF/QTI target buttons, checkbox-style target state, and nonfunctional question-mark icons are absent from the rail."
  - "Given files are available after conversion/replay, when the teacher opens `Filer`, then PDF and QTI remain available as download/save actions driven by artifact readiness; the UI does not imply that early target selection created files."
  - "Given the public one-time lane still exposes `graded_result_pdf` or target-selection request fields, when this PR is scoped, then it either removes the stale fields in the same slice or records a separate governed follow-up before closeout; the authenticated shell must not keep stale UI because public cleanup is larger."
  - "Given the UI changes are browser-visible, when the slice closes, then focused Vitest plus authenticated internal-browser fixture proof at desktop and compact workspace widths are recorded in `.codex/handoff.md`."
---

# PR-0356: ST-21-10 Exam Converter Source-Only Intake And Export-Owned Formats

## Problem

The current Exam Converter intake still has two pieces of stale product shape:

- a second optional upload for a marked/result PDF; and
- early target-format toggles for PDF and QTI.

Both create unnecessary teacher decisions before the conversion has produced a
reviewable test. The optional marked exam file has been superseded by the LLM
answer-key enrichment and teacher review/editor workflow. The target selection
is also premature: PDF, QTI, and future DOCX should be download/save choices in
`Filer` after conversion and review, not setup choices before the teacher knows
what they need.

There is also a visible affordance bug: the question-mark/help icon near the
target buttons looks like a tooltip trigger but does not open help.

## Goal

Make the active Exam Converter setup rail match the current product contract:

- one required source exam upload;
- no optional marked/result PDF upload;
- no visible early target-format selector;
- current supported targets requested by default for conversion/replay;
- PDF/QTI exposed as post-conversion file actions; and
- no orphaned help/question-mark affordance.

## Non-goals

- No DOCX output implementation in this PR.
- No PDF template redesign in this PR.
- No QTI editor, saved editable exam model, shared question pool, or tagging
  implementation in this PR.
- No new Sir Convert route or local conversion engine.
- No broad redesign of the Exam Converter workspace beyond the intake and file
  action contract needed by this slice.

## Implementation plan

1. Update `useExamConverterSourceFile` so the source-intake state owns only the
   required source file and default target set. Remove supporting-file state,
   supporting-file validation, and target toggle state from teacher-visible
   controls.
2. Update `ExamConverterWorkflowRailShell.vue` to remove the optional marked
   PDF section, remove the visible target buttons, renumber/simplify the rail,
   and remove or replace the nonfunctional help icon.
3. Update `ExamConverterWorkspaceShell` drop-zone copy and file-drop handling so
   PDFs/DOCX no longer become supporting inputs. Reject or ignore them with
   teacher-facing copy that names the visible next action.
4. Update `ExamConverterAuthenticatedView.vue` submit paths so
   `submitAndPoll` receives no `supportingFile`/`gradedResultPdf`, while the
   request still asks for currently supported artifacts by default.
5. Update Sir Convert Gateway request-context/client tests so no multipart
   `graded_result_pdf` part or idempotency digest component is produced for the
   active authenticated flow.
6. Audit the public one-time route and docs. If the stale public
   `graded_result_pdf`/`targets_json` contract can be removed safely in this PR,
   remove it with backend tests. If not, create the next governed follow-up and
   state why it is split.
7. Update `ref-exam-converter-ui-content-model-v1.md`, `ST-21-03`, `ST-21-10`,
   and `.codex/handoff.md` with the final scope and verification evidence.

## Progress

- Authenticated Exam Converter intake is now source-only in the local
  implementation: one governed `.dxe` selection, no optional marked/result PDF
  state, no visible target toggles, and no orphan help icons in the rail.
- Authenticated submit/retry now always use the configured LLM answer-key
  suggestion mode, request the current default target artifacts, and send no
  `graded_result_pdf` multipart field or digest input.
- Focused authenticated Vitest coverage now proves source-only drop/select
  behavior, absence of optional upload/target controls, default PDF/QTI
  post-conversion actions, and source-only request-context serialization.
- Invalid replacement attempts now preserve the current valid `.dxe` until the
  teacher supplies exactly one replacement `.dxe`; `.pdf`, `.docx`, and
  ambiguous multi-`.dxe` attempts no longer clear the active selection.

## Scope Clarifications

- Public one-time cleanup is intentionally split into
  `PR-0357`: `docs/backlog/prs/pr-0357-st-21-10-public-exam-converter-source-only-alignment.md`.
- Reason for the split: the public lane still carries the historical optional
  graded-result PDF and target-selection contract across
  `ExamConverterUploadPanel.vue`, `usePublicExamConverterRuntime.ts`,
  `examConverterPublicApi.ts`, and focused backend public-route/upstream-client
  tests. Expanding `PR-0356` to include that work would break the assigned
  authenticated-only implementation slice.

## Verification Notes

- Red-first evidence:
  `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts src/views/apps/ExamConverterAuthenticatedConversionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts src/api/sirConvertGateway/requestContext.spec.ts src/api/sirConvertGateway/completionContract.spec.ts`
  failed first with three expectation mismatches while the source-only slice was
  mid-edit, then passed after the authenticated source-only contract was fully
  wired.
- Focused invalid-replacement regression coverage:
  `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts`
  now passes with the added cases proving `.pdf`, `.docx`, and ambiguous
  multi-`.dxe` replacement attempts leave the original valid `.dxe` selected.
- Sanctioned authenticated fixture proof now passes through the HuleEdu
  browser-session ceremony:
  `pdm run python -m scripts.playwright_pr_0356_source_only_fixture_proof --base-url http://127.0.0.1:5173 --dotenv .env`
  retained
  `.artifacts/playwright-pr-0356-source-only-fixture-proof/20260614T233419Z/manifest.redacted.json`
  plus desktop/compact screenshots for
  `/apps/documents.conversion_hub/exam-converter/ui-fixtures/complete-qti-ready`
  and `/apps/documents.conversion_hub/exam-converter/ui-fixtures/missing-facit`.

## Red-first test plan

Start with focused tests that currently fail because the old UI is still
present:

- `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts`
  should fail until optional marked-PDF copy, supporting-file controls, and
  target toggles are removed from expected behavior.
- `pdm run fe-test -- --run src/api/sirConvertGateway/requestContext.spec.ts src/api/sirConvertGateway/client.spec.ts src/api/sirConvertGateway/completionContract.spec.ts`
  should fail until the active request path stops appending/digesting
  `graded_result_pdf`.
- If public cleanup is included:
  `pdm run test tests/unit/web/test_public_apps_exam_converter_runtime.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_public_exam_converter_upstream_clients.py`
  should fail first against the old public contract and pass after removal.

Then run closeout:

- `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedView.spec.ts src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterAuthenticatedUiInspectionFixtures.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- backend focused tests if public/backend request shape changes
- authenticated internal-browser proof via
  `/apps/documents.conversion_hub/exam-converter/ui-fixtures/complete-qti-ready`
  and `/apps/documents.conversion_hub/exam-converter/ui-fixtures/missing-facit`
  after the normal HuleEdu browser-session ceremony
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

Revert the intake/request-shape changes from this PR before release. Do not
restore the optional marked-PDF upload or target selector through compatibility
aliases unless a new accepted product contract explicitly reintroduces them.
