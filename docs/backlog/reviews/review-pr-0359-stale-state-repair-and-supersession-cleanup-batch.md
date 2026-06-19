---
type: review
id: REV-PR-0359
title: "Review: PR-0359 stale-state repair and supersession cleanup batch"
status: approved
owners: "agents"
created: 2026-06-18
updated: 2026-06-18
reviewer: "codex-independent-reviewer"
prs:
  - PR-0359
links:
  - ST-37-01
  - PR-0358
  - REF-pr-0358-active-backlog-inventory-2026-06-17
  - EPIC-37
  - REV-EPIC-37
---

## TL;DR

Approved. The working-tree patch stays docs-only, the repaired and canceled
rows match the operative `PR-0358` deep-audit queue, no `needs-decision` rows
were silently closed, `EPIC-37` remains proposed with `REV-EPIC-37` pending,
`PR-0277` and `ST-26-07` remain open, and the browser-auth cancellations keep
the required warning not to delete backend identity-token artifacts through docs
cleanup alone.

## Problem Statement

This review checks whether `PR-0359` truthfully repairs stale backlog status and
supersession state without over-closing still-governed work, bypassing the
`EPIC-37` review gate, or claiming docs-only cleanup as evidence for unrelated
backend or production behavior changes.

## Proposed Solution

Approve only if the patch:

1. limits itself to backlog/docs state repair
2. uses the `PR-0358` deep audit and revised queue as the governing evidence
3. preserves explicit warnings and review gates that still matter
4. updates parent summaries when children are closed
5. leaves unresolved or `needs-decision` items open

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0359-st-37-01-stale-state-repair-and-supersession-cleanup-batch.md` | Cleanup scope, claimed repairs, gate language | 10 min |
| `docs/reference/ref-pr-0358-active-backlog-inventory-2026-06-17.md` | Deep-audit authority and revised queue | 20 min |
| `docs/backlog/stories/story-37-01-backlog-inventory-and-stale-state-repair.md` | Parent story authority and gate notes | 5 min |
| `docs/backlog/epics/epic-02-identity-and-access-control.md` | Browser-auth cancellation summary and warning preservation | 5 min |
| `docs/backlog/epics/epic-14-admin-tool-authoring.md` | File-ref, vault, editor repairs and layout-editor cancellations | 10 min |
| `docs/backlog/epics/epic-21-curated-app-conversion-hub.md` | Transcript repairs and `PR-0324` / `PR-0325` supersession | 10 min |
| `docs/backlog/epics/epic-26-klassrumskartan-explicit-exports-and-class-list-import.md` | `PR-0277` / `ST-26-07` remain open | 5 min |
| `docs/backlog/epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md` | `PR-0195`..`PR-0197` absorption record | 5 min |
| `docs/backlog/epics/epic-30-frontend-transition-continuity-for-same-shell-selectors.md` | `EPIC-30` done-state repair | 5 min |
| `.codex/handoff.md` | Current-state alignment and retained gate notes | 5 min |
| `frontend/...` and `src/...` spot checks | Current code evidence for repaired rows and supersession notes | 20 min |

**Total estimated time:** ~100 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Repair only the rows named in the deep-audit revised queue | Avoids arbitrary cleanup or silent expansion of scope | [x] |
| Leave `EPIC-37` proposed and `REV-EPIC-37` pending | Docs-only cleanup must not substitute for the epic review gate | [x] |
| Leave `PR-0277` and `ST-26-07` open | Retained review and fresh Teams unfurl proof are still missing | [x] |
| Preserve identity-token retirement warnings in the browser-auth cancellations | Docs cleanup must not imply backend artifact deletion authority | [x] |
| Approve only if the diff remains docs-only | This slice has no authority to change production code or tests | [x] |

## Review Checklist

- [x] The patch is limited to docs/backlog state repair plus `.codex/handoff.md`.
- [x] The changed rows match the operative `PR-0358` deep-audit recommendations and revised queue.
- [x] No `needs-decision` rows were silently closed.
- [x] `EPIC-37` remains `proposed` and `REV-EPIC-37` remains `pending`.
- [x] `PR-0277` and `ST-26-07` remain open with the required rationale.
- [x] Browser-auth cancellation rows preserve the warning against deleting backend identity-token artifacts without a separate backend or ops decision.
- [x] Parent epics/stories received appropriate implementation summary updates for touched children.
- [x] No production code or test files changed.
- [x] Required validation gates passed.

## Review Feedback

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-18`
**Verdict:** `approved`

### Required Changes

None.

### Suggestions (Optional)

- Keep later `EPIC-37` slices anchored to the deep-audit revision rather than
  the first-pass matrix counts or stale per-row first-pass classifications.

### Decision Approvals

- [x] Repair only the revised-queue rows
- [x] Preserve the `REV-EPIC-37` gate
- [x] Leave `PR-0277` / `ST-26-07` open
- [x] Preserve browser-auth retirement warnings
- [x] Keep the slice docs-only

### Findings

No findings.

### Evidence And Validation

- `git diff --name-only` shows only docs and handoff files; no production code
  or tests changed.
- The repaired and canceled rows match the operative `PR-0358` deep-audit
  guidance and `Revised PR-0359 Queue`, including `EPIC-30`, transcript rows
  `ST-21-05` / `ST-21-06` / `PR-0325`, editor/file-vault rows
  `ST-14-24` / `ST-14-36` / `ST-14-38` / `PR-0053` / `PR-0054` / `PR-0055` /
  `PR-0056` / `PR-0058`, browser-auth cancellations
  `ST-02-07` / `ST-02-09` / `PR-0172`, superseded `PR-0324`, generic
  `layout_editor_v1` cancellations `ST-14-25`..`ST-14-28`, and absorbed
  `ST-29-11` drafts `PR-0195`..`PR-0197`.
- Spot checks confirmed the cited current surfaces exist today:
  `frontend/apps/skriptoteket/src/components/tool-run/ToolFileFieldPicker.vue`,
  `frontend/apps/skriptoteket/src/components/ui-actions/UiActionFieldFileRef.vue`,
  `frontend/apps/skriptoteket/src/components/vault/VaultPanel.vue`,
  `frontend/apps/skriptoteket/src/components/vault/VaultPickerModal.vue`,
  `frontend/apps/skriptoteket/src/views/editor/EditorHubView.vue`,
  `frontend/apps/skriptoteket/src/components/editor/EditorToolMenu.vue`,
  `src/skriptoteket/web/api/v1/tools.py`,
  `src/skriptoteket/web/api/v1/editor/sandbox.py`,
  `src/skriptoteket/web/api/v1/vault.py`,
  `src/skriptoteket/web/api/v1/apps_conversion_hub_transcript_saves.py`,
  `frontend/apps/skriptoteket/src/router/routes.ts`,
  `frontend/apps/skriptoteket/src/views/AuthLifecycleHandoffView.vue`,
  `src/skriptoteket/infrastructure/db/models/password_reset_token.py`, and
  `src/skriptoteket/infrastructure/repositories/email_verification_token_repository.py`.
- `EPIC-30` already carried a completed implementation summary, and a current
  source scan found no live `out-in` transition usage in SPA source.
- Validation commands and outcomes:
  - `pdm run docs-validate`: passed.
  - `pdm run handoff-validate`: passed.
  - `git diff --check`: passed.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0359` | Recorded the independent review decision, evidence trail, and validation results for the docs-only cleanup batch |
