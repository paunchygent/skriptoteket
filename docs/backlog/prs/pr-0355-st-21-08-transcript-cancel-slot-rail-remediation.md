---
type: pr
id: PR-0355
title: "ST-21-08 Transcript cancel slot rail remediation"
status: done
owners: "agents"
created: 2026-06-14
updated: 2026-06-15
stories:
  - "ST-21-08"
tags: ["frontend", "transcript", "conversion-hub", "cancel", "ux"]
acceptance_criteria:
  - "Given the transcript setup rail is idle, when the page renders, then the Avbryt control has reserved space directly above Starta transkribering but is invisible, disabled, and not focusable."
  - "Given transcription is running, when the setup rail renders, then Avbryt appears in that same reserved slot directly above Starta transkribering without pushing controls down."
  - "Given the Avbryt control is shown, when users inspect the control, then it does not contain a square icon or checkbox-like affordance."
  - "Given no transcript source is selected, when the empty workspace intro renders, then the upload copy says `Ladda upp en ljudfil eller en video som du vill ha transkriberad`."
  - "Given the local dev transcript E2E runs after the Offload lane is free, when the proof completes, then retained evidence shows cancel feedback, transcript autosave, overlay save, all four formatter downloads, and Mina filer save."
---

# PR-0355: ST-21-08 Transcript Cancel Slot Rail Remediation

## Problem

The transcript setup rail regressed from the approved mockup contract. The
running cancel action is conditionally inserted after `Starta transkribering`,
which makes the rail jump when transcription starts. Its square stop icon also
reads visually like a useless checkbox.

## Goal

Keep cancellation as one direct action:

- reserve the cancel row directly above `Starta transkribering`;
- keep the reserved row invisible, disabled, and out of tab order until work is
  running;
- show `Avbryt` in the same slot while transcription runs;
- remove the square icon so the control no longer looks like a checkbox.
- update the empty workspace upload copy to address the teacher's intent
  directly: `Ladda upp en ljudfil eller en video som du vill ha
  transkriberad`.

## Non-goals

- No runtime cancellation API changes.
- No progress-panel redesign.
- No transcript export changes.
- No transcript runtime cancellation API changes.

## Implementation plan

1. Update `TranscriptWorkflowRailShell.vue` so the cancel button is always
   mounted above the start button, using CSS visibility and disabled/focus
   state to reserve space while idle.
2. Remove the square icon from the cancel button.
3. Add focused rail DOM coverage for idle, running, and pending cancellation
   states.
4. Update the empty transcript workspace intro copy from passive audio-track
   language to direct teacher intent.
5. Run focused Vitest/typecheck and the required local dev transcript E2E
   after the Offload lane is free.

## Test plan

- `pdm run fe-test -- --run src/views/apps/conversion-hub-transcript/TranscriptWorkflowRailShell.spec.ts` - passed, 3 tests.
- `pdm run fe-test -- --run src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts` - passed, 10 tests.
- `pdm run fe-type-check` - passed.
- `pdm run docs-validate` - passed.
- `pdm run python -m scripts.playwright_pr_0349_transcript_parity_live --base-url http://127.0.0.1:5173 --dotenv .env --sir-convert-proof-lane hemma-remote-proof --sir-convert-gateway-backend-url http://host.docker.internal:28085 --sir-convert-producer-backend-url http://host.docker.internal:28085 --sir-convert-ready-url http://127.0.0.1:28085/readyz --gateway-signer-fingerprint 46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992 --sir-convert-trusted-fingerprint 46aefc0edc2f71267e2df783ca27f4df2b0da269cc7e84b43cbe2de6ac7c1992 --timeout-seconds 1200` - passed.
- Retained E2E artifact:
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260615T141002Z/proof-summary.json`.
- `pdm run hemma-deploy` - passed for commit `fe56307c`; deploy log:
  `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260615-154707.log`.
- Production health after deploy: `https://skriptoteket.hule.education/healthz`
  returned `{"status":"healthy","message":"Service is healthy"}`; Hemma
  `skriptoteket-web` and `skriptoteket-worker` containers were healthy.

## Rollback plan

Revert the rail template/test/doc changes from this PR slice. Runtime
transcription and export behavior are unchanged.
