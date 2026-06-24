---
type: pr
id: PR-0375
title: "ST-37-04 Document Converter backend-backed MVP planning"
status: done
owners: "agents"
created: 2026-06-23
updated: 2026-06-23
stories:
  - "ST-37-04"
tags:
  - planning
  - document-converter
  - sir-convert
dependencies:
  - "PR-0368"
  - "PR-0374"
  - "REF-current-product-lanes-and-sir-convert-boundary-v1"
  - "REF-app-presentation-decomposition-and-naming-plan-v1"
acceptance_criteria:
  - "Given Document Converter is an approved product lane but has no truthful runtime, when this planning slice closes, then it defines the backend-backed MVP contract before any route, host, registry capability, or runtime link is implemented."
  - "Given Sir Convert owns heavy format conversion, when the MVP is planned, then the plan inventories required Sir Convert routes, the single-result artifact contract, accepted inputs, output targets, polling, download, save, and replay semantics."
  - "Given Exam Converter and Audio Transcription now have separate identities, when Document Converter is planned, then the plan keeps document conversion separate from exam creation/migration and audio transcription workflows."
  - "Given auth-edge behavior is sensitive, when implementation follow-ups are proposed, then they preserve HuleEdu Gateway browser-session, CSRF, signed identity, route grants, server-side Sir key injection, polling, replay, and artifact-download proof requirements."
---

# PR-0375: ST-37-04 Document Converter Backend-Backed MVP Planning

## Problem

Document Converter is now a visible future product lane, but it still has no
truthful backend-backed workflow in Skriptoteket. `PR-0368` and `PR-0374`
removed the misleading combined Conversion Hub presentation for Exam Converter
and Audio Transcription, which leaves Document Converter correctly inert but
still unplanned as a runnable app.

Implementing a route or shell before the producer/backend contract is reviewed
would recreate the same facade problem this story is removing.

## Goal

Create a planning package for a real Document Converter MVP that defines the
minimum truthful backend, Sir Convert, authenticated shell, artifact, export,
and save contract before any product route or registry capability is activated.

## Non-goals

- No Document Converter route, alias, host, runtime link, public capability, or
  registry activation in this slice.
- No reuse of Exam Converter or Audio Transcription presentation as a document
  conversion facade.
- No backend/API decomposition unless the planning artifact proves a concrete
  contract need and creates a later reviewed implementation slice.
- No HuleEdu Gateway, Sir Convert authentication, browser-session, CSRF,
  signed-identity, or route-grant change.
- No browser-authored identity headers, direct cookies, credential POST
  shortcuts, host-only backend proof, browser-direct Sir Convert calls, or
  browser-held Sir Convert credentials.

## Review gate

`REV-PR-0375` must approve the planning package before any Document Converter
implementation slice is created.

## Follow-up correction

`PR-0380` supersedes the forward-looking one-file and Sir Convert-first
assumptions in this planning document for future Document Converter work.
`PR-0375` remains the accepted foundation for scoped backend ownership,
server-authoritative download/save, and no route activation before proof. Future
implementation should follow `PR-0380` for app-boundary simple conversion,
batch input, HTML/CSS project preview, and UI/copy gating.

## Current-state inventory

Skriptoteket already has a generic authenticated Sir Convert v2 integration
under the technical `documents.conversion_hub` app id:

- `GET /api/v1/apps/documents.conversion_hub/routes` lists generic PDF, DOCX,
  Markdown, and HTML conversion routes.
- `POST /api/v1/apps/documents.conversion_hub/jobs` accepts a constrained
  `ConversionHubJobSpecV2`, uploads one or more files, creates owner-scoped
  local `ConversionHubJob` rows, and submits `/v2/convert/jobs` to Sir Convert.
- `GET /api/v1/apps/documents.conversion_hub/jobs/{job_id}` refreshes and
  normalizes upstream status into Skriptoteket-owned job state.
- `GET /api/v1/apps/documents.conversion_hub/jobs/{job_id}/artifact` downloads
  the default Sir Convert artifact for a local owner-scoped job.

That surface is not yet a truthful Document Converter app. It is shared
technical runtime and still lacks a product-specific route, app identity,
single-result artifact contract, document-lane save semantics, replay/retry
semantics, and browser proof.

The only current authenticated save route is Exam Converter-specific:
`POST /api/v1/apps/documents.conversion_hub/exam-converter/artifacts/save`.
It stores browser-supplied artifact bytes plus producer metadata into Vault as
`APP_EXPORT`, validates size/hash metadata, and builds a source artifact id from
`documents.conversion_hub:{sir_convert_job_id}:{artifact_key}`. Document
Converter must not reuse that Exam-specific route or its bundle schema metadata
without a separate document-lane contract.

Existing producer contracts already show the boundary to preserve:

- Sir Convert owns conversion execution, source binding, artifact keys, artifact
  bytes, readiness, and producer evidence.
- HuleEdu Gateway owns protected browser session validation, CSRF, route grants,
  server-side Sir Convert credential injection, signed identity, and prefix
  stripping.
- Skriptoteket owns local owner-scoped job identity, route presentation,
  product state, Vault/Mina filer records, and user-visible recovery semantics.

## MVP contract

The Document Converter MVP is an authenticated-only product lane for teacher
document and presentation-format conversion. It should ship as a narrow wrapper
around generic Sir Convert v2 conversion, not as Exam Converter, Audio
Transcription, or a resurrected broad "Conversion Hub" app.

### Teacher workflow

1. Teacher opens a dedicated Document Converter route after login.
2. Teacher uploads one source file and chooses one supported target route:
   PDF to Markdown, PDF to DOCX, DOCX to Markdown, DOCX to PDF, Markdown to PDF,
   Markdown to DOCX, HTML to Markdown, HTML to PDF, or HTML to DOCX.
3. For PDF output, teacher may choose the existing constrained layout preset:
   paper size, orientation, and margins.
4. Skriptoteket creates an owner-scoped document-conversion job and submits the
   server-built Sir Convert job spec through the protected Gateway/Sir Convert
   edge.
5. The app shows submitted, queued, processing, succeeded, failed, or canceled
   state from the Skriptoteket job ledger; polling is against Skriptoteket, not
   the browser directly against Sir Convert.
6. When conversion succeeds, the app exposes the producer-authorized artifact
   for download and save to Mina filer.
7. The saved file becomes an owner-scoped Vault `APP_EXPORT` with source
   artifact metadata that proves which Sir Convert job and artifact produced it.
8. Retry/replay means a new Skriptoteket-owned submission using the same teacher
   selection and a new idempotency key unless a later accepted producer contract
   supplies safe artifact replay semantics.

### Accepted input and output scope

MVP routes are limited to the routes already mirrored by
`apps_conversion_hub.py`:

| Source | Targets | MVP notes |
|--------|---------|-----------|
| PDF | Markdown, DOCX | Uses existing Sir Convert PDF options; no exam extraction. |
| DOCX | Markdown, PDF | No template merge, comment import, or exam-state interpretation. |
| Markdown | PDF, DOCX | PDF layout uses the existing constrained preset only. |
| HTML | Markdown, PDF, DOCX | HTML/CSS to PDF is in scope only through server-built job specs; browser does not call Sir Convert. |

Out of scope for MVP: QTI, Exam.net packages, DigiExam imports, answer-key
enrichment, STT, diarization, transcript formatter bundles, arbitrary batch
jobs, public anonymous document conversion, template libraries, reference DOCX
styling, persistent job history views beyond the active result, and browser-held
producer credentials.

## Ownership split

| Area | Owner | Contract |
|------|-------|----------|
| Product route and app identity | Skriptoteket | A later route-visible slice may create `/apps/document-converter`; until then the lane stays inert. |
| Supported route catalog | Skriptoteket over Sir Convert mirror | The first implementation should expose only the approved MVP route set, not every upstream route. |
| Source upload validation | Skriptoteket web boundary | Validate declared route, extension/content type, size limits, and exactly one source file before producer submission. |
| Conversion execution | Sir Convert | `/v2/convert/jobs`, job status, default/named artifact bytes, upstream error taxonomy, source binding, and readiness evidence. |
| Auth edge | HuleEdu Gateway | Browser-session, CSRF, route grants, signed identity, and server-side Sir Convert credential injection remain unchanged. |
| Local job ledger | Skriptoteket backend | Owner-scoped job id, upstream job id, source filename, selected source/target route, status, error, correlation id, and timestamps. |
| Artifact download | Skriptoteket backend | Owner-scoped download by local job id; no browser-direct Sir Convert artifact URL. |
| Mina filer save | Skriptoteket backend | Server-owned save should fetch or verify producer artifact bytes and store a Vault `APP_EXPORT` record. |
| Replay/retry | Skriptoteket backend | New submission by default; no original-job fallback or guessed artifact key after failed or stale producer state. |
| UI shell | Skriptoteket frontend | Dedicated app surface for source, target, progress, result, download, save, retry, and failure recovery. |

### Artifact contract

The MVP freezes a single-result artifact contract:

- each document-conversion job has at most one teacher-facing result artifact;
- `GET job` exposes a `result_artifact` summary only after the local job is
  `succeeded`;
- `result_artifact` contains filename, content type, byte size if known, SHA-256
  if known, and a stable `source_artifact_id`;
- download and save endpoints are addressed by local `job_id` only;
- browser code never chooses, guesses, or submits an `artifact_key`;
- Skriptoteket maps the local job to Sir Convert's default converted artifact
  or to a producer-returned named artifact internally;
- future multi-artifact manifests, template bundles, and artifact selection need
  a separate reviewed slice before UI exposure.

The `source_artifact_id` namespace for saved MVP files is
`document-converter:{sir_convert_job_id}:converted_document` unless a later
accepted backend/API contract chooses a dedicated app id.

## Backend/API follow-up requirements

The first implementation slice must not activate a route before the backend
contract exists. It should create a document-lane API surface that can be tested
without pretending Exam Converter owns document artifacts.

The first backend slice must stay under the existing technical app id to avoid
bootstrap, catalog, or app-detail schema changes before a route-visible product
app exists. `PR-0369` stays blocked for this path.

Required API shape:

- `GET /api/v1/apps/documents.conversion_hub/document-converter/routes` returns
  only the MVP document routes.
- `POST /api/v1/apps/documents.conversion_hub/document-converter/jobs` creates
  one owner-scoped document-conversion job from one upload and one route
  selection.
- `GET /api/v1/apps/documents.conversion_hub/document-converter/jobs/{job_id}`
  polls local status and returns `result_artifact` only after success.
- `GET /api/v1/apps/documents.conversion_hub/document-converter/jobs/{job_id}/artifact`
  downloads the single producer-authorized result for the owner-scoped job.
- `POST /api/v1/apps/documents.conversion_hub/document-converter/jobs/{job_id}/artifact/save`
  saves the single producer-authorized result to Mina filer without
  browser-supplied bytes as the authority.

A later route-visible slice may introduce `/apps/document-converter` as the
frontend product route while still consuming the scoped
`documents.conversion_hub/document-converter` backend API. Only activate
`PR-0369` if that later slice proves a concrete need for bootstrap, catalog,
app-detail, generated app identity, or public-capability contract changes.

The save route should improve on the Exam Converter browser-upload save pattern:

- input is local `job_id` only;
- Skriptoteket confirms the job owner and terminal success;
- Skriptoteket downloads the default converted artifact through its server-side
  producer client or verifies a producer-signed single-artifact reference;
- Skriptoteket validates bytes, content type, filename, size, and hash if
  available;
- Skriptoteket stores the result as Vault `APP_EXPORT`;
- `source_artifact_id` uses
  `document-converter:{sir_convert_job_id}:converted_document`.

## Frontend follow-up requirements

A later route-visible slice may add the dedicated app route only after the
backend/API slice is reviewed. The frontend must then:

- link the authenticated-home Document Converter card to the real route;
- keep the sidebar utility-only and not duplicate app-card links;
- render a document-specific source/target/progress/result flow;
- poll Skriptoteket job status;
- use Skriptoteket download and save endpoints;
- avoid Exam Converter tabs, transcript copy, and generic Conversion Hub labels;
- prove small-screen behavior before activation.

## Red-first proof plan

### Backend/API slice

The first production slice is backend-only and should begin with failing tests
that prove the current false state:

1. Backend contract red: a focused test requests the scoped document route
   catalog and fails because no dedicated document-lane API exists.
2. Backend save red: a focused test tries to save a successful document
   conversion by local job id and fails because only the Exam Converter
   browser-upload save route exists.
3. Artifact red: a focused test expects `GET job` to expose a single
   `result_artifact` only after success and fails because the document artifact
   contract does not exist.
4. Frontend inertness red or guard check: the authenticated-home Document
   Converter card remains unlinked while the backend contract is added.

Backend/API green proof must include:

- backend unit tests for allowed routes, unsupported route rejection,
  owner-scoped job polling, single-result artifact summary, artifact download,
  save-to-Vault, quota rollback, stale/failed job rejection, and no cross-owner
  access;
- backend tests proving no browser-supplied `artifact_key` is accepted by MVP
  download/save routes;
- generated API type refresh if API schemas change;
- backend lint/typecheck and focused backend tests required by touched code;
- focused frontend/home test only if needed to prove the route remains inert;
- `pdm run docs-validate`, `pdm run handoff-validate` when handoff changes, and
  `git diff --check`.

### Route-visible slice

The later route-visible slice owns:

- frontend route/home red tests proving Document Converter still has no runnable
  app route;
- green tests for home link activation, route guard behavior, source and target
  selection, polling, download, save, retry, and failure state;
- `pdm run fe-type-check`, `pdm run fe-lint`, relevant focused Vitest, and
  docs/handoff validation;
- live shared-auth Docker plus Playwright proof through the HuleEdu browser
  session ceremony after the route-visible UI exists.

## Follow-up slice sequence

1. `PR-0375A` or successor: backend/API document-lane contract under
   `documents.conversion_hub/document-converter` with tests and generated type
   refresh. Keep frontend route inactive and `PR-0369` blocked.
2. Route-visible implementation slice: dedicated Document Converter app route,
   authenticated-home card activation, focused frontend tests, and shared-auth
   browser proof.
3. Save/replay hardening slice if the first backend slice cannot safely provide
   server-authoritative save and retry semantics without a larger producer
   artifact-reference contract.

Do not create any public Document Converter capability until a separate
abuse-control, TTL, rate-limit, artifact-retention, and anonymous-download
contract is reviewed.

## Stop conditions

- Stop if a proposed implementation links Document Converter to Exam Converter,
  Audio Transcription, the public Exam Converter route, or the generic
  compatibility host.
- Stop if document artifacts would be saved through the Exam Converter
  `bundle_schema_version` metadata contract.
- Stop if the browser would call Sir Convert directly, hold Sir Convert
  credentials, forge HuleEdu identity headers, bypass CSRF, or rely on
  direct-cookie/credential-POST proof.
- Stop if save-to-Mina-filer depends on browser-supplied artifact bytes without
  server-side producer authority or a reviewed signed-artifact reference.
- Stop if implementation needs bootstrap/catalog/API contract changes not named
  in its reviewed slice; activate `PR-0369` only for that concrete need.
- Stop if document conversion drifts into exam creation/migration,
  transcript/STT export, QTI/Exam.net packaging, or template libraries.

## Implementation plan

This planning slice stops at the contract above. Implementation is deferred to
reviewed follow-up slices after `REV-PR-0375`.

## Test plan

- Docs/planning validation:
  `pdm run docs-validate`.
- Handoff validation if `.codex/handoff.md` changes:
  `pdm run handoff-validate`.
- `git diff --check`.
- No production behavior tests are expected in this planning-only slice.

## Rollback plan

Remove the planning PR slice and keep Document Converter inert until a new
reviewed planning package is created.

## Planning closeout

Completed as a planning-only slice:

- Defined the Document Converter MVP as authenticated-only document and
  presentation-format conversion.
- Froze the first backend slice under
  `/api/v1/apps/documents.conversion_hub/document-converter/...`, keeping
  `PR-0369` blocked unless later route-visible work proves a concrete
  backend/API app-presentation contract need.
- Chose a single-result artifact contract: `GET job` exposes one
  `result_artifact` after success, while download and save use local `job_id`
  without browser-supplied artifact keys.
- Defined server-authoritative save-to-Mina-filer semantics and retry/replay as
  new submission by default.
- Split backend/API proof obligations from later route-visible proof.

Reviewed and approved by
[REV-PR-0375](../reviews/review-pr-0375-document-converter-backend-backed-mvp-planning.md).

Verified locally:

- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
