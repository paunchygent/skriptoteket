---
type: pr
id: PR-0325
title: "ST-21-03 Exam Converter authenticated runtime UI and save remediation"
status: ready
owners: "agents"
created: 2026-05-13
updated: 2026-05-14
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

Status: implemented after product approval.

Implemented:

- `ExamConverterAuthenticatedView` owns browser-local `.dxe` source-file state
  through a small local composable.
- `ExamConverterWorkspaceShell` exposes the working `.dxe` file input/drop zone
  and rejects non-`.dxe` files with direct Swedish copy.
- `ExamConverterWorkflowRailShell` reflects the selected source filename, size,
  uploaded status, and remove affordance.
- The conversion CTA remains disabled because submit/runtime behavior belongs
  to the next slice.
- `ExamConverterAuthenticatedView.spec.ts` now covers selected-file state,
  invalid-file rejection, removal back to idle, and the no-runtime boundary.

Out of scope for slice 2:

- result-PDF selection;
- submit/runtime calls;
- result strip;
- inspection tabs;
- question/file/report modes;
- download and save behavior.

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
