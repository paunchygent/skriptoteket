---
type: review
id: REV-PR-0386
title: "Review: PR-0386 Audio Transcription button token remediation"
status: approved
owners: "agents"
created: 2026-06-25
updated: 2026-06-25
reviewer: "codex-independent-reviewer"
prs:
  - PR-0386
links:
  - ST-37-04
  - EPIC-37
  - PR-0383
---

# Review: PR-0386 Audio Transcription Button Token Remediation

## TL;DR

Independent review completed for the Audio Transcription button-token
remediation. The frontend-only patch removes navy-filled CTA treatment from the
ordinary transcript command buttons, preserves explicit selected-state styling
for selector controls, and keeps behavior, copy, backend contracts, and auth
surface boundaries unchanged. Focused Vitest, frontend gates, retained visual
artifacts, and route-level auth-fixture inspection support approval.

## Problem Statement

`PR-0383` locked the compact curated-app token rule that selected rails may use
navy fill while ordinary operating actions remain neutral. Audio Transcription
had drifted away from that rule by presenting start/download-style operating
controls with CTA-like filled treatment. This review checks whether the
remediation restores the governed visual split without sneaking in backend/API
changes, copy drift, auth shortcuts, or a hidden local design system.

## Proposed Solution

Keep the remediation route-local: extract a narrow transcript command-button
class helper for the affected operating buttons, preserve explicit selected
state on the speaker/export selectors, and extend the existing dev/test
authenticated transcript inspection fixture so intake, running, and completed
export states can be reviewed without mutating production behavior.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0386-st-37-04-audio-transcription-button-token-remediation.md` | Scope, acceptance criteria, claimed proof, stop conditions | 20 min |
| `docs/backlog/prs/pr-0383-st-37-04-document-converter-mockup-and-copy-approval-package.md` | Governing visual-token decision | 15 min |
| `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkflowRailShell.vue` | Start/cancel/reset command-button styling, copy, emitted behavior | 20 min |
| `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptFormatterExportPanel.vue` | Selected-format selector styling versus neutral download/save controls | 20 min |
| `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/transcriptCommandButtonClasses.ts` | Scope, typing, and hidden-design-system audit | 15 min |
| `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptUiInspectionView.vue` and `frontend/apps/skriptoteket/src/router/routes.ts` | Dev/test fixture truthfulness, auth gating, non-production boundary | 25 min |
| `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkflowRailShell.spec.ts`, `TranscriptFormatterExportPanel.spec.ts`, `TranscriptWorkspaceShell.spec.ts`, `ConversionHubTranscriptHost.spec.ts`, `src/router/routes.spec.ts` | Regression-proof quality and contract coverage | 30 min |
| `.artifacts/pr-0386-transcript-button-token-proof/20260625T201832Z/` | Intake/running/completed visual proof and DOM class evidence | 20 min |

**Total estimated time:** ~2.5 hours

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep ordinary transcript operating buttons on route-local neutral token surfaces instead of shared CTA primitives. | Fixes the governed drift without rewriting the shared design system or leaking planner-specific button recipes into the transcript lane. | [x] |
| Keep selector controls visually selected with explicit fill while command buttons stay neutral. | Matches the `PR-0383` compact curated-app token decision and avoids ambiguous state. | [x] |
| Allow the new helper only as a narrow route-local class constant, not a second design system. | The helper is scoped to transcript operating controls and does not preserve any retired button contract or introduce a broader compatibility alias. | [x] |
| Accept the authenticated dev/test fixture route as proof support only because it stays gated behind `requiresAuth` and `DEV`/`test` mode. | Preserves the approved HuleEdu browser-session entry mechanics and keeps the proof surface out of production bundles. | [x] |

## Review Checklist

- [x] Scope stayed frontend-only with no backend, API, producer, or persistence changes.
- [x] Start, cancel, reset, selected-format download, and selected-format Mina filer controls no longer use filled CTA styling.
- [x] Selector controls retain explicit selected-state styling and remain visually distinct from commands.
- [x] Visible copy and emitted behavior remain unchanged in the reviewed command surfaces.
- [x] `transcriptCommandButtonClasses.ts` stays narrow, typed, and route-local rather than becoming a compatibility shim or second design system.
- [x] Focused tests prove rendered controls and emitted outcomes, not only helper internals.
- [x] Retained visual proof covers intake, running, and completed/export states.
- [x] The inspection route remains authenticated and dev/test-only.
- [x] `.codex/handoff.md` remains under the 200-line budget.

## Findings

No findings. I did not identify any blocker, high, medium, low, or nit issue in
the reviewed PR-0386 scope.

## Review Feedback

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-25`
**Verdict:** `approved`

### Required Changes

None.

### Suggestions

None.

## Verification

- Reviewed `AGENTS.md`, `.codex/handoff.md`, `docs/index.md`,
  `.codex/rules/025-curated-apps.md`, `.codex/rules/045-huleedu-design-system.md`,
  `.codex/rules/070-testing-standards.md`, `.codex/rules/075-browser-automation.md`,
  `.codex/rules/096-review-workflow.md`, the routed `ruthless-code-review`,
  `testing`, `agent-docs-governance`, `integrated-frontend-stack`, and
  `skriptoteket-testing` guidance, plus the governing `PR-0386` and `PR-0383`
  backlog docs.
- `git diff -- .codex/handoff.md docs/backlog/prs/pr-0386-st-37-04-audio-transcription-button-token-remediation.md frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkflowRailShell.vue frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkflowRailShell.spec.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptFormatterExportPanel.vue frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptFormatterExportPanel.spec.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/transcriptCommandButtonClasses.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptUiInspectionView.vue`
  Confirmed the implementation scope is bounded to the claimed frontend/docs surfaces.
- `wc -l .codex/handoff.md`
  Passed the handoff budget check at `197` lines.
- `pdm run fe-test -- --run src/views/apps/conversion-hub-transcript/TranscriptWorkflowRailShell.spec.ts src/views/apps/conversion-hub-transcript/TranscriptFormatterExportPanel.spec.ts`
  Passed: `2` files, `5` tests.
- `pdm run fe-test -- --run src/router/routes.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkflowRailShell.spec.ts src/views/apps/conversion-hub-transcript/TranscriptFormatterExportPanel.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.pr0351.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.spec.ts src/views/apps/conversion-hub-transcript/ConversionHubTranscriptHost.pr0351.spec.ts`
  Passed: `7` files, `38` tests.
- `pdm run fe-type-check`
  Passed.
- `pdm run fe-lint`
  Passed.
- `pdm run fe-build`
  Passed with the repo’s existing dynamic-import and chunk-size warnings only.
- Reviewed `.artifacts/pr-0386-transcript-button-token-proof/20260625T201832Z/intake.png`,
  `running.png`, `completed-export.png`, and `proof-summary.json`.
  Verified neutral command-button classes for start/cancel/reset/download/save,
  verified selected-format navy fill remains on the selector family only, and
  confirmed the retained proof covers all three requested states.
- Reviewed `src/router/routes.ts` and `src/router/routes.spec.ts`.
  Confirmed the transcript UI-inspection route is `requiresAuth: true` and only
  registered for `import.meta.env.DEV || import.meta.env.MODE === "test"`.
- I did not rerun a live HuleEdu browser-session proof in this review pass.
  Approval relies on the retained authenticated artifact, the auth-gated
  route definition, and the focused frontend gates above.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0386` | Created the retained independent review record for PR-0386. |
| 2 | `REV-PR-0386` | Recorded the bounded review scope, independent verification evidence, and approved verdict. |
