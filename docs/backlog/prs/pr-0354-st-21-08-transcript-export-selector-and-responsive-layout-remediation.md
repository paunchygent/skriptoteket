---
type: pr
id: PR-0354
title: "ST-21-08 Transcript progress, export selector, and responsive layout remediation"
status: done
owners: "agents"
created: 2026-06-14
updated: 2026-06-14
stories:
  - "ST-21-08"
tags: ["frontend", "transcript", "conversion-hub", "progress", "export", "responsive", "ux"]
dependencies:
  - "PR-0351"
  - "MOCK-pr-0351-transcript-progress-export-ux"
acceptance_criteria:
  - "Given the completed transcript export selector is shown, when TXT, MD, VTT, or SRT is selected or focused, then the selected segment keeps a visible label and selected state instead of rendering navy-on-navy or hover-only fill."
  - "Given the transcript lane is shown on a desktop width, when the completed workspace has enough room, then the transcript and Talare och export inspector use the approved side-by-side composition."
  - "Given the transcript lane is shown at tablet-ish widths, when the workspace would squeeze the transcript, then the inspector moves below the transcript while the setup rail remains stable."
  - "Given the transcript lane is shown at small widths, when the mockup calls for reduced layout, then the setup rail stacks above the work surface."
  - "Given transcript creation is running after upload handoff, when upstream progress counters jump, freeze, or lack a stable ETA, then the UI does not render raw percent/ETA/audio-processed counters as precise progress promises."
  - "Given the browser is still uploading the selected media, when byte progress is available from the browser transport, then upload percent/bytes may remain visible because that progress is directly measured."
  - "Given the teacher edits speaker names, when the name fields change, then Skriptoteket autosaves the overlays and keeps export gated until the latest full speaker-name set is persisted."
  - "Given a formatter export retry resolves to a stale Sir Convert idempotency job that remains queued/submitted beyond the producer timeout window, when Skriptoteket creates the export, then the backend submits a bounded recovery request so the transcript can still receive formatter artifacts."
  - "Given implementation is complete, when focused frontend tests and browser-visible proof run, then the selector and responsive layout contract are verified without changing product-owned export APIs."
---

# PR-0354: ST-21-08 Transcript Progress, Export Selector, And Responsive Layout Remediation

## Problem

`PR-0351` implemented the approved transcript completion/export direction, but
manual UI inspection found two visual/interaction regressions:

- selected export-format chips can render with a navy fill and no readable
  label because selected and unselected Tailwind text/background utilities are
  present on the same button;
- browser focus can appear after screenshot keyboard shortcuts and be mistaken
  for selected state when the selected fill/text treatment is not clear;
- the running progress panel renders raw upstream percent, ETA, processed
  audio, and chunk counters as if they were stable teacher-facing progress, but
  production screenshots show those values jump and freeze between phases;
- a previous failed formatter export can be an idempotency collision with an
  old Sir Convert `queued` formatter job, so retrying the same saved transcript
  can attach to the stale upstream job instead of producing usable artifacts;
- speaker-name persistence is exposed as an unlabeled square icon that sits
  apart from the speaker-name workflow, making the save-before-export gate hard
  to understand;
- the transcript route inherits too much of the surrounding Exam Converter
  shell grid, so desktop, tablet-ish, and small-width compositions do not map
  cleanly to the mockup breakpoints.

## Goal

Restore the approved `PR-0351` mockup behavior without changing transcript
save/export APIs:

- selected format is visibly selected and readable;
- hover/focus feedback does not masquerade as selection;
- post-upload transcript creation uses truthful phase/status copy and stable
  stage markers rather than raw percent/ETA counters the backend cannot make
  smooth today;
- browser upload can still show measured byte percent because that is a local
  transport fact;
- speaker-name edits autosave on change, with saved/saving/failed copy that
  explains the export gate without a separate save button;
- desktop uses side-by-side transcript plus inspector when there is room;
- tablet-ish widths keep the transcript readable by moving the inspector below;
- small widths stack the setup rail above the work surface.

## Non-goals

- No product-owned formatter export API changes.
- No browser-owned Sir Convert replay orchestration.
- No copy changes beyond state labels required to keep existing behavior
  truthful.
- No broad redesign of the Conversion Hub Exam Converter lane.
- No new upstream progress/ETA contract in Sir Convert.

## Implementation plan

1. Add focused frontend regression coverage for visible selected-format state
   and transcript host responsive class contracts.
2. Refactor the transcript host template to own one responsive grid root that
   spans the parent Conversion Hub frame.
3. Move the completed workspace inspector split to a container-owned threshold
   so tablet/smaller desktop widths keep the transcript readable and wide
   desktop gets the side-by-side inspector.
4. Replace conflicting format-chip classes with selected/unselected branches so
   active labels stay readable.
5. Replace raw post-upload percent/ETA/audio counters with truthful running
   phase display and stable workflow markers; keep browser upload percent only.
6. Detect stale idempotent formatter jobs at the backend producer boundary and
   resubmit with a bounded recovery idempotency key.
7. Replace the unlabeled speaker-name save icon with debounced autosave on name
   change and a compact state row.
8. Run focused frontend tests, backend producer tests, frontend type/lint/build
   gates, dev local E2E proof, docs validation,
   and a browser-visible layout check.

## Remediation Ledger

Track every production and proof change in this slice here.

| Area | Change | Proof |
|---|---|---|
| Export selector | Remove conflicting selected/unselected text and fill utility classes from format chips. Selected chips use persistent navy fill with readable canvas text; unselected chips keep navy text and light hover only. | Focused Vitest asserts selected TXT/MD chips contain `text-canvas` and not `text-navy`; in-app browser proof must click TXT/MD/VTT/SRT and inspect visible text. |
| Transcript progress | Stop rendering raw Sir Convert post-upload percent/ETA/audio-processed/chunk counters as precise progress. Keep measured browser upload percent/bytes, then switch to stable phase labels and workflow markers once the backend owns the job. | Focused Vitest must assert upload percent remains visible, post-upload percent/ETA are absent, and phase copy remains teacher-facing; in-app browser proof must inspect the running state. |
| Native transcript proof progress snapshot | Align `scripts.playwright_pr_0349_transcript_parity_live` with the honest progress contract. The proof accepts phase text plus workflow steps/current-step after job handoff, accepts upload percent/bytes only while the browser owns upload, and treats terminal-before-snapshot as a valid fast-completion path instead of demanding removed raw counters. | Focused pytest covers job-owned progress, upload-owned progress, no-evidence rejection, and terminal-before-snapshot fast completion; native Hemma proof must rerun after deploy. |
| Formatter export idempotency | Detect stale Sir Convert formatter jobs returned by deterministic export idempotency keys and recover with a bounded retry idempotency key before polling/artifact download. | Infrastructure unit test proves stale queued idempotency response is not reused for artifact reads and recovered artifacts come from the new job; dev local E2E must still prove transcript export behavior. |
| Speaker overlay autosave | Remove the isolated save control. Speaker-name inputs now debounce autosave on change; export stays disabled until the latest full overlay set is persisted. The inspector shows compact copy for incomplete, saving, saved, and failed states. | Focused Vitest asserts name input triggers autosave and export only enables after persisted full coverage; in-app browser proof verifies there is no dead save button and the status row stays aligned. |
| Transcript route layout | Wrap the transcript lane in a `col-span-full` responsive grid owned by `ConversionHubTranscriptHost`, rather than relying on the Exam Converter parent grid. | Focused Vitest asserts the transcript host exposes small, tablet, and desktop breakpoint classes. |
| Completed workspace layout | Make the completed result surface an `@container`. The inspector stacks below the transcript until the result surface itself has enough width, then switches to a side-by-side transcript plus inspector grid. | Focused Vitest asserts the result surface owns the container-query grid contract; in-app browser proof checks stacked layout at 1440px and side-by-side at 1800px. |

## Implementation Summary

- `TranscriptFormatterExportPanel.vue` now branches selected/unselected
  segment classes instead of composing conflicting fill/text classes. Selected
  segments retain readable `text-canvas` labels.
- `TranscriptProgressPanel.vue` keeps measured browser upload percent/bytes
  before job handoff, then renders stable phase/workflow state without raw
  Sir Convert percent, ETA, processed-audio, chunk, or heartbeat counters.
- `scripts.playwright_pr_0349_transcript_parity_live` now treats that same
  progress contract as the native proof surface. It no longer requires removed
  duration/chunk/heartbeat fields and records fast terminal completion as
  `terminal_reached_before_snapshot=true` when the result surface appears before
  a running-state screenshot can be captured.
- `TranscriptCompletedWorkspace.vue` uses a container-query result grid and a
  compact speaker-name autosave row. Name edits do not require a separate save
  button; the saved state is status text, not a disabled control.
- `ConversionHubTranscriptHost.vue` debounces speaker-name autosave and clears
  stale formatter export state as soon as a name changes.
- `ConversionHubTranscriptHost.vue` and `TranscriptWorkflowRailShell.vue` own
  the transcript lane breakpoints, so the rail stacks on small widths, stays as
  a left rail at tablet-ish widths, and gives the completed result surface room
  to choose stacked or side-by-side content.
- `TranscriptUiInspectionView.vue` adds a dev/test-only authenticated fixture
  route for browser inspection of the production components without depending
  on a long STT job just to check layout.
- `SirConvertTranscriptFormatterProducerV2` detects stale deterministic
  formatter idempotency jobs and uses a bounded recovery key before polling and
  reading artifacts.

## Live Dev-Container Proof

The closeout proof for this PR must use the local dev containers and the
Codex in-app browser.

The local dev stack was reused with the dev-container frontend on
`http://127.0.0.1:5173`, Skriptoteket backend on `http://127.0.0.1:8000`,
HuleEdu on `http://127.0.0.1:8080`, and the sanctioned Sir Convert proof tunnel
on `http://127.0.0.1:28085`.

Retained local E2E proof:
`.artifacts/playwright-pr-0349-transcript-parity-live/20260614T210105Z/proof-summary.json`.

- Passed through the HuleEdu browser-session ceremony.
- Created transcript `ee18650e-5a3e-4e51-841c-7bea9e91abbb`.
- Proved product-owned formatter export returned all four artifacts:
  `transcript_txt`, `transcript_md`, `transcript_vtt`, and `transcript_srt`.
- Downloaded `.txt`, `.md`, `.vtt`, and `.srt` files with overlay labels
  present and fallback labels absent.
- Saved the representative TXT artifact to Mina filer.
- Proved speaker overlays were saved through autosave after name field input;
  no manual speaker-name save button was clicked or required.
- Captured progress UI truthfulness: upload percent visible while uploading;
  duration/chunk/heartbeat counters absent after job handoff.

Native Hemma proof on 2026-06-15 exposed one stale proof-script assertion after
this remediation: the deployed script still required old progress fields and
failed with `Progress fields did not render before terminal state.` Retained
failed artifact:
`/home/paunchygent/apps/skriptoteket/.artifacts/playwright-pr-0352-transcript-parity-native/20260615T155823Z/proof-summary.json`.
The follow-up proof-script contract above is governed here so the next native
run proves the current UI rather than the removed counters.

Retained in-app browser proof artifacts:
`.artifacts/pr-0354-transcript-ui-remediation/20260614T2104Z/`.

- URL:
  `http://127.0.0.1:5173/apps/documents.conversion_hub/transcript/ui-fixtures/completed-export`.
- `in-app-browser-1440-autosave-md-download.png`: at 1440px, the setup
  rail remains left, while the completed transcript and inspector stack because
  the result surface has only 766px available. The saved speaker state shows
  `Namnen är sparade.`, no speaker save button is rendered, MD is selected with a
  readable label, export status is `Fil hämtad.`, and the clicked export action
  has `outline-style: none` while keyboard focus remains `focus-visible`.
- `in-app-browser-1800-autosave-md-download.png`: at 1800px, the result
  surface has 1118px available and switches to side-by-side transcript plus
  inspector. Export actions fit inside the inspector without clipping.

## Test plan

```bash
pdm run fe-test -- --run src/router/routes.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.pr0351.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.pr0351.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts
pdm run test tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_transcript_formatter_producer.py
pdm run python -m scripts.playwright_pr_0349_transcript_parity_live --base-url http://127.0.0.1:5173 --dotenv .env --sir-convert-proof-lane hemma-remote-proof --sir-convert-gateway-backend-url http://host.docker.internal:28085 --sir-convert-producer-backend-url http://host.docker.internal:28085 --sir-convert-ready-url http://127.0.0.1:28085/readyz --gateway-signer-fingerprint 46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992 --sir-convert-trusted-fingerprint 46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992 --timeout-seconds 1200
pdm run fe-type-check
pdm run fe-lint
pdm run fe-build
pdm run docs-validate
pdm run handoff-validate
git diff --check
```

All listed commands passed on 2026-06-14. `pdm run fe-build` retained the
existing Vite dynamic/static import and large-chunk warnings.

Follow-up proof-script regression added after the 2026-06-15 native Hemma proof
found the stale raw-counter assertion:

```bash
pdm run test tests/unit/scripts/test_playwright_pr_0349_progress_snapshot.py tests/unit/scripts/test_playwright_pr_0349_summary_truthfulness.py
pdm run python -m py_compile scripts/playwright_pr_0349_transcript_parity_live.py
pdm run docs-validate
pdm run handoff-validate
git diff --check
```

All follow-up commands passed on 2026-06-15.

## Rollback plan

Revert only the transcript Vue component layout/style changes while preserving
the `PR-0350`/`PR-0351` product-owned export state boundary and autosave
workflow. Do not restore legacy per-artifact export rows or browser replay
orchestration.
