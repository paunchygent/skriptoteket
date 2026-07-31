---
type: epic
id: EPIC-SKRIPT-21
title: 'Curated app: Conversion Hub (Sir Convert-a-Lot v2)'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
outcome: Skriptoteket provides first-class conversion hub and exam-converter UI lanes
  that route supported conversions through Sir Convert-a-Lot v2, with no production
  dependence on the legacy html-to-pdf-preview tool script.
retired_ids:
- EPIC-21
---

## Scope
- Add a **Conversion Hub** curated app (bespoke-required) that exposes a complete UI for the set of
  conversions supported by Sir Convert-a-Lot v2.
- Add an Exam Converter product lane under Conversion Hub for teacher-facing
  DigiExam/Exam.net migration workflows, split into public one-time conversion
  and authenticated owner-scoped artifact workflows.
- Add an authenticated transcript product lane under Conversion Hub for
  Sir Convert-backed speech-to-text jobs, diarization controls, Gateway-backed
  transcript job lifecycle, Skriptoteket-owned durable transcript saves,
  progress/cancel parity, speaker overlays, and producer-owned formatter
  exports.
- Keep live proof compatible with Sir Convert's hosted model/runtime estate by
  enforcing coherent HuleEdu Gateway/Sir Convert internal identity trust lanes
  before upload or producer job creation.
- Support batch conversions (multiple files) and a single-PDF preview UX through
  a Skriptoteket-owned local job ledger and download boundary rather than raw
  upstream job ids. For the newer teacher-facing Document Converter lane,
  `PR-0380` narrows this: simple lanes run inside the Skriptoteket app boundary
  and Sir Convert is reserved for heavy/OCR/complex PDF paths.
- Surface v2 PDF layout presets (for example A5/A4/A3 and portrait/landscape) in the UI for relevant
  outputs.
- Migrate tests and remove production reliance on `html-to-pdf-preview`.
- Define the same-host Sir Convert transport shape explicitly: Unix socket preferred, `127.0.0.1`
  HTTP fallback, no internal HTTPS default between co-located services.
### Out of scope
- No new conversion engines inside Skriptoteket for historical generic
  Conversion Hub work. This is superseded for the teacher-facing Document
  Converter lane by `PR-0380`, which allows researched in-app simple conversion
  paths while preserving Sir Convert for heavy/OCR/complex PDF work.
- No partial/legacy shims for `html-to-pdf-preview` once the curated app exists: callers/tests are
  updated to the new surface.
- No redirect-based artifact delivery that bypasses Skriptoteket ownership checks for Conversion Hub
  downloads.
- No general public anonymous conversion upload route may ship outside the
  accepted `ADR-0085` scoped public capability contract for the bounded Exam
  Converter exception.
- No public anonymous speech-to-text lane, no direct Sir Convert browser
  traffic, and no Skriptoteket-owned STT/diarization runtime.
### Dependencies
- ADR-0066 (this epic's conversion strategy decision)
- Current product lanes and Sir Convert/Skriptoteket ownership boundary:
  [REF-current-product-lanes-and-sir-convert-boundary-v1](../../reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md)
- Existing curated apps platform: ADR-0022, ADR-0023, ADR-0024
- Public curated-app access and abuse-control authority: ADR-0079, ADR-0085,
  ST-32-03
- HuleEdu authenticated Sir Convert edge:
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-07-expose-sir-convert-artifact-bundle-routes-through-huleedu-auth-edge.md`
- Sir Convert artifact-bundle contract:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/converters/digiexam-migration-service-api-artifact-contract.md`
- Sir Convert speech-to-text authority:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
  and
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md`
- HuleEdu audio transcription Gateway story:
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-08-expose-sir-convert-audio-transcription-jobs-through-huleedu-auth-edge.md`
- HuleEdu transcript formatter replay Gateway story:
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-09-expose-transcript-formatter-replay-through-sir-convert-auth-edge.md`
- Sir Convert transcript overlay replay story:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/stories/story-56-transcript-speaker-overlay-formatter-replay-over-canonical-json.md`
- Sir Convert compact answer-key review-state production proof story:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/stories/story-57-cross-repo-compact-answer-key-review-state-production-proof.md`

## Epic Contract
The source record did not define a separate section for this package heading.

## ADR Coverage
The source record did not define a separate section for this package heading.

## Contract Inputs
The source record did not define a separate section for this package heading.

## Stories
### Stories (ordered)
- [ ] 1. [ST-21-01: Curated app: Conversion Hub (v1)](../stories/story-21-01-curated-app-conversion-hub-v1.md)
- [ ] 2. [ST-21-02: Migration: retire html-to-pdf-preview + update tests](../stories/story-21-02-migrate-off-html-to-pdf-preview-and-retire-tool.md)
- [ ] 3. [ST-21-03: Exam converter public and authenticated artifact lanes](../stories/story-21-03-exam-converter-public-and-authenticated-artifact-lanes.md)
- [ ] 4. [ST-21-04: Exam Converter durable teacher correction sessions](../stories/story-21-04-exam-converter-durable-teacher-correction-sessions.md)
- [x] 5. [ST-21-05: Conversion Hub transcript intake and diarization controls](../stories/story-21-05-conversion-hub-transcript-intake-and-diarization-controls.md)
- [x] 6. [ST-21-06: Transcript job lifecycle through HuleEdu Gateway](../stories/story-21-06-transcript-job-lifecycle-through-huleedu-gateway.md)
- [x] 7. [ST-21-07: Durable transcript saves and JSON-first downstream formatting](../stories/story-21-07-durable-transcript-saves-and-json-first-downstream-formatting.md)
- [x] 8. [ST-21-08: Transcript speaker overlays and replay formatter exports](../stories/story-21-08-transcript-speaker-overlays-and-replay-formatter-exports.md)
- [x] 9. [ST-21-09: Conversion Hub remote inference proof trust lane](../stories/story-21-09-conversion-hub-remote-inference-proof-trust-lane.md)
- [ ] 10. [ST-21-10: Exam Converter source-only intake and export-owned formats](../stories/story-21-10-exam-converter-source-only-intake-and-export-owned-formats.md)
- [x] 11. [ST-21-11: Cross-repo compact answer-key review state production proof](../stories/story-21-11-cross-repo-compact-answer-key-review-state-production-proof.md)

## Epic Verification Plan
The source record did not define a separate section for this package heading.

## Exceptions And Follow-Ups
The source record did not define a separate section for this package heading.

## Risks
- External dependency risk (Sir Convert-a-Lot availability/latency):
  mitigate with timeouts, clear UI progress, and deterministic error surfaces.
- Ownership/auth drift if the product keeps treating upstream job ids as the visible boundary:
  mitigate by adding the local job ledger before the bespoke SPA adopts the current passthrough
  contract.
- Artifact naming / vault integration drift:
  mitigate by asserting on "PDF exists and is valid" rather than hardcoded filenames in E2E.
- Public upload and compute abuse:
  mitigate by reusing the dedicated public namespace, rate-limit, payload-cap,
  MIME/type-validation, reason-code, TTL, and no-Vault rules from the accepted
  public curated-app boundary before opening the Exam Converter lane.
- Over-scoping in one PR:
  mitigate via PR-sized tasks with strict ordering (PR-0063..).
- Remote proof trust-lane drift:
  mitigate with a default preflight that verifies signer/verifier profile
  coherence before upload or producer job creation while keeping heavy hosted
  model/runtime work on remote Sir Convert compute.

## Notes
### Implementation Summary (as of 2026-05-13)
- PR-0063 (docs planning scaffold): done
- PR-0064 (backend v2 client + curated app API surface): done
- PR-0148 (local job ledger + owned status/download boundary): done
- PR-0065 (SPA bespoke UI): pending after the local-ledger boundary lands
- PR-0066 (migrate tests + retire html-to-pdf-preview): pending
- ST-21-03 (Exam Converter public/authenticated lanes): in progress; `ADR-0085`
  accepts the bounded public Exam Converter exception, and PR-0319 now freezes
  the scoped public-capability registry/profile and route contract before
  public runtime conversion ships.
- PR-0318 (authenticated Exam Converter HuleEdu Sir Convert edge adapter):
  done and approved by retained review `REV-PR-0318`; browser adapter package
  now uses `/sir-convert/v2/convert/...` with deterministic
  idempotency/correlation, named artifact reads, save-to-user-files metadata
  mapping, Gateway base-URL fail-closed validation, a dedicated local Gateway
  proxy target, and stricter blocked-artifact parser semantics.
- PR-0319 (public Exam Converter profile and route-contract freeze): done;
  `documents.conversion_hub` remains app-wide `authenticated_only`, exposes
  only `public_capabilities: [{ scope: "exam_converter", profile:
  "public_browser_runtime" }]`, freezes
  `/public/apps/documents.conversion_hub/exam-converter` and
  `/api/v1/public/apps/documents.conversion_hub/exam-converter`, and ships no
  public runtime conversion behavior. Retained review `REV-PR-0319` is
  approved.
- PR-0321 (public active-runtime metadata and grant contract): done and approved
  by `REV-PR-0321`; `documents.conversion_hub` remains app-wide
  `authenticated_only`, while scoped `exam_converter` metadata can distinguish
  `contract_only`, `grant_contract_ready`, and `active`, with disabled
  grant-ready action affordances and opaque-handle authority boundaries.
- PR-0320 (public Exam Converter one-time runtime lane): done; implemented the
  backend/runtime public lane plus minimal host wiring behind the
  PR-0319/PR-0321 metadata contract, with transient upload/job/artifact state,
  anonymous abuse controls on each public action, cookie parity, direct
  downloads, no Vault/MyFiles writes, and no browser direct-service
  credentials. Live upstream public-grant proof remains in the end-to-end proof
  slice.
- PR-0322 (live upstream public grant proof): done and approved by
  `REV-PR-0322` after Sir Convert `TASK-292` and Skriptoteket `PR-0323`
  remediated the grant/read-lease contract drift. The approved proof retained
  sanitized positive submit/status/result/manifest/download evidence, cookie
  parity, negative abuse-control probes, TTL-expiry rejection, no-account-
  persistence evidence, and forbidden browser-authority grep results across
  local live HuleEdu Gateway, Sir Convert, and Skriptoteket services.
- PR-0324 (authenticated Exam Converter end-to-end proof): blocked by
  `REV-PR-0324`; proof preflight found no authenticated bespoke Exam Converter
  host surface, no authenticated DigiExam artifact-bundle runtime surface, and
  no save-to-user-files path for downloaded Sir Convert named artifacts.
- PR-0325 (authenticated Exam Converter runtime UI and save remediation):
  implemented the authenticated host/runtime/save surface needed before
  rerunning `PR-0324`.
- PR-0326 (authenticated LLM-enrichment consumer sync): done; the authenticated
  consumer now requests advisory suggestions, shows AI-facit review in the
  selected-question panel, builds `reviewed_completion_answer_key` overlays, and
  resubmits reviewed apply jobs before PDF/QTI readiness can change.
- PR-0328 (authenticated advisory idempotency rerun): done; live
  `paunchygent@gmail.com` testing proved that failed facitförslag enrichment
  can be a stale Sir Convert idempotent replay rather than a current Qwen
  failure. The remediation adds an explicit retry path for provider-only
  advisory failures that changes only the client idempotency digest for a
  bounded `advisoryRetryAttempt`, preserves normal duplicate-submit behavior,
  keeps retry state browser-runtime local, and renders the approved
  `Det gick inte att ta fram ett facitförslag.` / `Försök igen` UI without
  internal provider/idempotency wording.
- PR-0329 (reviewed AI-facit handoff): done; valid choice and `gap_fill`
  AI-facit suggestions now become teacher-reviewed
  `reviewed_completion_answer_key` overlays before the reviewed apply job can
  change file readiness.
- PR-0330 (small-screen AI-facit review layout strategy): canceled after
  PR-0338; the phone-layout diagnosis is retained as historical input, but the
  reviewed-AI accept/bulk-apply workflow is no longer an implementation target.
  Future phone work must target the durable AI-prefill editor flow.
- PR-0331 (reviewed AI-facit contract and affordance reconciliation): ready;
  retained Hemma/public proof shows accepted reviewed keys survive projection,
  reviewed apply, target readiness, and PDF/QTI downloads without forbidden
  internal fallback text.
- PR-0332 (teacher-owned correction overlay contract): done; consumes the
  unified Sir Convert/HuleEdu non-matching correction edge for point, choice,
  gap/open-cloze, and item-text corrections, projects transaction-returned
  effective state, keeps matching blocked, and does not claim durable
  correction-session persistence.
- ST-21-04 (durable teacher correction sessions): ready after accepted
  `ADR-0087` and approved `REV-ST-21-04`. Implementation is split into ordered
  PR-sized slices: `PR-0333` backend aggregate/persistence, `PR-0334`
  API/types, `PR-0335` replay orchestration, `PR-0336` frontend readback, and
  `PR-0338` AI-prefill/replay artifact authority are done. `PR-0339` is done
  as the Sir Convert-owned replay artifact reference contract follow-up.
  `PR-0340` is done: the report now replaces raw conversion-warning counts
  with teacher-relevant AI suggestion outcome reporting before the canonical
  `PR-0337` browser/artifact proof.
- ST-21-05 through ST-21-07 (speech-to-text transcript lane): planning stories
  added on 2026-06-09. They split authenticated transcript intake and
  diarization controls, Gateway-backed transcript job lifecycle, and durable
  JSON-first transcript saves. Retained review `REV-ST-21-05` is approved for
  downstream planning. `PR-0342` is done with accepted live proof through
  Skriptoteket -> HuleEdu Gateway -> Sir Convert -> STT/diarization ->
  canonical `transcript_json` for English and Swedish fixtures. `ST-21-07` /
  `PR-0343` is done: Skriptoteket now has an owner-scoped typed saved
  transcript aggregate, authenticated save/readback API, migration coverage,
  frontend save affordance over canonical JSON, and approved retained review
  `REV-PR-0343`. Sir Convert Story 54 / Task 358 is now accepted for
  product-neutral TXT, Markdown, WebVTT, and SRT formatter artifacts.
  `ST-21-08` is done: `PR-0344` progress/cancel parity, `PR-0345` formatter
  authority sync, `PR-0346` saved speaker-name overlays, `PR-0347` and
  `PR-0348` overlay-aware export actions, `PR-0349` live parity proof, and
  `PR-0350` product-owned export boundary are complete. `PR-0351` then hardened
  completion/progress/export UX around autosave, selected-format export
  actions, absence of forbidden legacy controls, and Task-364 progress fields.
  `PR-0354` is done as the manual remediation follow-up: it fixes export
  selector selected-state readability, removes unstable post-upload progress
  counters from teacher-facing UI, recovers stale formatter idempotency jobs,
  autosaves speaker-name edits, and proves transcript breakpoint ownership.
  Final retained proof
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260614T030725Z/proof-summary.json`
  used the HuleEdu browser-session ceremony and proved upload cancel feedback,
  running progress, durable transcript save, two speaker overlays, backend-owned
  formatter export, TXT/Markdown/WebVTT/SRT downloads with overlay labels, and
  Mina filer save. The production producer URL is now the internal Hemma Sir
  Convert service `http://sir_convert_a_lot_prod:8085`, not the reserved public
  `convert.hule.education` edge.
  Later retained `PR-0354` proof
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260614T210105Z/proof-summary.json`
  passed the same local dev E2E path after the UI remediation, and
  `.artifacts/pr-0354-transcript-ui-remediation/20260614T2104Z/` records
  in-app browser layout proof at 1440px and 1800px.
  `PR-0355` is done as a narrow follow-up: the rail keeps an invisible
  reserved `Avbryt` slot directly above `Starta transkribering` and removes the
  checkbox-like square icon. The empty upload copy now says
  `Ladda upp en ljudfil eller en video som du vill ha transkriberad`, and local
  remote-proof E2E passed at
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260615T141002Z/proof-summary.json`.
  The slice was pushed and deployed to Hemma at commit `fe56307c`.
- `ST-21-09` / `PR-0352` is done and approved by `REV-PR-0352`: remote
  inference with coherent HuleEdu Gateway/Sir Convert trust is enforced before
  upload, mixed local-signer to Hemma-verifier lanes fail closed unless
  explicitly verified, local heavy model/runtime hosting remains out of scope,
  and both local remote-proof plus native Hemma production STT E2E proofs are
  retained.
- `PR-0359` backlog cleanup repaired stale open transcript/runtime rows on
  2026-06-18. `ST-21-05` and `ST-21-06` are now marked `done` because the
  authenticated transcript intake, Gateway-backed job lifecycle, and canonical
  `transcript_json` delivery shipped through `PR-0342`, then stayed in active
  product use through `ST-21-07`, `ST-21-08`, and `ST-21-09`. `PR-0325` is
  now marked `done` as the authenticated Exam Converter runtime/save
  remediation that shipped before the later source-only direction. `PR-0324` is
  canceled as a superseded proof slice because its original blocker was
  remediated by `PR-0325`, and the remaining forward direction is governed by
  `ST-21-10`, `PR-0356`, and `PR-0357` rather than by reopening the old
  optional-result/early-target proof lane.
- `ST-21-10` is ready as the next Exam Converter product-direction follow-up:
  current intake should require only the governed source `.dxe` file, rely on
  LLM answer-key enrichment plus teacher review instead of optional marked
  exams, hide early target selection, and treat PDF/QTI/future DOCX as
  post-conversion file actions. `PR-0356` is the immediate authenticated
  source-only intake and export-owned format UX slice, and `PR-0357` is the
  separate governed public-lane cleanup follow-up.
- `PR-0360` / `ST-37-02` added
  [REF-current-product-lanes-and-sir-convert-boundary-v1](../../reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md)
  on 2026-06-18. Future `EPIC-21` cleanup should treat broad "Conversion Hub"
  language as technical/historical unless it is explicitly describing the
  compatibility shell. Teacher-facing planning should use the separate Exam
  Converter, Audio Transcription, and Document Converter lanes.
- `PR-0380` / `ST-37-04` corrected the Document Converter follow-up direction on
  2026-06-23: simple document conversion is app-boundary work inside
  Skriptoteket, while Sir Convert remains the heavy/OCR/complex PDF producer
  path. This correction applies only to the Document Converter lane and does not
  move STT, diarization, Exam Converter heavy import, or model-backed extraction
  into Skriptoteket.

## Decision And Assumption Ledger
The source record did not define a separate section for this package heading.

## Plan Document Review
The source record did not define a separate section for this package heading.

## Epic Closeout Review
The source record did not define a separate section for this package heading.
