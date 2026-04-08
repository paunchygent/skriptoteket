---
type: pr
id: PR-0245
title: "ST-32-05 follow-up: empty guest snapshot and zero-effect import UI reconciliation"
status: ready
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
stories:
  - "ST-32-05"
tags:
  [
    "frontend",
    "klassrumskartan",
    "guest-upgrade",
    "import-policy",
    "remediation",
    "ui-reconciliation",
  ]
dependencies:
  - "ADR-0079"
  - "ST-32-04"
  - "ST-32-05"
  - "PR-0221"
  - "PR-0233"
acceptance_criteria:
  - "Given the authenticated Klassrumskartan host finds a browser-owned guest snapshot record whose summary has no rosters, templates, smart-rule sets, checkpoints, grouping draft, or seating draft, when the guest-upgrade gate initializes, then the stale empty browser snapshot is cleared silently and the authenticated planner continues without showing the import prompt."
  - "Given an authenticated guest-upgrade preview or commit returns a structured receipt with zero `created`, `reused`, `skipped`, and `conflicted` items, when the frontend updates the authenticated host shell, then it does not render the `import complete` success summary."
  - "Given the frontend sees a zero-effect commit receipt for a snapshot summary that still claims teacher-facing content, when the authenticated guest-upgrade flow resolves, then the frontend preserves the browser snapshot and keeps the teacher on the prompt/error lane instead of silently presenting a successful import."
  - "Given the authenticated Klassrumskartan host opens immediately after a no-op guest-upgrade attempt, when the route shell chooses a home roster, then any already-existing backend roster is not misrepresented as newly imported by guest-upgrade UI copy."
---

## Problem

Live authenticated Klassrumskartan behavior on 2026-04-08 exposed a frontend
truth-gap in the `ST-32-05` guest-upgrade lane:

- the browser gate prompts on any `ready` guest snapshot, even if the snapshot
  contains no importable teacher-facing content
- the authenticated success summary renders for any non-conflicted commit
  receipt, even if the receipt contains zero created/reused/skipped/conflicted
  items
- after that no-op path, the authenticated planner reboots into the user's
  already-existing backend roster, which can make the UI look like a class list
  was imported when the backend actually recorded no new roster, template,
  draft, or checkpoint writes

This is not the backend `500` fixed by `PR-0233`. It is a separate
frontend-reconciliation problem: the route shell currently treats "snapshot
exists" and "import had a real effect" as the same thing.

## Goal

Make the authenticated Klassrumskartan guest-upgrade UI tell the truth when
browser storage contains only an empty snapshot and when an authenticated
preview/commit produces an all-zero receipt.

## Non-goals

- No changes to the authenticated guest-upgrade backend route shape.
- No changes to the non-destructive import policy or asset dedupe semantics.
- No redesign of the broader authenticated Klassrumskartan overview shell.
- No new global guest-import center outside the existing route-scoped seam.

## Implementation plan

1. Add a small frontend helper that defines:
   - what counts as meaningful guest snapshot summary content
   - what counts as a meaningful guest-upgrade receipt outcome
2. Update `useClassroomPlannerGuestUpgrade.ts` so initialization:
   - clears truly empty browser guest snapshots before preview/prompt
   - refuses to mark an all-zero commit receipt as a completed import
   - preserves suspicious non-empty browser snapshots if a commit still returns
     an all-zero receipt
3. Update `ClassroomPlannerEntryView.vue` to defend against rendering the
   success summary when the stored receipt has no effectful items.
4. Lock the behavior in focused Vitest coverage and re-prove the authenticated
   route live in the browser.

## Test plan

- `pdm run fe-test -- --run src/views/apps/useClassroomPlannerGuestUpgrade.spec.ts src/views/apps/ClassroomPlannerEntryView.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live authenticated browser proof on `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
  showing:
  - empty guest snapshot no longer prompts
  - zero-effect guest-upgrade does not show the import-complete summary

## Rollback plan

- Revert the frontend guest-upgrade reconciliation helper and the
  authenticated entry-shell changes together if the prompt or post-import
  summary regresses legitimate import flows.
- Keep rollback narrow; do not revert the backend route/import-policy hardening
  already shipped in `PR-0221` and `PR-0233`.

## References

- Story owner:
  [ST-32-05](../stories/story-32-05-authenticated-upgrade-orchestration-and-idempotent-import-policy.md)
- Initial authenticated guest-upgrade foundation:
  [PR-0221](pr-0221-st-32-05-authenticated-upgrade-orchestration-and-idempotent-import-policy-foundation.md)
- Template-reuse/remap hardening:
  [PR-0233](pr-0233-st-32-05-follow-up-authenticated-guest-upgrade-template-reuse-and-seat-remap-hardening.md)
