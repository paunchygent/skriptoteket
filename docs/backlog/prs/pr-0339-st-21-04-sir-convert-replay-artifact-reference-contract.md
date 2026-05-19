---
type: pr
id: PR-0339
title: "ST-21-04 Sir Convert replay artifact reference contract"
status: done
owners: "agents"
created: 2026-05-19
updated: 2026-05-19
stories:
  - "ST-21-04"
tags:
  - sir-convert
  - huleedu-gateway
  - frontend
  - conversion-hub
  - exam-converter
  - artifact-authority
dependencies:
  - "ADR-0087"
  - "PR-0338"
acceptance_criteria:
  - "Given Sir Convert correction apply creates an exportable corrected target, when `ExamAuthoringCorrectionsApplyResultV1` is returned, then the target readiness row exposes a replay-scoped corrected artifact reference for that target."
  - "Given a target is not exportable, when the correction apply result is returned, then no downloadable corrected artifact reference is exposed for that target."
  - "Given HuleEdu Gateway receives the corrected artifact reference from Sir Convert, when Skriptoteket calls the unified correction apply edge, then the field is passed through unchanged in the generated contract."
  - "Given Skriptoteket receives a replay-scoped corrected artifact reference, when file rows are projected, then `file.artifactActionReference` uses `{ authority: \"replay_result\", artifactKey }` and downloads/saves use that reference only."
  - "Given replay returns target readiness without a corrected artifact reference, when the teacher opens `Filer`, then corrected `Hämta` and `Spara` stay disabled and no original-job artifact fallback is used."
---

# PR-0339: ST-21-04 Sir Convert Replay Artifact Reference Contract

## Problem

`PR-0338` tightened Skriptoteket so corrected file actions cannot fall back to
original job artifacts after correction replay. That is the right authority
boundary, but the current Sir Convert correction apply result exposes only
artifact availability and target readiness. It does not expose the corrected
artifact key/reference that should authorize replay-derived downloads and
save-to-files actions.

The original DigiExam target readiness row already has an `artifact_key`, which
is why original-job file actions can be authorized. Correction replay needs the
same kind of authority in the replay result. Skriptoteket must consume that
reference; it must not guess one.

## Goal

Make Sir Convert the owner of replay-derived corrected artifact references.
When correction apply produces or identifies an exportable corrected target,
the result contract must include a replay-scoped reference that HuleEdu Gateway
passes through and Skriptoteket uses for file actions.

Recommended default: Sir Convert owns corrected artifact creation/storage or
returns a reference to already-created replay artifacts. Skriptoteket-owned
replay artifact storage is not the default and needs a separate explicit
product-owner approval slice.

## Scope

- Sir Convert contract shape:
  `ExamAuthoringCorrectionTargetReadinessRowV1` should include either
  `artifact_key` or a more explicit `artifact_reference` when
  `export_enabled=true`.
- Sir Convert runtime behavior: the reference must identify the replay-derived
  corrected artifact that is safe to download/save for that corrected target.
- HuleEdu Gateway behavior: pass the reference through unchanged and regenerate
  generated clients/types.
- Skriptoteket behavior: keep the `PR-0338` gating and map the replay reference
  in `correctionSessionProjection.ts` to
  `file.artifactActionReference = { authority: "replay_result", artifactKey }`.
- File action behavior: `useExamConverterFileActions.ts` downloads and saves
  only through the authorized replay reference for corrected rows.

## Non-goals

- No fallback to original `/jobs/{jobId}/artifacts` for corrected file actions.
- No Skriptoteket-owned replay artifact storage unless explicitly approved as
  a separate storage/security/retention slice.
- No matching answer-key enablement before the governed matching producer task.
- No change to `PR-0337` proof requirements beyond letting it prove disabled
  corrected file actions until this contract exists.

## Implementation Plan

1. In Sir Convert, update the correction apply result contract so exportable
   correction target readiness rows expose a replay-scoped corrected artifact
   reference.
2. Ensure Sir Convert creates/stores the corrected artifact, or returns a
   reference to an already-created corrected artifact, before setting
   `export_enabled=true`.
3. Add Sir Convert contract/runtime tests proving ready targets include the
   reference and blocked targets do not.
4. Pass the field through HuleEdu Gateway unchanged and regenerate Gateway
   OpenAPI/types.
5. Regenerate Skriptoteket Sir Convert client types and keep
   `correctionSessionProjection.ts` as the sole mapper into
   `artifactActionReference`.
6. Extend Skriptoteket focused file-action tests so a replay row with
   `artifact_key` enables `Hämta`/`Spara` and uses that replay artifact key,
   while rows without the reference remain disabled.
7. Update `PR-0337` or its successor proof to include enabled corrected
   downloads/saves only after this contract is present in the live route.

## Test Plan

- Sir Convert contract/runtime tests for replay artifact reference emission.
- HuleEdu Gateway generated-client/pass-through proof.
- Skriptoteket generated type refresh and focused Vitest around replay
  `artifactActionReference` mapping and file actions.
- `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run fe-build`,
  `pdm run docs-validate`, `pdm run handoff-validate`, and `git diff --check`
  from this repo after the generated contract lands here.

## Implementation Closeout

Completed in this slice:

- Sir Convert owns replay-derived corrected artifacts for correction apply and
  exposes replay-scoped `artifact_key` values on exportable correction target
  readiness rows.
- HuleEdu Gateway passes the replay artifact authority through unchanged in
  the generated correction apply contract.
- Skriptoteket maps only producer-returned replay references into
  `file.artifactActionReference = { authority: "replay_result", artifactKey }`;
  corrected `Hämta` and `Spara` never fall back to original job artifacts.
- Accepted unchanged AI-prefilled answer keys keep
  `accepted_advisory_candidate` provenance after replay projection, so the
  question list and inspector use the Lucide Bot symbol. Teacher-authored and
  teacher-edited keys keep the normal check/selected-choice indicator.
- The report separates remaining teacher actions from conversion diagnostics:
  original conversion warning counts can remain visible after all missing
  facit/poäng actions are resolved and corrected downloads are enabled.

Verified locally:

- `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedAiPrefillDurableSlice.spec.ts src/views/apps/ExamConverterAuthenticatedReviewSlice.spec.ts src/views/apps/ExamConverterAuthenticatedRuntimeBridgeSlice.spec.ts`
- `pdm run fe-test -- --run src/views/apps/ExamConverterAuthenticatedFilesActionSlice.spec.ts src/views/apps/ExamConverterCorrectionSessionReplay.spec.ts src/views/apps/ExamConverterAuthenticatedCorrectionSlice.spec.ts`
- `pdm run fe-type-check`
- `pdm run pytest -q tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py`

## Rollback Plan

If the upstream reference cannot be produced safely, keep `PR-0338` behavior:
corrected file actions remain disabled after replay and the UI shows
`Filer kunde inte skapas`. Do not restore original-job artifact fallback for
corrected rows.
