---
type: pr
id: PR-0311
title: "ST-24-04: phone room-template modal stabilization"
status: done
owners: "agents"
created: 2026-05-09
updated: 2026-05-10
stories:
  - "ST-24-04"
tags: ["frontend", "ux", "klassrumskartan", "room-builder", "small-screen"]
dependencies:
  - "PR-0103"
  - "PR-0116"
  - "PR-0136"
  - "PR-0284"
  - "PR-0310"
acceptance_criteria:
  - "Given the room-template modal opens on a phone-sized viewport, when it first renders, then the destructive, cancel, and save actions are present in a deterministic sticky bottom footer without waiting for a second modal visit or later layout jump."
  - "Given the sticky footer renders on phone, when the action labels are shown, then they use compact copy and icons: `Radera`, `Avbryt`, and `Spara` for edit mode, with no two-row wrapping at the iPhone 15 Pro portrait review width."
  - "Given the teacher taps a room-builder cell on a touch device, when the selected tool is `Sittplats`, then the visible seat appears only because the seat exists in editor state; no hover/ghost preview remains stuck after the tap."
  - "Given the pointer-capable desktop room builder still renders, when the teacher moves across the grid before placing a seat or fixture, then the existing hover ghost preview remains available."
  - "Given the classroom name is required, when the teacher tries to save without a name, then the modal shows a short Swedish error message, scrolls/focuses the classroom-name input, and does not silently ignore the save action."
  - "Given the classroom-name panel renders on phone, when compared to the other modal panels, then it aligns edge-to-edge with the same modal content column and does not appear shifted to the right."
---

## Problem

The phone room-template modal has several related small-screen regressions:

- the bottom actions (`Radera klassrum`, `Avbryt`, `Spara klassrum`) are flaky on
  first render and only settle into the expected position after another modal
  visit
- the footer labels are too long for the phone width and wrap into two rows
- touch placement keeps a hover/ghost preview stuck on the grid, so the teacher
  can mistake a preview for a real placed seat and tap again, accidentally
  removing it
- the classroom-name panel is horizontally misaligned with the other panels
- saving without a required classroom name fails silently because the save
  button is disabled instead of helping the teacher fix the missing field

## Goal

Stabilize the contained room-template editor on phone while preserving the
desktop/laptop builder model.

The teacher should get a deterministic phone modal:

- sticky footer actions always visible from first render
- compact footer buttons that fit one row
- touch placement shows only real saved editor state, not sticky hover previews
- name field alignment matches the surrounding panels
- missing-name save attempts focus the name input and show clear recovery copy

## Non-goals

- No new room-object types.
- No saved room-template data-model change.
- No desktop redesign of the builder.
- No removal of pointer hover previews on desktop/laptop.
- No broad replacement of the modal with a full route or wizard.

## Recommended Solution

Treat phone and touch as a no-hover editing mode. The existing ghost preview is
good desktop UX, but it becomes misleading on a touch screen because there is no
stable hover intent. The phone/touch rule should be:

- tap places or removes the real object according to existing editor rules
- the cell shows a seat or fixture only after editor state contains it
- ghost placement renders only for pointer hover/focus devices where preview is
  meaningful

For the footer and name validation, keep the modal as a contained editor and fix
the shell:

- make the footer sticky and first-render deterministic through CSS-owned
  layout, not delayed measurement
- use compact labels and icons:
  - `Radera` with trash icon
  - `Avbryt` with cancel/close icon
  - `Spara` with save icon
- keep the footer in one row at `393x852` and `390x844`
- replace disabled-save silence with focus + system message for the required
  name field

## PR-0310 Alignment

`PR-0310` changed the phone seating and fixed-seat authoring surfaces to use a
simplified classroom map with explicit touch semantics. This slice must reuse
the same principle in the room-template editor: phone touch input should produce
visible room objects only from real editor state, not from sticky hover or ghost
preview state.

Implementation guidance:

- keep no-hover behavior local to touch/coarse-pointer room-builder input
- preserve desktop pointer hover previews unchanged
- avoid adding always-visible overlay affordances that compete with small phone
  grid cells
- keep wall-attached fixtures visually wall-attached in phone proof
- use CSS-owned modal/footer geometry instead of post-render measurement

## Current Frontend Entry Points

- `CreateRoomTemplateModal.vue`: modal shell, submit/delete lifecycle, footer,
  and error message.
- `RoomTemplateEditorSidebar.vue`: classroom-name field and tool panels.
- `RoomTemplateBuilderSurface.vue`: interactive grid, hover events, ghost
  overlay, and viewport containment.
- `useRoomTemplateEditorState.ts`: selected tool, hover/ghost state, parsed
  seats/fixtures, validation, and placement reducer.
- `roomTemplateEditorDomain.ts`: placement helpers and same-tool removal rules.
- `klassrumskartan-responsive-workspace.css`: phone modal sizing, builder
  viewport, sidebar, and footer overrides.

## Implementation Plan

1. Add focused tests for the phone modal footer and save validation before
   changing behavior.
2. Update the modal footer so edit mode uses compact button text:
   - `Radera`
   - `Avbryt`
   - `Spara`
3. Add icon support using the repo's existing icon surface or Lucide-backed
   shared icons already used by Klassrumskartan controls.
4. Keep the sticky footer deterministic on first render:
   - footer is inside the modal panel
   - modal body owns scrolling
   - footer does not depend on a post-render layout pass to become visible
   - safe-area bottom padding is included on phone
5. Add a save attempt path even when the name is missing:
   - do not silently no-op
   - show field-level copy such as `Ge klassrummet ett namn innan du sparar.`
   - scroll/focus the classroom-name input
   - do not duplicate this field validation in the dismissible modal-level
     system message
   - keep backend submit blocked until local validation passes
6. Align the classroom-name panel by fixing the phone sidebar/content column
   spacing. Do not add per-field margins that diverge from the rest of the
   modal panels.
7. Detect touch/no-hover interaction for the builder:
   - either suppress ghost rendering through a prop/class when
     `(hover: none)` / coarse pointer applies
   - or clear hover state immediately after touch/click placement
   - do not remove desktop hover/focus ghost behavior
8. Add tests for touch placement:
   - first tap creates one real seat
   - no ghost seat remains visible after placement
   - second tap removes the real seat only because that is the existing
     same-seat toggle rule
9. Add phone proof that wall-attached fixtures remain attached to the modal room
   boundary and that the sticky footer does not cover the editable grid.
10. Run phone and desktop browser proof.

## UX Copy Lock

- Footer edit-mode labels: `Radera`, `Avbryt`, `Spara`.
- Missing-name message: `Ge klassrummet ett namn innan du sparar.`
- Keep destructive confirmation/delete error copy unchanged unless the
  implementation path exposes a visible issue.

## Test Plan

- `pdm run fe-test -- --run CreateRoomTemplateModal RoomTemplateBuilderSurface useRoomTemplateEditorState roomTemplateEditorDomain`
- Add focused assertions for:
  - sticky footer actions present on first render
  - compact footer labels in edit mode
  - save attempt without a name focuses the name field and shows recovery copy
  - touch/no-hover placement does not render a stuck ghost preview
  - desktop hover ghost preview still renders
  - phone wall fixtures remain attached to the wall boundary after the modal
    layout changes
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q`
- `pdm run ruff check scripts/_playwright_classroom_planner.py scripts/playwright_pr_0302_toolbar_overflow_parity.py scripts/playwright_pr_0303_public_guest_overview_distribution.py scripts/playwright_pr_0310_phone_fixed_seat_rules_map.py scripts/playwright_pr_0311_phone_room_template_modal.py`
- `git diff --check`
- Live browser proof:
  - phone `393x852`: open edit classroom, verify footer first render, one-row
    buttons, aligned name panel, missing-name focus/message, and touch seat
    placement
  - desktop `1440x900`: verify hover ghost preview remains available and
    footer layout is unchanged
  - `pdm run python -m scripts.playwright_pr_0311_phone_room_template_modal --base-url http://127.0.0.1:5173`

## Implementation Closeout

Implemented and verified on 2026-05-09.

- Updated the room-template modal footer to use compact icon-supported actions:
  `Radera`, `Avbryt`, and `Spara` in edit mode, with phone CSS forcing one
  sticky row at the iPhone 15 Pro portrait proof width.
- Changed missing-name save from a disabled/silent path to an actionable save
  attempt that shows `Ge klassrummet ett namn innan du sparar.` as field-level
  validation and focuses the classroom-name input without duplicating it in the
  dismissible modal-level system message.
- Aligned the classroom-name field as a real editor panel in the same column as
  the other phone modal panels.
- Suppressed room-builder ghost previews on touch/coarse-pointer input while
  preserving desktop pointer hover previews; the phone `Sittplats` proof now
  verifies first tap creates a real editor-state seat and second tap removes it.
- Restored stable Swedish delete failure recovery copy in line with the PR copy
  lock.
- Added the shared `IconSave` wrapper and updated retained classroom-create
  Playwright helpers to accept the compact `Skapa` label.
- Added retained browser proof in
  `scripts/playwright_pr_0311_phone_room_template_modal.py`.

Verification:

- `pdm run fe-test -- --run CreateRoomTemplateModal RoomTemplateBuilderSurface useRoomTemplateEditorState roomTemplateEditorDomain`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run python -m scripts.playwright_pr_0311_phone_room_template_modal --base-url http://127.0.0.1:5173`

Browser artifacts:

- `.artifacts/playwright-pr-0311-phone-room-template-modal/phone-create-modal-recovery.png`
- `.artifacts/playwright-pr-0311-phone-room-template-modal/phone-edit-modal-footer.png`
- `.artifacts/playwright-pr-0311-phone-room-template-modal/desktop-hover-ghost-preview.png`

## Retained Review

`REV-PR-0311` is `approved` as of 2026-05-10 after second-pass review.
Resolved retained blockers:

1. Add direct `Sittplats` touch proof that creates one real seat from editor
   state, leaves no ghost overlay, and keeps the second tap as same-seat
   removal.
2. Restore the governed delete failure recovery copy instead of surfacing raw
   `Error.message` text.

## Rollback Plan

Revert the modal/footer/touch changes and tests. The rollback must preserve
existing room-template persistence, same-tool toggle removal, and desktop zoom
behavior.
