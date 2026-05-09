---
type: review
id: REV-PR-0311
title: "Review: PR-0311 phone room-template modal stabilization"
status: approved
owners: "agents"
created: 2026-05-10
updated: 2026-05-10
reviewer: "codex"
prs:
  - PR-0311
links:
  - ST-24-04
  - ST-29-16
  - PR-0310
---

## TL;DR

`PR-0311` is approved after second-pass review. The two retained blockers are
resolved: the focused phone test and retained Playwright proof now exercise the
exact `Sittplats` touch create/remove contract, and delete failure handling
keeps the stable Swedish recovery copy.

## Problem Statement

This review checks whether the phone room-template modal stabilization can
close `PR-0311` without regressing the teacher-facing modal footer, required
name recovery, desktop hover previews, or phone touch placement semantics.

## Proposed Solution

The implementation keeps the contained room-template modal, moves phone footer
geometry into CSS-owned layout, adds compact icon-supported footer actions,
focuses the classroom-name input on missing-name save attempts, and suppresses
room-builder ghost previews for touch/coarse-pointer input while preserving
desktop hover previews.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0311-st-24-04-phone-room-template-modal-stabilization.md` | Scope, acceptance criteria, copy lock, proof obligations | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/components/CreateRoomTemplateModal.vue` | Footer actions, save/delete lifecycle, missing-name recovery | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/components/RoomTemplateEditorSidebar.vue` | Name field focus and field-level validation | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/components/RoomTemplateBuilderSurface.vue` | Touch/no-hover suppression and desktop hover preservation | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/useRoomTemplateEditorState.ts` | Placement reducer and hover-state cleanup | 8 min |
| `frontend/apps/skriptoteket/src/assets/klassrumskartan-responsive-workspace.css` | Phone modal/footer geometry | 5 min |
| `scripts/playwright_pr_0311_phone_room_template_modal.py` | Retained phone/desktop proof scope | 8 min |
| `frontend/apps/skriptoteket/src/views/apps/components/CreateRoomTemplateModal.phone.spec.ts` | Focused phone modal tests | 5 min |

**Total estimated time:** ~61 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep the contained modal and fix sticky footer geometry with CSS | Matches PR non-goals and layout-geometry doctrine | [x] |
| Replace disabled missing-name save with field-level recovery and focus | Matches the required-name acceptance criterion | [x] |
| Suppress ghost previews only for touch/coarse-pointer input | Preserves desktop hover behavior while fixing phone ambiguity | [x] |
| Keep destructive delete failure copy unchanged | Required by the PR UX copy lock unless a visible issue is documented | [x] |

## Review Checklist

- [x] Scope is bounded to the phone room-template modal and builder touch state.
- [x] Docs-as-code authority exists under `PR-0311`.
- [x] Footer first-render and compact labels have automated and browser proof.
- [x] Missing-name recovery has automated and browser proof.
- [x] The exact `Sittplats` touch contract has retained proof.
- [x] Destructive delete failure copy remains unchanged.

## Review Feedback

**Reviewer:** `codex`
**Date:** `2026-05-10`
**Verdict:** `changes_requested`

### Required Changes

1. Add direct `Sittplats` touch proof for the PR acceptance criterion.

   `PR-0311` specifically requires that a phone touch on the room builder with
   selected tool `Sittplats` shows a seat only from real editor state, leaves no
   stuck ghost preview, and keeps the second tap as the existing same-seat
   removal rule. The current focused phone test and retained Playwright proof
   switch to `Whiteboard`, then only assert that the ghost overlay is absent.
   Add assertions that keep `Sittplats` selected, tap a cell, verify one real
   seat is rendered/persisted from editor state, verify the ghost overlay is
   absent, then tap the same cell again and verify the seat is removed.

2. Restore the governed delete failure copy.

   The PR copy lock says destructive confirmation/delete error copy should stay
   unchanged unless the implementation path exposes a visible issue. The current
   catch path now surfaces `deleteError.message`, which can expose backend or
   transport copy and diverges from the existing Swedish recovery message. Keep
   the stable delete failure text for the user-facing modal message, or document
   and test a deliberate copy change in the PR scope before changing it.

### Suggestions (Optional)

- Add a small geometric assertion in the retained Playwright proof for the
  whiteboard's saved bounding box touching the room edge, so the wall-attached
  fixture obligation is more than screenshot-only evidence.

### Passing Checks Observed

- `pdm run fe-test -- --run CreateRoomTemplateModal RoomTemplateBuilderSurface useRoomTemplateEditorState roomTemplateEditorDomain`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q`
- `pdm run ruff check scripts/_playwright_classroom_planner.py scripts/playwright_pr_0302_toolbar_overflow_parity.py scripts/playwright_pr_0303_public_guest_overview_distribution.py scripts/playwright_pr_0310_phone_fixed_seat_rules_map.py scripts/playwright_pr_0311_phone_room_template_modal.py`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
- `pdm run python -m scripts.playwright_pr_0311_phone_room_template_modal --start-backend --start-vite`

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0311` | Recorded retained review verdict as `changes_requested` with two required fixes and observed verification evidence. |
| 2 | `frontend/apps/skriptoteket/src/views/apps/components/CreateRoomTemplateModal.phone.spec.ts` | Added direct `Sittplats` touch proof that first tap creates a real builder seat, leaves no ghost overlay, and second tap removes the same real seat. |
| 3 | `scripts/playwright_pr_0311_phone_room_template_modal.py` | Updated retained phone proof to exercise the same `Sittplats` create/remove contract instead of the prior `Whiteboard` no-ghost-only path. |
| 4 | `frontend/apps/skriptoteket/src/views/apps/components/CreateRoomTemplateModal.vue` | Restored stable Swedish delete failure recovery copy instead of surfacing backend error message text. |

### Second Pass

**Reviewer:** `codex`
**Date:** `2026-05-10`
**Verdict:** `approved`

Both retained blockers are resolved.

- `CreateRoomTemplateModal.phone.spec.ts` proves `Sittplats` touch placement
  creates one real builder seat, leaves no ghost overlay, and removes the same
  seat on the second tap.
- `scripts/playwright_pr_0311_phone_room_template_modal.py` runs the same
  phone `Sittplats` create/remove contract in the retained browser proof.
- `CreateRoomTemplateModal.vue` restores
  `Det gick inte att ta bort klassrummet. Försök igen eller stäng dialogrutan.`
  as the user-facing delete failure recovery copy.

Passing second-pass checks:

- `pdm run fe-test -- --run CreateRoomTemplateModal RoomTemplateBuilderSurface useRoomTemplateEditorState roomTemplateEditorDomain`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q`
- `pdm run ruff check scripts/_playwright_classroom_planner.py scripts/playwright_pr_0302_toolbar_overflow_parity.py scripts/playwright_pr_0303_public_guest_overview_distribution.py scripts/playwright_pr_0310_phone_fixed_seat_rules_map.py scripts/playwright_pr_0311_phone_room_template_modal.py`
- `pdm run python -m scripts.playwright_pr_0311_phone_room_template_modal --start-backend --start-vite`
