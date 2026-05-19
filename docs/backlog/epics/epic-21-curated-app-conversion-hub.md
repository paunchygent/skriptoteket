---
type: epic
id: EPIC-21
title: "Curated app: Conversion Hub (Sir Convert-a-Lot v2)"
status: active
owners: "agents"
created: 2026-03-01
updated: 2026-05-19
outcome: "Skriptoteket provides first-class conversion hub and exam-converter UI lanes that route supported conversions through Sir Convert-a-Lot v2, with no production dependence on the legacy html-to-pdf-preview tool script."
---

## Scope

- Add a **Conversion Hub** curated app (bespoke-required) that exposes a complete UI for the set of
  conversions supported by Sir Convert-a-Lot v2.
- Add an Exam Converter product lane under Conversion Hub for teacher-facing
  DigiExam/Exam.net migration workflows, split into public one-time conversion
  and authenticated owner-scoped artifact workflows.
- Support batch conversions (multiple files) and a single-PDF preview UX that still uses the normal
  v2 job lifecycle, but through a Skriptoteket-owned local job ledger and download boundary rather
  than raw upstream job ids.
- Surface v2 PDF layout presets (for example A5/A4/A3 and portrait/landscape) in the UI for relevant
  outputs.
- Migrate tests and remove production reliance on `html-to-pdf-preview`.
- Define the same-host Sir Convert transport shape explicitly: Unix socket preferred, `127.0.0.1`
  HTTP fallback, no internal HTTPS default between co-located services.

## Out of scope

- No new conversion engines inside Skriptoteket (no WeasyPrint/Pandoc pipelines in Skriptoteket
  beyond what's required for tests unrelated to conversion hub).
- No partial/legacy shims for `html-to-pdf-preview` once the curated app exists: callers/tests are
  updated to the new surface.
- No redirect-based artifact delivery that bypasses Skriptoteket ownership checks for Conversion Hub
  downloads.
- No general public anonymous conversion upload route may ship outside the
  accepted `ADR-0085` scoped public capability contract for the bounded Exam
  Converter exception.

## Stories (ordered)

- [ ] 1. [ST-21-01: Curated app: Conversion Hub (v1)](../stories/story-21-01-curated-app-conversion-hub-v1.md)
- [ ] 2. [ST-21-02: Migration: retire html-to-pdf-preview + update tests](../stories/story-21-02-migrate-off-html-to-pdf-preview-and-retire-tool.md)
- [ ] 3. [ST-21-03: Exam converter public and authenticated artifact lanes](../stories/story-21-03-exam-converter-public-and-authenticated-artifact-lanes.md)
- [ ] 4. [ST-21-04: Exam Converter durable teacher correction sessions](../stories/story-21-04-exam-converter-durable-teacher-correction-sessions.md)

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

## Dependencies

- ADR-0066 (this epic's conversion strategy decision)
- Existing curated apps platform: ADR-0022, ADR-0023, ADR-0024
- Public curated-app access and abuse-control authority: ADR-0079, ADR-0085,
  ST-32-03
- HuleEdu authenticated Sir Convert edge:
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-07-expose-sir-convert-artifact-bundle-routes-through-huleedu-auth-edge.md`
- Sir Convert artifact-bundle contract:
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/converters/digiexam-migration-service-api-artifact-contract.md`

## Implementation Summary (as of 2026-05-13)

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
