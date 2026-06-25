---
type: pr
id: PR-0386
title: "ST-37-04 Audio Transcription button token remediation"
status: ready
owners: "agents"
created: 2026-06-25
updated: 2026-06-25
stories:
  - "ST-37-04"
tags:
  - frontend
  - design-system
  - audio-transcription
  - remediation
dependencies:
  - "PR-0383"
acceptance_criteria:
  - "Given the compact curated-app design contract separates selector state from command buttons, when Audio Transcription renders command actions, then download, save, start, cancel, reset, and related operating buttons do not use navy-filled CTA styling."
  - "Given selector rails and segmented selectors have their own selected-state treatment, when Audio Transcription renders mode or format selection, then selection styling is explicit and not reused as generic command-button styling."
  - "Given PR-0383 corrected the Document Converter visual-token contract, when this remediation closes, then the transcript route is audited against the same token rule without changing backend contracts, product flow, or user-facing copy."
  - "Given route-visible UI styling changes require proof, when the remediation closes, then focused frontend tests and live visual evidence cover the transcript intake, running, and completed/export states."
---

# PR-0386: ST-37-04 Audio Transcription Button Token Remediation

## Problem

The `PR-0383` Document Converter mockup review exposed a broader compact-app
styling drift: the current Audio Transcription route uses navy-filled or
CTA-like treatment for ordinary operating buttons. That blurs the distinction
between selector state and command actions, and risks teaching the wrong pattern
to the Document Converter implementation.

## Goal

Audit and remediate the Audio Transcription route so compact command buttons
use neutral bordered token surfaces, while selector controls keep an explicit
selected-state treatment. Preserve all route behavior and copy.

## Non-goals

- No backend, API, producer, persistence, or transcript-export contract changes.
- No user-facing copy rewrite.
- No Document Converter implementation work.
- No broad design-system rewrite unless the audit finds a direct conflict that
  must be reconciled before route-visible styling can be truthful.

## Implementation Plan

1. Audit the transcript route styling in:
   - `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkflowRailShell.vue`
   - `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptFormatterExportPanel.vue`
   - `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptProgressPanel.vue`
   - `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptCompletedWorkspace.vue`
2. Classify controls as selector, command, progress/status, or destructive.
3. Replace navy-filled command-button styling with neutral compact button
   treatment using existing token primitives or tightly scoped shared classes.
4. Keep selector styling explicit and avoid reusing selector fills for command
   actions.
5. If the corrected contract conflicts with
   `.codex/rules/045-huleedu-design-system.md`, pause implementation and patch
   the governed design-system doctrine before continuing.

## Test Plan

Red-first target:

- Add or update focused transcript component tests proving command buttons no
  longer carry navy-filled CTA classes while selector controls retain a selected
  state.

Green/closeout:

- `pdm run fe-test -- --run src/views/apps/conversion-hub-transcript/TranscriptWorkflowRailShell.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- Live authenticated or UI-inspection visual proof for intake, running, and
  completed/export transcript states.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Stop Conditions

- Stop if remediation requires behavior, copy, backend, producer, or persistence
  changes.
- Stop if selector versus command-button token doctrine cannot be reconciled
  with the governed design-system rule.
- Stop if live route proof would require changing the HuleEdu shared-auth
  ceremony or bypassing the existing authenticated proof helpers.

## Rollback Plan

Revert the Audio Transcription styling/test changes and restore the previous
component classes. Keep the PR-0383 mockup/copy approval package unchanged.
