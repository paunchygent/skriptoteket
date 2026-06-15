---
type: review
id: REV-PR-0355
title: "Review: PR-0355 transcript cancel slot rail remediation"
status: approved
owners: "agents"
created: 2026-06-15
updated: 2026-06-15
reviewer: "independent-reviewer-pr0355"
prs:
  - PR-0355
links:
  - ST-21-08
  - EPIC-21
  - PR-0356
---

## TL;DR

Approved. The scoped PR-0355 transcript UI slice satisfies its governed
contract: the `Avbryt` row is always mounted above `Starta transkribering`,
stays invisible/disabled/out of tab order while idle, remains visible but inert
while cancellation is pending, drops the misleading square icon, and updates
the empty workspace intro copy to the required teacher-intent wording.

This approval is intentionally limited to the PR-0355 transcript slice in the
mixed local PR-0356 worktree. Deploy/native production proof remains out of
scope until the slice is separated, which matches the governing PR non-goal and
current handoff state.

## Problem Statement

This review verifies that PR-0355 closes the narrow transcript-rail remediation
without reopening transcript runtime/export ownership, introducing layout jump
workarounds, or relying on stale docs. The review scope is limited to the
teacher-visible transcript rail/workspace copy plus the retained docs/handoff
evidence attached to this slice.

## Proposed Solution

Keep the cancel action as one direct rail control with reserved layout:

- mount `Avbryt` above `Starta transkribering` at all times;
- hide it with CSS visibility plus disabled/focus-state constraints while idle;
- keep it visible and disabled while cancellation is pending;
- remove the square icon; and
- replace the empty workspace intro copy with
  `Ladda upp en ljudfil eller en video som du vill ha transkriberad`.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0355-st-21-08-transcript-cancel-slot-rail-remediation.md` | Governing scope, acceptance, proof boundary | 10 min |
| `docs/backlog/stories/story-21-08-transcript-speaker-overlays-and-replay-formatter-exports.md` | Parent story alignment | 10 min |
| `docs/backlog/epics/epic-21-curated-app-conversion-hub.md` | Epic summary and out-of-scope proof note | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkflowRailShell.vue` | Cancel-slot DOM order, visibility, focus, icon removal | 20 min |
| `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkflowRailShell.spec.ts` | Rail behavioral proof truthfulness | 15 min |
| `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.vue` | Empty-state copy | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts` | Copy regression proof | 10 min |
| `.codex/handoff.md` | Retained verification evidence and scope note | 10 min |
| `.artifacts/playwright-pr-0349-transcript-parity-live/20260615T141002Z/proof-summary.json` | Existing retained remote-proof E2E evidence | 10 min |

**Total estimated time:** ~105 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Cancel row stays permanently mounted in the rail | This is the simplest truthful way to reserve the row without JS-owned geometry. | [x] |
| Idle cancel state must be invisible, disabled, and unfocusable | Matches the PR contract while preserving layout occupancy. | [x] |
| Pending-cancel state must stay visible but inert | Avoids a disappearing destructive action during the user-visible abort attempt. | [x] |
| Empty workspace intro must use teacher-intent wording | This was an explicit copy requirement added to the governed PR. | [x] |
| Native deploy proof is not an approval requirement for this pass | The workspace is mixed with PR-0356 and the governing PR explicitly excludes deploy from this slice. | [x] |

## Review Checklist

- [x] Docs-as-code authority exists and matches the requested PR-0355 slice.
- [x] Review scope stays limited to the transcript rail/workspace slice, not PR-0356 work.
- [x] `Avbryt` remains above `Starta transkribering` in the rail DOM order.
- [x] Idle cancel state is invisible, disabled, `aria-hidden`, and removed from tab order.
- [x] Pending cancel stays visible and disabled.
- [x] No square/checkbox-like icon remains in the active cancel control.
- [x] Empty workspace intro copy matches the user-provided Swedish wording.
- [x] Focused tests prove user-visible behavior rather than helper internals.
- [x] Retained docs/handoff evidence correctly records that local remote-proof E2E passed.
- [x] Deploy/native production proof is explicitly marked out of scope until the PR-0355 slice is separated from PR-0356.

## Review Feedback

**Reviewer:** @independent-reviewer-pr0355
**Date:** 2026-06-15
**Verdict:** approved

### Scope Reviewed

- Governing docs: `PR-0355`, `ST-21-08`, `EPIC-21`, repo `AGENTS.md`,
  `.codex/handoff.md`, `docs/index.md`, `docs/reference/ref-review-workflow.md`,
  and targeted rules/skills for docs governance, frontend layout/testing, and
  ruthless review.
- Scoped implementation files only:
  `TranscriptWorkflowRailShell.vue`,
  `TranscriptWorkflowRailShell.spec.ts`,
  `TranscriptWorkspaceShell.vue`,
  `TranscriptWorkspaceShell.spec.ts`.
- Retained proof artifact:
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260615T141002Z/proof-summary.json`.

### Findings

No findings.

### Validation Commands And Evidence

Reviewer-ran focused checks:

```bash
git diff --check
pdm run fe-test -- --run frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkflowRailShell.spec.ts frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/TranscriptWorkspaceShell.spec.ts
```

Results:

- `git diff --check`: passed.
- Focused transcript rail/workspace Vitest: passed, `2` files / `13` tests.

Evidence inspected without rerunning long E2E:

- `.artifacts/playwright-pr-0349-transcript-parity-live/20260615T141002Z/proof-summary.json`
  records local remote-proof success with visible cancel feedback, transcript
  autosave, saved speaker overlays, four formatter downloads, and Mina filer
  save.
- `.codex/handoff.md`, `ST-21-08`, and `EPIC-21` consistently record that this
  retained proof exists and that deploy/native production proof is deferred
  until the PR-0355 slice is separated from the mixed PR-0356 branch state.

### Residual Risks / Validation Gaps

- I intentionally did not rerun the long transcript E2E because the retained
  artifact already exists, the user requested a narrow review, and the current
  change set is a localized DOM/copy remediation rather than a runtime-protocol
  change.
- Native Hemma production proof was not reviewed as a current requirement for
  approval. That remains a separate follow-up once PR-0355 is isolated from the
  mixed PR-0356 worktree.

### Decision Approvals

- [x] Reserved cancel slot contract
- [x] No misleading cancel icon
- [x] Updated teacher-intent empty copy
- [x] Truthful focused test coverage
- [x] Explicit out-of-scope native proof boundary

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `docs/backlog/reviews/review-pr-0355-transcript-cancel-slot-rail-remediation.md` | Recorded the independent review, decision, scope boundary, and validation evidence for PR-0355. |
