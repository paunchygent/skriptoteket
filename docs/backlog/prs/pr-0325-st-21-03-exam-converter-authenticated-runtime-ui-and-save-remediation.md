---
type: pr
id: PR-0325
title: "ST-21-03 Exam Converter authenticated runtime UI and save remediation"
status: ready
owners: "agents"
created: 2026-05-13
updated: 2026-05-15
stories:
  - "ST-21-03"
tags:
  - backend
  - frontend
  - authenticated
  - conversion-hub
  - sir-convert
  - huleedu
  - remediation
acceptance_criteria:
  - "Given `PR-0324` stopped because no authenticated Exam Converter product surface exists, when an authenticated teacher opens `documents.conversion_hub`, then a bespoke authenticated Exam Converter view loads instead of the generic Conversion Hub fallback."
  - "Given authenticated conversion work is user-originated, when the teacher submits a `.dxe` with optional sanitized result PDFs and target selection, then browser traffic uses the HuleEdu Gateway `/sir-convert/v2/convert/...` client with credentials, CSRF, idempotency, and correlation headers, and never exposes Sir Convert service credentials or direct upstream hosts."
  - "Given Sir Convert returns a DigiExam migration artifact bundle, when the teacher polls and opens results, then the UI can render result metadata, artifact manifest entries, named downloads, blocked/partial/manual-follow-up states, and `not_requested` targets using the same teacher-facing taxonomy as the approved public lane."
  - "Given the authenticated view is implemented, when UI content is introduced, then it follows `REF-exam-converter-ui-content-model-v1`: direct Swedish copy, progressive disclosure, no summary cards, no visible service jargon, dynamic imported-question indicators, low-friction question-level completion actions, per-slice mockup/proposal/product approval before implementation, test-code behavior specifications per UI slice, and no service-contract fields rendered as flat UI content."
  - "Given the teacher chooses to save a named artifact, when save-to-user-files succeeds, then Skriptoteket persists the downloaded Sir Convert artifact as an owner-scoped user file with bundle provenance and rejects unrelated-account access."
  - "Given this slice remediates the proof blocker, when it is done, then `PR-0324` can be rerun without relying on public fallback behavior or manual lower-level API calls."
---

# PR-0325: ST-21-03 Exam Converter Authenticated Runtime UI And Save Remediation

## Problem

`REV-PR-0324` found that the authenticated proof cannot run yet. The product has
an approved authenticated HuleEdu Gateway adapter package, but the authenticated
`documents.conversion_hub` host does not load an Exam Converter view, the
authenticated backend surface still models generic document conversion routes,
and there is no owner-scoped save-to-user-files path for downloaded Sir Convert
named artifacts.

Without this remediation, `PR-0324` would have to bypass the product surface or
skip the save proof, which would violate the story contract.

## Goal

Make the authenticated Exam Converter lane runnable enough for `PR-0324` to
prove it end to end:

- register a bespoke authenticated `documents.conversion_hub` Exam Converter
  host view;
- wire submit, poll, result, artifact manifest, and named download through the
  existing HuleEdu Gateway browser client;
- add the narrow server-side persistence surface needed to save downloaded Sir
  Convert named artifacts as owner-scoped user files with bundle provenance;
- preserve public-lane taxonomy compatibility for targets, artifact labels,
  blocked, partial, manual-follow-up, and `not_requested` states; and
- retain focused unit/frontend tests without rerunning the live proof inside
  this remediation slice.

## Dependencies

- Blocked proof review:
  `docs/backlog/reviews/review-pr-0324-exam-converter-authenticated-end-to-end-proof.md`
- Authenticated adapter package:
  `frontend/apps/skriptoteket/src/api/sirConvertGateway/`
- Public lane taxonomy/reference implementation:
  `frontend/apps/skriptoteket/src/views/apps/ExamConverterPublicView.vue`
- Current authenticated host registry:
  `frontend/apps/skriptoteket/src/views/curatedAppHostRegistry.ts`
- Current generic authenticated Conversion Hub API:
  `src/skriptoteket/web/api/v1/apps_conversion_hub.py`
- Current vault save command:
  `src/skriptoteket/application/scripting/vault.py`
- Klassrumskartan app-export save precedent:
  `src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_job_completion.py`,
  `src/skriptoteket/application/curated_apps/classroom_planner/handlers/grouping_export_job_completion.py`,
  `src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_job_support.py`,
  and
  `src/skriptoteket/web/api/v1/apps_classroom_planner_export_job_contracts.py`
- Exam Converter UI content model:
  `docs/reference/ref-exam-converter-ui-content-model-v1.md`
- Selected Exam Converter UI mockup:
  `docs/mockups/st-21-03-exam-converter-authenticated-progressive-review/README.md`
- Design-system rule and workspace doctrine:
  `.codex/rules/045-huleedu-design-system.md` and
  `docs/reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md`

## Non-goals

- Do not reopen the approved public grant/read-lease lane.
- Do not rerun the `PR-0324` live proof in this remediation slice.
- Do not add new Sir Convert targets, editable DOCX/QTI authoring, or bulk
  migration history.
- Do not expose Sir Convert service credentials, raw HuleEdu identity tokens,
  direct upstream hosts, or student-identifying evidence in browser code,
  retained docs, or tests.
- Do not refactor the whole generic Conversion Hub or Vault surface. Keep the
  persistence change narrow and owner-scoped for Sir Convert named artifacts.
- Do not use the generic run-artifact `SaveVaultFileCommand` as the primary
  shape for Sir Convert named artifacts when the Klassrumskartan app-export
  job finalizer pattern fits better.
- Do not make UI design or copy decisions from service field names. UI content
  must be structured through `REF-exam-converter-ui-content-model-v1` and an
  reviewed mockup before component implementation continues.
- Do not implement any Exam Converter UI area without first proposing that
  focused UI slice, including a mockup/sketch, behavior, components,
  affordances, recommendation rationale, and clarifying questions, then
  receiving explicit product-owner approval.
- Do not merge UI tests that only assert selectors or snapshots without
  describing the slice purpose, expected teacher-visible behavior, and
  recommended implementation shape in the test module.

## Implementation Plan

1. Freeze UI content and slice approval before further UI implementation:
   use `REF-exam-converter-ui-content-model-v1` to define visible copy,
   progressive disclosure, forbidden user-facing service jargon, and the split
   between result strip, compact files list, and expandable question list. Then
   follow the reference's UI Slice Approval Protocol: each UI area needs its
   own mockup/sketch, behavior discussion, component/affordance proposal,
   recommendation rationale, clarifying questions, and explicit product-owner
   approval before implementation. Use the selected mockup bundle as the
   whole-screen direction, but do not implement its rejected bottom `Visa filer`
   panel.
2. Add an authenticated Exam Converter host registration for
   `documents.conversion_hub` and implement a dedicated authenticated view or a
   thin authenticated adapter around shared Exam Converter presentation pieces.
3. Factor any reusable public/authenticated taxonomy rendering into small
   frontend modules if needed, keeping view modules under the repo's module
   size expectations and avoiding public/auth authority mixing.
4. Wire authenticated submit/status/result/manifest/named download actions to
   `frontend/apps/skriptoteket/src/api/sirConvertGateway/client.ts`.
5. Add a narrow save-to-user-files API/application path for downloaded Sir
   Convert named artifacts. It must bind the saved file to the authenticated
   owner, persist bundle provenance from `saveMetadata.ts`, and reject
   unrelated-account reads.
6. Use Klassrumskartan's export-job/Vault finalizer shape as the precedent:
   app-owned job/result DTOs expose `download_url` and `vault_artifact`;
   application finalizers enforce `VAULT_MAX_FILE_BYTES`,
   `VAULT_MAX_TOTAL_BYTES`, sanitized filenames, `VaultFileSourceKind.APP_EXPORT`,
   `VaultStorageProtocol` writes, usage updates, rollback of stored bytes on
   failure, and owner checks before download. Adapt that shape for Sir Convert
   artifact keys, bundle schema, checksum/content type, and correlation
   provenance instead of coupling to classroom draft/checkpoint concepts.
7. Keep web routers thin: request/response DTOs at the boundary, application
   handlers for orchestration, protocols for infrastructure boundaries, and
   Unit of Work ownership for persistence.
8. Add focused tests for host registration, authenticated client/UI states,
   missing-auth behavior, save success, and unrelated-account denial.
9. Update `PR-0325`, `ST-21-03`, `EPIC-21`, `docs/index.md`, and
   `.codex/handoff.md` with the completed remediation state, then hand back to
   `PR-0324` for live proof.

## Slice Status

### Slice 1: Authenticated Host Frame

Status: implemented after product approval.

Implemented:

- `ExamConverterAuthenticatedView` is now a composition-only authenticated
  host frame.
- `ExamConverterWorkflowRailShell` reserves the left workflow rail with
  token-colored structural step icons and no upload/submit behavior.
- `ExamConverterWorkspaceShell` reserves the dominant right workspace with a
  neutral placeholder and no result, file, question, report, or save behavior.
- `ExamConverterAuthenticatedView.spec.ts` documents the slice purpose,
  expected behavior, progressive-disclosure boundary, and recommended
  implementation shape in test code.

Out of scope for slice 1:

- upload controls;
- result strip;
- inspection tabs;
- question list;
- selected-question detail pane;
- files/report modes;
- runtime, Gateway, download, and save behavior.

### Slice 2: Source File Intake

Status: implemented after product approval and extended with local intake
affordances after product feedback.

Implemented:

- `ExamConverterAuthenticatedView` owns browser-local `.dxe` source-file state
  through a small local composable.
- `ExamConverterWorkspaceShell` exposes the working `.dxe` file input/drop zone
  and rejects non-`.dxe` files with direct Swedish copy.
- `ExamConverterWorkflowRailShell` reflects the selected source filename, size,
  uploaded status, and remove affordance.
- `ExamConverterWorkflowRailShell` exposes a separate optional
  `Valfritt rättat prov` PDF affordance with `Välj fil (.pdf)`, empty state,
  selected filename/size, remove affordance, and PDF-only rejection.
- `ExamConverterWorkspaceShell` now announces that a `.dxe` and optional
  corrected PDF can be dragged in together; the local intake composable places
  them in the correct slots and rejects multiple `.dxe` files with
  `Välj en provfil åt gången.`.
- Target output formats are local true/false choices in the rail. The choices
  remain a preview/declaration before review, not final download/save actions.
- The conversion CTA remains disabled because submit/runtime behavior belongs
  to the next slice.
- `ExamConverterAuthenticatedView.spec.ts` now covers selected-file state,
  invalid-file rejection, optional corrected PDF selection/removal, combined
  drop placement, multiple-`.dxe` rejection, target-format toggles, reset
  behavior, and the no-runtime boundary.

Out of scope for slice 2:

- submit/runtime calls;
- result strip;
- inspection tabs;
- question/file/report modes;
- download and save behavior.

### Slice 3: Conversion Start And Result Strip Scaffold

Status: implemented after product approval.

Implemented:

- `useExamConverterConversionState` owns local conversion phase state for the
  authenticated UI scaffold without importing Gateway, Sir Convert, or save
  clients.
- `ExamConverterWorkflowRailShell` enables `Starta konvertering` only when one
  `.dxe` is selected and at least one target format is selected.
- Starting conversion transitions the workspace to `Konverterar provet...` and
  locks local input/target affordances while the scaffold is running.
- Running conversion now uses a token-aligned progress visualization with
  stage text, percentage, segmented progress, and a long-running message after
  ten seconds. This remains local visual feedback until Sir Convert exposes
  real progress/ETA events.
- `ExamConverterResultStrip` renders the approved compact status strip copy for
  running, success, partial, and failed conversion states:
  `Konverterar provet...`, `Provet är konverterat`,
  `Konverteringen av provet lyckades delvis`, and
  `Konverteringen av provet misslyckades`.
- The authenticated host originally wired only the running state in this slice;
  terminal success, partial, and failed transitions are now connected by Slice
  4's runtime bridge.
- `ExamConverterAuthenticatedConversionSlice.spec.ts` covers start eligibility,
  running-state rendering, moving local progress, long-running copy, reset
  behavior, result-strip copy, no service jargon, and the
  no-question/file/report boundary.

Required upstream follow-up:

- If authenticated Exam Converter jobs can exceed ten seconds, Sir Convert must
  expose a governed progress/ETA contract for the DigiExam migration runtime
  path. Skriptoteket must consume that stream or polling field instead of
  treating browser-local progress as authoritative. The desired downstream
  shape is additive: current stage label, bounded percent or step index,
  optional ETA seconds, and stale/stalled/unknown semantics without leaking
  service internals into user-facing copy.

Out of scope for slice 3:

- Gateway submit calls;
- polling/result mapping;
- real upstream progress/ETA consumption;
- inspection tabs;
- question list and selected-question detail;
- files/report modes;
- download and save behavior.

### Slice 4: Authenticated Runtime Submit/Poll/Result Strip

Status: implemented after product approval.

Implemented:

- `useExamConverterAuthenticatedRuntime` is a focused authenticated runtime
  bridge for exactly one selected exam conversion.
- The bridge submits the selected `.dxe`, optional `Valfritt rättat prov` PDF,
  Swedish artifact language, selected target formats, and `wait_seconds=0`
  through the existing HuleEdu Gateway Sir Convert client.
- Target declarations are mapped narrowly:
  `PDF -> examnet_pdf` and `QTI-format -> qti_package`.
- Queued/submitted/processing jobs are polled through
  `getDigiExamMigrationJob` with the returned correlation ID until terminal
  status.
- Succeeded jobs read the terminal result through
  `getDigiExamMigrationResult`; failed/canceled jobs map to the approved
  failure strip copy.
- `useExamConverterConversionState` now accepts a terminal runtime outcome and
  maps complete, partial/manual-follow-up/warning, and blocked outcomes to the
  approved result-strip states without exposing service jargon.
- Partial result copy intentionally avoids inventing an exact question count
  until a later manifest/question slice consumes a governed count contract.
- `ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts` documents the slice
  purpose, expected teacher-visible behavior, recommended implementation shape,
  submit payload, polling correlation, partial result copy, and failure
  mapping.

Out of scope for slice 4:

- real upstream progress/ETA consumption;
- artifact manifest rendering;
- inspection tabs;
- question list and selected-question detail;
- generated file list;
- report mode;
- download and save behavior.

### Slice 5: IR-Backed Read-Only Review Shell

Status: implemented after product approval.

Implementation contract:

- Add the inspection mode surface as progressive disclosure:
  `Frågor`, `Filer`, and `Rapport`.
- Default to `Frågor` when the terminal result or migration manifest reports
  `manual_follow_up_required`, manual follow-ups, or warnings.
- Default to `Filer` only when no question review is required.
- Fetch and parse the read-only Sir Convert named artifacts that already exist
  for authenticated DigiExam jobs:
  `ir_json` (`digiexam-ir.json`) and `migration_manifest`
  (`migration-manifest.json`).
- Introduce `digiexamIrReviewParser.ts` as the boundary that validates the
  subset Skriptoteket needs and projects it into teacher-facing review rows.
  This boundary must not mutate the IR, create local reviewed state, or invent
  answer keys, points, alternatives, or review outcomes.
- Introduce `useExamConverterReviewArtifacts` or equivalent focused composable
  for manifest/artifact reads and loading/error state. It must call the
  existing Gateway artifact client with the runtime `jobId` and
  `correlationId`.
- Add `ExamConverterInspectionTabs` as a pure mode switch. Only one mode may
  render at a time.
- Add an initial `ExamConverterQuestionReviewShell` with a dense read-only
  question list and one selected-question detail pane/drawer. The detail pane
  may show only safe, contract-backed fields and teacher-facing warning/action
  copy.
- Add `ExamConverterFilesReadinessList` as readiness/status only. It must not
  render download/save actions in this slice and must not use a generic
  `Åtgärd` column.
- Add `ExamConverterReportSummary` as a lightweight diagnostic summary from the
  migration manifest. It should explain counts and provenance in teacher-facing
  Swedish and point the teacher back to `Frågor`.
- In `Frågor`, do not render success pills for expected imported information.
  Show only missing/actionable fields, and keep labels short under the `Saknas`
  column, for example `Facit` and `Poäng`. If the contract only proves manual
  follow-up without a specific missing field, do not invent a generic label.
  Let the status symbol mark the row and show the contract-backed explanation
  in the selected-question detail pane. Do not invent missing labels such as
  `Svarsalternativ` unless the conversion contract explicitly proves that
  alternatives were expected and absent.
- Use teacher-recognizable Swedish type labels. Do not use `Enval`; map
  one-correct-choice source items to `Flerval: ett val`,
  multiple-response items to `Flerval: flera val`, matching items to
  `Flerval: matchning` when the source contract explicitly proves matching
  structure, and gap-fill items to `Lucktext`.
- The selected-question detail pane must include source-backed alternatives
  for all flerval questions. Alternatives are required review data, not summary
  metadata. If alternatives are present but no source-proven correct marker is
  present, show missing `Facit`; do not imply that the alternatives themselves
  are missing.
- Render one `Fråga` table column containing the question number plus real
  prompt preview. Do not render a separate `Nr` column, and keep source item ids
  such as `item-001` in the selected-question detail pane only.
- Count only actual missing `Facit`/`Poäng` questions in the result-strip and
  inspection-header missing-data counts. `manual_answer_key_required` maps to
  `Facit`; missing `maxScore` maps to `Poäng`; `manual_marking_required` for
  `Fritext` is normal for this read-only slice and must not be counted as
  `saknar facit eller poäng`.
- In dense question rows, use approved lucide success/warning symbols for
  status instead of repeated text such as `Behöver ses över`.
- In read-only detail panes, do not explain implementation gaps or future
  editing support to the teacher. Show the question, present data, and missing
  fields only.
- In `Filer`, avoid internal staging language such as `beredskap`; file rows
  must state the visible outcome and the next useful teacher action.

Implementation notes:

- The authenticated runtime now accepts Sir Convert `running` as an active job
  state and accepts the actual v2 terminal-result envelope where `job_id` and
  `status` are top-level fields.
- A Sir Convert bundle marked `blocked` because question review is required is
  shown as `Konverteringen av provet lyckades delvis`, not as a failed
  conversion, when manual follow-up or warnings are present.
- Follow-up refinement: free-text `manual_marking_required` is treated as
  normal, while the missing-data headline counts only questions that actually
  lack `Facit` or `Poäng`. If Sir Convert reports the bundle as `partial`
  only because free-text items need normal teacher marking, the authenticated
  UI keeps the teacher-facing result as `Provet är konverterat`.
- Live validation against local Sir Convert and the HuleEdu Gateway edge passed
  for submit, terminal result, artifact manifest, `migration_manifest`, and
  `ir_json`.

Out of scope for slice 5:

- editing IR fields;
- local `markera som kontrollerad` state;
- mutation/rebuild of downstream PDF or QTI;
- download;
- save-to-files;
- LLM-inferred answer-key UX beyond displaying governed provenance if the
  artifact already contains it.

### Slice 6: Review Decision Gate And Files Actions

Status: partially implemented; live audit exposed an accepted-state export
contract gap before closeout.

Implementation contract:

- Add the review-decision gate that lets the teacher choose what happens when
  the conversion has actual missing `Facit` or `Poäng`.
- Use short action labels only:
  - `Granska` with an approved lucide review/inspection symbol.
  - `Godkänn` with an approved lucide check/confirm symbol.
- Do not use long action sentences as button copy. Put explanatory text in a
  dynamic help/info affordance, tooltip, or compact disclosure.
- Approved end-state help/info copy:
  - `Granska`: `Granska och redigera frågorna som saknar facit eller poäng.`
  - `Godkänn`: `Hoppa över granskningen och exportera provet direkt.`
- `Godkänn` accepts the current conversion state for export/save. It must not
  mutate Sir Convert IR, invent missing facit/poäng, or claim that questions
  have been fixed.
- File actions (`Hämta`, `Spara`) are available when either:
  - the projection has no actual missing `Facit`/`Poäng` and no blocking
    warning; or
  - the teacher has used `Godkänn` for the current conversion result.
- `Godkänn` must make the accepted current conversion exportable without
  claiming missing data has been fixed. It is not sufficient for Skriptoteket
  to set only a local acceptance flag when Sir Convert has pre-generated a
  blocked artifact manifest. If a requested file is blocked specifically
  because accepted missing `Facit`/`Poäng` prevents generation, this slice needs
  either a Sir Convert accepted-state export/rebuild contract or a Sir Convert
  best-effort output contract that emits available files with warnings.
- File rows still respect non-review blockers. If Sir Convert marks a requested
  file as blocked, failed, unsupported, or not created for a reason unrelated
  to accepted missing `Facit`/`Poäng`, `Hämta` and `Spara` stay disabled for
  that row and the row shows the visible outcome, for example
  `Kunde inte skapas`.
- Starting a new conversion, clearing selected files, or resetting local choices
  must clear the current-state acceptance.
- `Filer` remains the place for file actions. Do not add a generic mixed
  `Åtgärd` column that blends review, report, export, and save actions.
- The copy must describe the intended release end state, not a temporary
  intermediate development state.

Implementation notes:

- `ExamConverterReviewDecisionGate` renders the approved short actions:
  `Granska` and `Godkänn`. The approved long-form explanations live in
  affordance help (`title`) instead of visible button copy.
- `ExamConverterFilesReadinessList` now owns the `Hämta` and `Spara` columns.
  It does not render a generic `Åtgärd` column and does not mix review/report
  actions with export/save actions.
- `useExamConverterFileActions` keeps download/save state per Sir Convert
  artifact key, downloads named artifacts through the authenticated Gateway
  client, and saves downloaded artifacts through the owner-scoped
  save-to-user-files endpoint.
- `saveMetadata.ts` normalizes Sir Convert artifact checksums from
  `sha256:<hex>` into the 64-character SHA-256 value required by the
  Skriptoteket save boundary before the backend verifies content bytes.
- New conversions, source/supporting-file changes, and `Rensa val` clear the
  current-state acceptance and per-file action state.
- Focused frontend tests cover the decision-gate copy/affordance boundary,
  gated file actions, save-to-user-files wiring, and reset behavior. The
  Sir Convert Gateway client spec covers checksum normalization and the
  multipart save request shape.
- Live validation passed with local Sir Convert at `http://127.0.0.1:8085`:
  one DXE with an actual missing `Facit` showed the review gate, kept QTI
  `Hämta`/`Spara` disabled before `Godkänn`, enabled QTI after `Godkänn`,
  saved QTI to user files, and kept the upstream-blocked PDF row disabled.
  Screenshot retained locally at
  `.artifacts/pr-0325-live/slice-6-review-gate-files-save.png`.
- Follow-up live audit with a fresh byte-distinct copy of
  `1811577114-ekologiprov-v-49-25d-e.dxe` now proves the accepted-state
  end-state against rebuilt Sir Convert. Before `Godkänn`, both target rows are
  disabled. After `Godkänn`, Sir Convert returns `examnet_pdf` and
  `qti_package` as available; both rows show `Godkänt för export`; QTI saves to
  user files; and the generated PDF is retained locally at
  `.artifacts/pr-0325-live/fresh-examnet-import.pdf`.
- The fresh `target_readiness_report_v1` shows
  `ready_after_accepted_current_state` for `examnet_pdf` on items 1, 2, 3, and
  13 with reason `accepted_current_state_pdf_manual_unkeyed_profile`, and
  `ready_after_accepted_current_state` for `qti_package` on the same items with
  reason `accepted_current_state_manual_unkeyed_profile`.
- The same audit exposed a prerequisite review-projection flaw that belongs in
  this save/export slice: Skriptoteket currently cannot let the teacher make a
  meaningful `Godkänn` decision for flerval questions because the UI projection
  does not render the source-backed alternatives in the selected-question
  detail. Before an accepted-state export contract is implemented, the review
  projection must show alternatives for `Flerval: ett val`,
  `Flerval: flera val`, and governed matching items, while keeping correct
  answers absent unless Sir Convert proves them.
- For the audited ecology `.dxe`, Sir Convert classifies question 13 as
  `Lucktext` because the source carries DigiExam `type: 3`, `bodyHTML`
  `dxWordGap` spans, five `blanks`, and one embedded image reference. That
  classification is source-backed. The fresh accepted-state PDF render now
  preserves it as manual/free-text output with the embedded image and five gap
  placeholders; it must still not invent accepted values or claim fixed
  `Facit`.

Recommended solution retained for this slice:

- tighten the Skriptoteket review projection so question type labels follow the
  approved Swedish taxonomy and selected flerval details include alternatives;
- keep consuming Sir Convert's governed accepted-state export/readiness
  contract, preserving per-target and per-item blocker reasons instead of a
  stale local `Godkänn` flag;
- allow `Godkänn` to trigger or refresh accepted-state export only for target
  rows Sir Convert can actually create under the accepted-current-state policy;
  and
- keep unsupported target-shape blockers disabled with a visible outcome if a
  future source item still has no governed producer representation.

Out of scope for slice 6 until separately approved:

- broad IR mutation/rebuild workflow;
- group edit for points;
- batch answer-key editing;
- unrelated Vault redesign;
- public-lane save/persistence.

### Task 306 Sir Convert Contract Consumer Sync

Status: implemented after Sir Convert `Task 306` retained review.

Implemented:

- Regenerated Skriptoteket's checked-in Sir Convert OpenAPI consumer types from
  Sir Convert's `sir-convert-a-lot-v2.openapi.json` snapshot so
  `DigiExamEffectiveAnswerKeyLineageV1`,
  `DigiExamEffectiveAnswerKeyV1.lineage`, and
  `DigiExamIngestionOverlayItem.reviewed_completion_answer_key` are present in
  the authenticated Exam Converter type surface.
- Added a focused Gateway client contract fixture proving the Task 306
  reviewed-completion overlay field and effective-answer-key lineage field are
  accepted by the generated consumer types.
- Removed the obsolete terminal-result `target_availability` consumer
  expectation from handwritten Gateway types, parsers, and fixtures; target
  file state now stays with the artifact manifest/readiness artifacts.
- Replaced nearby hard-coded DigiExam schema-version literals in authenticated
  frontend fixtures with the existing centralized schema-version constants.
- Removed the production Tailwind Vite plugin from Vitest's jsdom config while
  leaving Tailwind in the real Vite dev/build config, so `fe-test` no longer
  loads `@tailwindcss/node` and no longer emits Node `DEP0205`.

Boundary:

- This pass does not add UI for reviewed advisory candidates.
- This pass does not apply reviewed candidates inside Skriptoteket.
- Sir Convert remains responsible for applying reviewed completions through the
  overlay into effective IR; Skriptoteket only keeps the consumer contract
  current.

Stop conditions for slice 6:

- Stop if the authenticated Gateway client cannot fetch `ir_json` or
  `migration_manifest` through owned artifact reads.
- Stop if the IR shape needed for question rows differs from the Sir Convert
  retained contract and would require guessing fields.
- Stop if a visible UI control would imply persisted review, corrected answers,
  regenerated exports, download readiness, or save readiness without a
  governed mutation/rebuild/export contract.

## Test Plan

- Focused frontend tests for authenticated host registration and Exam Converter
  view behavior.
- For each approved UI slice, include a focused frontend spec whose module
  header states the slice purpose, expected behavior, progressive-disclosure
  boundary, and recommended component/affordance shape before assertions.
- Focused frontend tests or mocks proving the HuleEdu Gateway client uses
  credentials, CSRF, idempotency, and correlation headers without forbidden
  browser authority strings.
- Focused backend tests for Sir Convert named-artifact save success,
  owner-scoped persistence, and unrelated-account denial.
- Focused backend tests mirroring the Klassrumskartan save guarantees:
  per-file limit, total Vault limit, sanitized display filename,
  `APP_EXPORT` source kind, storage cleanup on post-write failure, and
  owner-only download/read behavior.
- Missing-auth tests for authenticated submit/result/manifest/download/save
  surfaces touched by this remediation.
- Production bundle grep for `convert.hule.education`, `X-API-Key`,
  `SIR_CONVERT_A_LOT_V2_API_KEY`, `InternalIdentityContextV1`, direct Sir
  Convert upstream hosts, and local upstream dev ports.
- `pdm run lint`
- `pdm run typecheck`
- Focused backend tests for touched handlers/routes
- `pdm run fe-test` with touched specs
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Stop Conditions

- Stop if saving Sir Convert named artifacts requires weakening owner scope or
  exposing raw upstream authority to the browser.
- Stop if the authenticated lane can only pass by falling back to public
  routes, public handles, or anonymous public-grant behavior.
- Stop if the remediation requires a broad Vault/Conversion Hub rewrite instead
  of a narrow owner-scoped save path.
- Stop if artifact taxonomy differs from the approved public lane in a way that
  needs a product or contract decision.
- Stop if the UI design flattens service data into visible content, duplicates
  the same status across unrelated regions, introduces summary cards for
  question types or vanity metrics, or uses non-token colors/patterns.
- Stop if a UI area is about to be implemented without explicit approval of
  that focused UI slice's mockup, behavior, affordances, component choices, and
  recommendation rationale.
- Stop if a UI slice lacks test code that describes what the slice should do,
  the expected behavior it protects, and the recommended implementation form.

## Rollback Plan

Keep changes behind the authenticated `documents.conversion_hub` route and
server-side owner checks. If the remediation exposes a larger contract gap,
mark `PR-0325` blocked, retain a review finding, and do not rerun `PR-0324`
until the new blocker has its own governed slice.
