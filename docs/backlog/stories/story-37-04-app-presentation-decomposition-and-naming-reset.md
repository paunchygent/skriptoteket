---
type: story
id: ST-37-04
title: "App presentation decomposition and naming reset"
status: ready
owners: "agents"
created: 2026-06-17
updated: 2026-06-29
epic: "EPIC-37"
dependencies:
  - "ST-37-01"
  - "ST-37-02"
  - "PR-0361"
  - "REF-current-product-lanes-and-sir-convert-boundary-v1"
  - "REF-service-shell-ux-realignment-plan-v1"
  - "EPIC-21"
acceptance_criteria:
  - "Given generic Conversion Hub presentation hides distinct teacher jobs, when app presentation is decomposed, then exam conversion/editor work, audio transcription, and general document conversion have separate names, descriptions, and entry surfaces."
  - "Given Exam Converter is growing into a full app workflow, when its presentation identity is split from the compatibility host, then creation, import/migration, structure, item, point, answer-key, metadata editing, correction/replay, save, and export workflows are preserved as Exam Converter scope."
  - "Given presentation splitting touches protected Sir Convert flows, when route-visible app identities are implemented, then the HuleEdu Gateway authenticated edge remains the only supported protected proof path and is retained through shared-auth Docker/Playwright proof."
  - "Given Exam Converter is a native app lane after heavy source import, when future QTI/edit/share workflows are presented, then they are described as Skriptoteket-owned exam state rather than Sir Convert replay state."
  - "Given document conversion is a separate lane, when it is presented, then it focuses on format conversion and template-shaped output such as PDF, DOCX, HTML/CSS, and platform-ready presentation artifacts."
  - "Given route or app registry changes are implemented, when the slice closes, then docs, generated types where relevant, frontend tests, and live browser proof all reflect the new app presentation."
ui_impact: "Yes (curated app registry, app cards/entrypoints, descriptions, and possibly routes)."
---

# ST-37-04: App Presentation Decomposition And Naming Reset

## Context

The product has grown from a generic Conversion Hub into several use-case
specific application lanes. Teachers should not have to infer whether "the
converter" means exam migration, speech-to-text, or document-format conversion.

This story owns the app-presentation reset after the backlog inventory and
dashboard direction are settled.

## Planned PR Slices

- [x] [PR-0362: ST-37-04 app presentation decomposition and naming package](../prs/pr-0362-st-37-04-app-presentation-decomposition-and-naming-package.md)
- [x] [PR-0370: ST-37-04 public landing authenticated-app preview mockup approval](../prs/pr-0370-st-37-04-public-landing-authenticated-app-preview-mockup-approval.md)
- [x] [PR-0371: ST-37-04 public landing authenticated-app preview implementation](../prs/pr-0371-st-37-04-public-landing-authenticated-app-preview-implementation.md)
- [x] [PR-0372: ST-37-04 public landing header simplification](../prs/pr-0372-st-37-04-public-landing-header-simplification.md)
- [x] [PR-0366: ST-37-04 copy-only app lane naming and description alignment](../prs/pr-0366-st-37-04-copy-only-app-lane-naming-and-description-alignment.md)
- [x] [PR-0373: ST-37-04 public app local proof runtime contract](../prs/pr-0373-st-37-04-public-app-local-proof-runtime-contract.md)
- [x] [PR-0367: ST-37-04 curated app registry presentation alignment](../prs/pr-0367-st-37-04-curated-app-registry-presentation-alignment.md)
- [x] [PR-0368: ST-37-04 route-visible app entrypoint and presentation alignment](../prs/pr-0368-st-37-04-route-visible-app-entrypoint-and-presentation-alignment.md)
- [ ] [PR-0369: ST-37-04 backend and API app presentation contract alignment](../prs/pr-0369-st-37-04-backend-and-api-app-presentation-contract-alignment.md)
- [x] [PR-0374: ST-37-04 post-cutover conversion hub compatibility cleanup](../prs/pr-0374-st-37-04-post-cutover-conversion-hub-compatibility-cleanup.md)
- [x] [PR-0375: ST-37-04 Document Converter backend-backed MVP planning](../prs/pr-0375-st-37-04-document-converter-backend-backed-mvp-planning.md)
- [x] [PR-0376: ST-37-04 transcript proof lane orchestration](../prs/pr-0376-st-37-04-transcript-proof-lane-orchestration.md)
- [x] [PR-0377: ST-37-04 domain-named proof script surface cleanup](../prs/pr-0377-st-37-04-domain-named-proof-script-surface-cleanup.md)
- [x] [PR-0378: ST-37-04 transcript proof failure evidence capture](../prs/pr-0378-st-37-04-transcript-proof-failure-evidence-capture.md)
- [x] [PR-0379: ST-37-04 Document Converter backend API contract](../prs/pr-0379-st-37-04-document-converter-backend-api-contract.md)
- [x] [PR-0380: ST-37-04 Document Converter product contract correction](../prs/pr-0380-st-37-04-document-converter-product-contract-correction.md)
- [x] [PR-0381: ST-37-04 Document Converter local-heavy producer and batch contract](../prs/pr-0381-st-37-04-document-converter-local-heavy-producer-and-batch-contract.md)
- [x] [PR-0382: ST-37-04 Document Converter HTML/CSS project preview contract](../prs/pr-0382-st-37-04-document-converter-html-css-project-preview-contract.md)
- [x] [PR-0383: ST-37-04 Document Converter mockup and copy approval package](../prs/pr-0383-st-37-04-document-converter-mockup-and-copy-approval-package.md)
- [x] [PR-0384: ST-37-04 Document Converter route-visible MVP implementation](../prs/pr-0384-st-37-04-document-converter-route-visible-mvp-implementation.md)
- [x] [PR-0385: ST-37-04 Document Converter files and history follow-up](../prs/pr-0385-st-37-04-document-converter-files-and-history-follow-up.md)
- [x] [PR-0386: ST-37-04 Audio Transcription button token remediation](../prs/pr-0386-st-37-04-audio-transcription-button-token-remediation.md)
- [x] [PR-0387: ST-37-04 Document Converter small-screen mockup remediation](../prs/pr-0387-st-37-04-document-converter-small-screen-mockup-remediation.md)
- [x] [PR-0388: ST-37-04 Document Converter automatic preview and state-copy remediation](../prs/pr-0388-st-37-04-document-converter-automatic-preview-and-state-copy-remediation.md)
- [x] [PR-0398: ST-37-04 Document Converter production conversion and preview zoom remediation](../prs/pr-0398-st-37-04-document-converter-production-conversion-and-preview-zoom-remediation.md)
- [x] [PR-0399: ST-37-04 Sir Convert v2 status vocabulary contract](../prs/pr-0399-st-37-04-sir-convert-v2-status-vocabulary-contract.md)
- [x] [PR-0400: ST-37-04 Document Converter artifact content hygiene contract](../prs/pr-0400-st-37-04-document-converter-artifact-content-hygiene-contract.md)
- [x] [PR-0401: ST-37-04 Document Converter PDF image recovery planning](../prs/pr-0401-st-37-04-document-converter-pdf-image-recovery-planning.md)
- [x] [PR-0402: ST-37-04 Document Converter compact source-first layout](../prs/pr-0402-st-37-04-document-converter-compact-source-first-layout.md)
- [x] [PR-0403: ST-37-04 Document Converter preview touch-pinch ownership](../prs/pr-0403-st-37-04-document-converter-preview-touch-pinch-ownership.md)
- [x] [PR-0404: ST-37-04 Document Converter multi-source saved-file batches](../prs/pr-0404-st-37-04-document-converter-multi-source-saved-file-batches.md)
- [x] [PR-0405: ST-37-04 Document Converter column hierarchy and preview empty state](../prs/pr-0405-st-37-04-document-converter-column-hierarchy-and-preview-empty-state.md)
- [x] [PR-0407: ST-37-04 Audio Transcription retryable reattempt browser proof ownership](../prs/pr-0407-st-37-04-audio-transcription-reattempt-browser-proof-ownership.md)

## Notes

- The Exam Converter lane includes conversion, correction, future editing,
  sharing, QTI/source-neutral exam state, and later question-pool workflows.
- The Exam Converter shell must grow toward the full exam workflow: creation,
  import/migration, structure, item, point, answer-key, and metadata editing,
  correction/replay, save semantics, exports, sharing, QTI/source-neutral exam
  state, and later question-pool workflows.
- `PR-0368` must present Exam Converter and Audio Transcription as separate
  teacher-facing app identities, not tabs in one compatibility host, while
  reusing shared runtime shell/backend/auth machinery and retaining
  authenticated Sir Convert proof through the shared-auth Docker service lane
  and Playwright helpers.
- `PR-0374` removed the temporary
  `documents.conversion_hub?mode=...` presentation compatibility path after
  `PR-0368` proved the separate app identities. The shared
  `documents.conversion_hub` backend/runtime id remains only as technical
  authority under the canonical Exam Converter and Audio Transcription routes.
- Do not prove protected shell behavior through direct cookies, credential
  POSTs, host-only backend shortcuts, browser-authored identity headers, or
  browser-direct Sir Convert calls.
- The Document Converter lane is separate and should speak to format and
  presentation output, not test/exam workflows.
- `PR-0375` is done and approved by `REV-PR-0375`. It defines the
  authenticated-only Document Converter MVP as a scoped
  `documents.conversion_hub/document-converter` backend contract with
  single-result artifact, server-authoritative download/save, and retry/replay
  semantics before any route, host, registry capability, runtime link, or proof
  target is implemented.
- `PR-0376` is done and approved by `REV-PR-0376`. It owns the durable Audio
  Transcription live-proof lane launcher so
  local/downstream STT parity proof uses the fenced Sir Convert `remote-proof`
  lane through executable runtime validation rather than operator-selected
  port arguments.
- `PR-0377` is done and approved by `REV-PR-0377`. Active reusable proof
  scripts now use domain-named module, command, artifact, docstring, comment,
  metadata, and test surfaces instead of PR/task/ticket identifiers.
- `PR-0378` owns proof failure evidence capture and root-cause observability
  for `pdm run transcript-parity-proof remote-proof`. The earlier UI polling
  retry idea is deferred until retained evidence identifies an actual transient
  failure class.
- `PR-0407` is done and approved by `REV-PR-0407`. Sir Convert Task 371
  remains historical retained evidence; Skriptoteket now owns the domain-named
  browser, Gateway, and auth-helper proof mechanics for Audio Transcription
  retryable-failed reattempt proof.
- `PR-0379` is done and approved by `REV-PR-0379`. It adds the
  backend/API-only Document Converter contract under
  `documents.conversion_hub/document-converter`, keeps the frontend route
  inactive, and keeps `PR-0369` blocked.
- `PR-0380` is done. It corrects the next Document Converter product contract:
  simple lanes run inside the Skriptoteket app boundary, Sir Convert is
  reserved for automatically detected heavy/OCR/complex PDF paths, general
  batch input targets up to 10 source documents or project entries, HTML/CSS to
  PDF needs project input plus separate/combined output and 24-hour temporary
  PDF preview, and production UI remains blocked behind approved image mockups,
  HTML/CSS mockups, and copy lock.
- `PR-0381` is done and approved by `REV-PR-0381`. It records current local
  library evidence, centralizes existing PDF/rendering/extraction surfaces,
  expands the scoped backend contract to batch input and automatic local/heavy
  producer routing, and keeps the frontend route inactive.
- `PR-0382` through `PR-0384` are done and approved. They established the
  backend project-preview contract, approved the route-visible mockup/copy
  package, and activated `/apps/document-converter`.
- `PR-0386` is done and approved. It repaired Audio Transcription command
  buttons so normal actions use neutral compact surfaces while selector state
  remains visually distinct.
- `PR-0387` is done and approved. It remediated the route-inactive Document
  Converter small-screen mockup contract before production-route follow-up work.
- `PR-0388` is done and approved by `REV-PR-0388`. It removes
  implementation-detail preview copy and forbidden eyebrow/status labels, makes
  PDF preview automatic with stale-response protection, and keeps ordinary
  grid-heavy teacher HTML/CSS in scope through best-effort preview rendering.
- `PR-0385` is done and approved by `REV-PR-0385`. It adds owner-scoped
  `Mina filer` source selection and current route-session result continuity
  without promising durable job history or project-workspace restore.
- `PR-0398` and `PR-0399` are done and approved by `REV-PR-0398` and
  `REV-PR-0399`. Together they fixed the production conversion status defect,
  enforce typed Sir Convert v2 status vocabulary, keep Document Converter
  result state mode-scoped, and added the preview zoom/source-format inference
  remediation later tightened by `PR-0402` and `PR-0403`.
- `PR-0402` supersedes the temporary `PR-0398` compact ordering that placed
  conversion controls before upload. Source-format inference now lets compact
  `Filkonvertering` return to source/file picker first, then conversion
  controls, then preview. It is done and approved by `REV-PR-0402`.
- `PR-0403` is done and approved by `REV-PR-0403`. It remediates the Document
  Converter preview touch-pinch path using the `PR-0313` real-device lesson:
  native non-passive target binding, platform gesture events, anchored local
  zoom proof, centered fit geometry, and removal of the duplicated compact
  project summary panel.
- `PR-0400` is done and approved by `REV-PR-0400`. It removes generated
  missing-image placeholders from local HTML/CSS project previews and rejects
  known dirty terminal artifact markers before Document Converter download/save
  exposure instead of silently scrubbing upstream artifacts.
- `PR-0401` is done and approved by `REV-PR-0401`. It keeps PDF image
  recovery as an upstream Sir Convert manifest/real-byte recovery problem,
  links Sir Convert Task 272 as the prerequisite for recovered image artifacts,
  and keeps Skriptoteket fail-closed until a concrete recovery manifest and
  bytes exist.
- `PR-0404` is done and approved by `REV-PR-0404`. It deepens `PR-0385` by
  adding ordered multi-source `Mina filer` saved-file batches while keeping
  core `Mina filer`, combined output, and saved project/package restoration
  out of scope; retained shared-auth browser proof is present, the public
  saved-file contract exposes only ordered `source_refs`, and missing output
  filenames fail closed instead of exposing raw job ids.
- `PR-0405` owns the approved route-visible polish for Document Converter
  column hierarchy and preview empty state: stable `Källa` / `Konvertering` /
  `Resultat` headers across both modes, empty filename placeholder `filnamn`,
  and preview-shaped empty state labeled `Förhandsvisning`.
- The Audio Transcription lane is separate from document conversion even when
  downstream transcript exports are document-like artifacts.
- Use
  [REF-current-product-lanes-and-sir-convert-boundary-v1](../../reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md)
  as the ownership boundary before proposing names, descriptions, route impacts,
  or registry changes.
- `PR-0370` is a public landing mockup and copy-approval package only. It
  must finish image direction approval before any HTML/CSS mockup work, and
  must finish HTML/CSS plus Swedish copy approval before any production landing
  implementation slice begins.
- `PR-0371` implements the approved `PR-0370` public landing direction in
  production Vue, updates the public landing copy lock, and requires focused
  tests plus live public landing browser proof.
- `PR-0371` production runtime now removes the repeated signed-out
  `LandingFeaturedClassroom` showcase and replaces the retired generic
  authenticated ledger with the approved three-panel preview in
  `LandingAuthenticatedPreview.vue`; verification and retained review evidence
  are recorded in the PR slice, `.codex/handoff.md`, and approved
  `REV-PR-0371`.
- `PR-0372` is the follow-up public header simplification approved after the
  `PR-0371` landing direction: remove the redundant header `Klassrumskartan`
  link because the hero owns that CTA, and keep `Logga in` plus `Hjälp` as
  same-style single-row header actions on small screens. The runtime
  implementation now lives in
  `frontend/apps/skriptoteket/src/components/layout/LandingLayout.vue` with
  focused header coverage in
  `frontend/apps/skriptoteket/src/components/layout/LandingLayout.spec.ts`
  and retained in-app-browser desktop/mobile proof from `http://localhost:5173/`.
- `PR-0366` is done as of 2026-06-20. It aligned copy-only route-visible
  app-lane wording across authenticated home cards, the authenticated
  prov/transcript mode switch, the authenticated host frame label, and the
  public Exam Converter eyebrow without changing routes, app ids, registry
  metadata, or backend/API contracts.
- `PR-0373` is done as of 2026-06-20. It hardened the local proof lane from
  `PR-0366`: host Vite public-app proof now has explicit `dev-stack web-start`
  and `fe-dev-shared-auth` commands, while Docker frontend explicitly keeps
  public `/api/v1/public/...` proxy traffic on the Skriptoteket backend and
  protected `/api` on the HuleEdu Gateway.
- `PR-0361` closed the service-shell planning package through
  [REF-service-shell-ux-realignment-plan-v1](../../reference/ref-service-shell-ux-realignment-plan-v1.md),
  and `PR-0362` closed the naming/decomposition planning package through
  [REF-app-presentation-decomposition-and-naming-plan-v1](../../reference/ref-app-presentation-decomposition-and-naming-plan-v1.md).
  `ST-37-04` remains open for `PR-0404` and only later concrete backend/API
  app-presentation needs; keep `PR-0369` blocked until such a need is proven.
