---
type: pr
id: PR-0351
title: "ST-21-08 Transcript completion, progress, and export UX"
status: done
owners: "agents"
created: 2026-06-14
updated: 2026-06-14
stories:
  - "ST-21-08"
tags:
  - frontend
  - transcript
  - conversion-hub
  - progress
  - export
  - ux
dependencies:
  - "PR-0350"
  - "MOCK-pr-0351-transcript-progress-export-ux"
  - "Sir Convert task-364 for improved STT phase progress/telemetry where new producer fields are required"
acceptance_criteria:
  - "Given a teacher starts transcript conversion, when upload/admission and STT work are in progress, then the UI shows a stable progress layout with normal Swedish copy, measured progress/ETA where available, elapsed time, and no spinner-only or dead 0% presentation."
  - "Given a transcript finishes successfully, when the completed transcript view appears, then the transcript is saved automatically and the teacher lands directly in the useful transcript workspace without a generic manual Spara gate."
  - "Given the completed transcript workspace is shown, when speaker names and export controls render, then the transcript keeps real reading width and the inspector follows the approved mockup hierarchy without redundant labels, cramped middle columns, or calculator-like export button rows."
  - "Given export formats are available, when the teacher selects TXT, MD, VTT, or SRT, then the UI offers stable one-line actions Ladda ner and Mina filer for the selected format without duplicating download affordances or interpolating the selected format into action labels."
  - "Given warning, pending, running, failed, or recovery states are needed, when they render, then they use reserved layout or separately planned state layouts and never appear as hidden jump-scare rows that push surrounding controls."
  - "Given implementation is complete, when focused tests and live proof run, then old manual-save/export-gate copy and browser-owned replay/download/base64 behavior remain absent."
---

# PR-0351: ST-21-08 Transcript Completion, Progress, And Export UX

## Problem

The transcript lane is now architecturally product-owned after `PR-0350`, but
the teacher-facing workflow still carries confusing legacy UX:

- upload/admission and STT phases can look frozen or dead for short/few-chunk
  jobs;
- completion lands behind a generic manual `Spara` gate even though saving is
  not a meaningful teacher choice at that moment;
- speaker naming and export affordances appear too late and with unclear
  hierarchy;
- export controls have repeatedly drifted into duplicated download/save
  actions, metadata cards, dropdown symbols without menus, and cramped button
  rows;
- warning/status rows risk appearing dynamically and moving the layout.

The approved mockup direction now defines the product hierarchy and the
lessons learned from design review. This PR turns that direction into the
runtime transcript workspace.

## Goal

Make the transcript lane feel alive, direct, and product-owned:

- conversion progress is stable and understandable;
- completed transcripts autosave and open into the actual workspace;
- speaker naming and export actions are visible as the useful next work;
- exports have one selected format and two stable actions: `Ladda ner` and
  `Mina filer`;
- layout does not jump when status, failure, or warning state changes.

## Non-goals

- No chunk-size or batch-size tuning in Skriptoteket.
- No browser-owned Sir Convert submit/poll/download/base64/complete saga.
- No local TXT/Markdown/VTT/SRT formatter fallback.
- No manual save gate after a successful transcript conversion.
- No Swenglish/internal phase copy such as `diariserar` or raw producer stage
  names in teacher-facing UI.
- No hidden status, warning, or recovery row that appears later and pushes
  controls around.
- No new product promise that the teacher can leave or use other parts of the
  service unless the implementation has verified that behavior.

## Governing Mockup

Use the approved mockup bundle as qualitative product direction:

- `docs/mockups/pr-0351-transcript-progress-export-ux/README.md`
- `docs/mockups/pr-0351-transcript-progress-export-ux/index.html`

The implementation must preserve the state hierarchy and interaction contract;
it does not need to pixel-match the static HTML.

Mockup lessons that are part of this PR contract:

- Do not show the transcript/export workspace while the transcript does not
  exist. The running state is a conversion-progress workspace, not a preview of
  later controls.
- Do not use an `Avbryt efter klar` concept. Running work has one clear
  `Avbryt` action only where cancellation is actually possible.
- Avoid internal terms. Use normal Swedish such as `Hittar talare`, `Skriver ut
  samtalet`, and `Gör texten klar`.
- Do not add explanatory marketing/helper text unless it states verified
  product behavior.
- Do not add redundant labels such as `Talarnamn` and `Export` inside an
  inspector already titled `Talare och export`.
- Do not duplicate download controls. Format selection is one control; actions
  are `Ladda ner` and `Mina filer`.
- Do not interpolate selected file formats into visible action labels; `TXT`,
  `MD`, `VTT`, or `SRT` belongs in the format selector, not as a dynamic
  two-line button label.

## Implementation Plan

1. Audit the current transcript workspace components and API clients after
   `PR-0350`, especially completion/save state, progress rendering, speaker
   overlay editing, formatter export state, download action, and Mina filer
   action.
2. Add red-first frontend tests for the approved UX contract:
   - running progress does not render as a dead 0% single-chunk surface;
   - transcript completion autosaves and skips the generic `Spara` gate;
   - old copy/actions such as primary `Spara`, `Skapa exportfiler`, `Skapa
     igen`, and `Skapa transkript igen` are absent from the normal path;
   - export controls expose one selected format and stable `Ladda ner` /
     `Mina filer` actions.
3. Update the progress rendering to consume the current product/Sir Convert
   progress fields and, after Sir Convert `task-364`, prefer the new measured
   phase progress/ETA fields when present.
4. Refactor the completed workspace around the approved hierarchy:
   transcript reading surface plus right-side inspector, with responsive
   breakpoints that preserve transcript width before moving the inspector.
5. Remove the manual save gate from successful transcript completion and make
   autosave/readback the normal completed-state transition.
6. Replace export UI affordance drift with the approved format selector plus
   two stable one-line actions.
7. Add explicit reserved state handling for pending/running/failed export or
   save states so messages do not pop in and move controls.
8. Run focused frontend tests, focused backend tests if DTO/API behavior
   changes, browser proof through the sanctioned HuleEdu ceremony, and docs
   closeout.

## Implementation Summary

`PR-0351` is implemented and independently reviewed in `REV-PR-0351`.

- The running transcript surface now uses Task-364 progress fields, maps
  producer phases to normal Swedish copy, reserves abort/status layout, and does
  not render a fake completed workspace before transcript content exists.
- Successful transcript completion autosaves through the product save API and
  lands directly in the transcript workspace. The generic manual `Spara` gate is
  removed from the normal completion path.
- The completed workspace is split into a readable transcript surface and a
  `Talare och export` inspector without redundant `Talarnamn` / `Export`
  labels.
- Formatter export UI is now selected-format only: `TXT`, `MD`, `VTT`, and
  `SRT` are selected in one control; visible actions stay `Ladda ner` and
  `Mina filer` without dynamic suffixes or duplicated per-artifact rows.
- Skriptoteket-owned legacy replay code was removed. The deleted surfaces
  include the frontend replay panel, old replay parser modules, old replay
  command naming, and old per-artifact download/save rows. Remaining
  `transcript_formatter_replay_v1`,
  `transcript_replay_bundle_manifest.json`, and
  `transcript_json_to_transcript_bundle_replay_v2` strings are upstream Sir
  Convert contract literals consumed by the product export boundary.
- The reviewer-requested remediation now requires saved non-empty speaker names
  for every canonical speaker label before selected-format export can run, both
  in the frontend readiness gate and in the backend producer-submission
  boundary.

## Red-First Evidence

- Frontend PR-0351 tests were added to assert the forbidden old UX is absent,
  not merely that new components render:
  `TranscriptWorkspaceShell.pr0351.spec.ts` and
  `ConversionHubTranscriptHost.pr0351.spec.ts`.
- Backend red-first remediation proved partial speaker overlays were previously
  accepted before producer submission; the production fix now raises
  `validation_error` before any export job is created.
- Frontend red-first remediation proved a two-speaker transcript with only one
  persisted overlay previously allowed export readiness; the production fix now
  keeps both selected-format actions disabled.

## Verification Evidence

Focused green checks after implementation:

```bash
pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py::test_product_export_rejects_partial_speaker_overlays_before_producer_submission
pdm run fe-test -- --run src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts -t "keeps export disabled until all transcript speakers have persisted names"
pdm run test tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_formatter_exports.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_artifact_actions.py tests/unit/application/curated_apps/handlers/test_conversion_hub_transcript_saves.py tests/unit/web/conversion_hub/test_apps_conversion_hub_transcript_saves_api.py
pdm run fe-test -- --run src/api/sirConvertGateway/transcriptClient.spec.ts src/api/sirConvertGateway/transcriptProgressParsers.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.pr0351.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.pr0351.spec.ts src/api/conversionHubTranscriptFormatterArtifactActions.spec.ts src/views/apps/conversion-hub-transcript/useTranscriptGatewayRuntime.spec.ts
pdm run fe-type-check
pdm run fe-lint
pdm run fe-build
```

Observed results:

- Backend remediation test passed.
- Frontend remediation test passed.
- Focused backend transcript/export bundle passed: 31 tests.
- Focused frontend transcript/export bundle passed: 8 files, 44 tests.
- `fe-type-check`, `fe-lint`, and `fe-build` passed. `fe-build` retained the
  existing Vite dynamic/static import and large chunk warnings.
- Legacy-surface grep found forbidden PR-0351 UI strings only in negative
  assertions. Backend replay-string grep found only upstream Sir Convert
  contract literals.

Live proof:

```bash
pdm run python -m scripts.playwright_pr_0349_transcript_parity_live --base-url http://127.0.0.1:5173 --dotenv .env --sir-convert-proof-lane hemma-remote-proof --sir-convert-gateway-backend-url http://host.docker.internal:28085 --sir-convert-producer-backend-url http://host.docker.internal:28085 --sir-convert-ready-url http://127.0.0.1:28085/readyz --gateway-signer-fingerprint 46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992 --sir-convert-trusted-fingerprint 46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992 --timeout-seconds 1200
```

Observed result:

- Local proof passed through the HuleEdu browser-session ceremony with real
  remote-proof Sir Convert STT/diarization/alignment compute.
- The proof retained cancel/progress/completion screenshots, autosaved a
  `transcript_json_v1` transcript with 27 segments and two speakers, saved two
  speaker overlays, produced four formatter artifacts, downloaded TXT/MD/VTT/SRT,
  and saved the representative TXT artifact to Mina filer.
- Retained proof artifact:
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260614T184817Z/proof-summary.json`.
- Docker-backed runtime evidence:
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260614T184817Z/backend-container.json`
  shows the local product backend producer lane as
  `http://host.docker.internal:28085`, and
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260614T184817Z/backend-live.log`
  shows formatter export plus all four artifact downloads through that lane
  with HTTP 200 responses.
- Native Hemma production proof is retained under `PR-0352` at
  `/home/paunchygent/apps/skriptoteket/.artifacts/playwright-pr-0352-transcript-parity-native/20260614T191738Z/proof-summary.json`
  after deploying Sir Convert `159e82d5` and Skriptoteket `2fa27cfb`.

## Test Plan

- Focused Vitest for transcript host/workspace rendering:
  - upload/admission/STT progress states;
  - autosave completion path;
  - absence of manual `Spara` gate and old export labels;
  - stable export action labels and no duplicate download controls;
  - no hidden jump-scare state rows.
- Focused API/client tests if DTOs or generated types change.
- Focused backend tests only if product export/save state contracts change.
- Live browser proof through the HuleEdu browser-session ceremony only,
  recording:
  - upload/admission/progress state;
  - autosaved transcript completion;
  - speaker rename/readback;
  - format selection;
  - download and Mina filer actions for a representative format;
  - failure/pending layout proof if feasible without destructive actions.
- Required closeout:

```bash
pdm run fe-test -- --run <focused transcript workspace specs>
pdm run fe-type-check
pdm run fe-lint
pdm run fe-build
pdm run docs-validate
pdm run handoff-validate
git diff --check
```

If backend or DTO surfaces change, also run:

```bash
pdm run test <focused backend transcript/export tests>
pdm run lint
pdm run typecheck
pdm run fe-gen-api-types
```

## Rollback Plan

Hide or disable the redesigned transcript/export controls while preserving
saved transcript readback and existing product-owned export endpoints. Do not
restore the browser-owned Sir Convert saga, local formatter fallback, or manual
generic `Spara` gate.
