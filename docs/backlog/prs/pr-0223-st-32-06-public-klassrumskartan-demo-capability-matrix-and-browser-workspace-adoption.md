---
type: pr
id: PR-0223
title: "ST-32-06: public Klassrumskartan demo capability matrix and browser-workspace adoption"
status: done
owners: "agents"
created: 2026-04-05
updated: 2026-04-07
stories:
  - "ST-32-06"
tags: ["frontend", "backend", "klassrumskartan", "public-access", "guest-workspace"]
dependencies:
  - "ADR-0079"
  - "ADR-0080"
  - "ST-32-04"
  - "ST-32-05"
  - "EPIC-27"
  - "EPIC-29"
acceptance_criteria:
  - "Given Klassrumskartan becomes the first concrete public browser-workspace consumer, when this slice is closed, then the public route renders the real browser-owned overview/workspace shell instead of the old placeholder."
  - "Given guest Klassrumskartan uses the browser-owned snapshot contract, when guest users author rosters, templates, grouping drafts, or seating drafts, then those changes persist locally and survive overview round-trips and reloads without owner-scoped API fallthrough."
  - "Given guest mode still needs import preview, when a roster import preview runs, then it uses the dedicated public helper seam and not authenticated owner-scoped import endpoints."
  - "Given guest mode should feel like the same teacher tool rather than a separate demo product, when the public browser-owned workspace renders, then it keeps the shared Klassrumskartan layout and final-state registration/system copy while unfinished account-only surfaces stay hidden rather than explained with temporary implementation copy."
  - "Given the authenticated guest-upgrade lane is already owned by ST-32-05, when this public baseline ships, then the guest snapshot remains browser-owned until a later authenticated Klassrumskartan visit explicitly offers import/discard/postpone."
---

## Problem

`ST-32-04` and `ST-32-05` froze the browser-owned guest snapshot and
authenticated upgrade boundary. `PR-0223` then needed to prove one bounded
implementation baseline: Klassrumskartan can run as the first real public
browser-workspace consumer without weakening the authenticated planner host or
owner-scoped APIs.

This PR no longer owns every remaining guest-mode gap. It is intentionally
closed around the shipped baseline so later guest Smart, export, and local
history follow-through can live in separate slices.

## Delivered scope

This PR now represents the shipped checkpoints 1-3 baseline:

- the public Klassrumskartan route no longer renders a placeholder or demo
  stub; it now renders the real overview shell
- public overview state is bootstrapped from the browser-owned guest snapshot
  seam through a dedicated guest controller/view
- guest roster/template create, edit, delete, and selection persist back into
  the browser-owned guest snapshot lane
- guest roster import preview stays on the dedicated public/stateless seam only:
  - `/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview`
- the public shell now swaps between overview and a dedicated guest planner
  shell for `Grupper` and `Sittplatser`
- guest grouping/seating drafts resume from the same browser-owned snapshot,
  survive overview round-trips, preserve overview-selected classroom state, and
  survive reload in the same browser workspace
- authenticated Klassrumskartan orchestration remains separate and unchanged
- checkpoint-1 presentation stays honest:
  - the final registration/system message is shown
  - temporary implementation helper copy is not shown
  - unfinished public capabilities stay hidden rather than pretending to work

## Frozen boundary retained from this slice

`PR-0223` keeps the public browser-workspace baseline explicit:

- guest mode is the same teacher-facing workspace product, not a separate demo
  layout
- guest state remains browser-owned until a later authenticated upgrade
- public helper behavior must stay on dedicated public seams
- guest mode must not fall through to owner-scoped authenticated
  `/api/v1/apps/...` endpoints when a public seam is absent

The remaining Smart/history distinction was clarified later in `ADR-0080`:

- solver-based Smart parity belongs to guest follow-on work
- history-based Smart and `Use history` remain account-only
- guest checkpoints do not create a guest Smart-history lane

## Remaining implementation extracted on 2026-04-07

The rest of `ST-32-06` is no longer carried in this PR.

- Guest `Regler`, expandable Smart settings drawer parity, and solver-based
  public Smart runs now live in
  [PR-0231](./pr-0231-st-32-06-guest-regler-workspace-solver-smart-parity-and-expandable-smart-settings-drawer.md).
- Guest local undo/redo parity, direct-download export, checkpoint continuity
  limits, and account-only history/recovery affordance polish now live in
  [PR-0232](./pr-0232-st-32-06-guest-local-draft-parity-direct-download-export-and-account-only-history-affordance-polish.md).

## Verification retained for this slice

Local proof captured for the delivered baseline:

- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/ClassroomPlannerEntryView.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/PublicAppHostView.spec.ts`
- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/ClassroomPlannerEntryView.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/PublicAppHostView.spec.ts src/views/apps/components/CreateRosterModal.spec.ts src/views/apps/components/CreateRoomTemplateModal.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- `pdm run python -m scripts.playwright_pr_0223_public_guest_overview_checkpoint2_check --base-url http://127.0.0.1:5173`
- live browser proof on `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` showed:
  - the public route renders the real overview shell with final registration
    copy
  - guest can create, edit, and delete rosters and room templates in the
    browser-owned workspace
  - `Grupper` and `Sittplatser` reopen from the same guest snapshot across
    overview round-trips and reloads
  - no owner-scoped authenticated planner/catalog/draft/export API seam was
    used during the retained network audit

## Notes

- `PR-0223` is intentionally narrower now than the original long-form planning
  draft so the shipped public baseline stays reviewable.
- Follow-on guest parity work should cite this PR as the delivered baseline,
  not reopen it as a catch-all planning container.
