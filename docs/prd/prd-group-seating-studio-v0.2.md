---
type: prd
id: PRD-group-seating-studio-v0.2
title: "Curated App: Klassrumskartan"
status: superseded
product: "skriptoteket"
version: "0.2"
owners: "agents"
created: 2026-03-21
updated: 2026-03-21
---

Superseded by [PRD-group-seating-studio-v0.3](prd-group-seating-studio-v0.3.md).

## Summary

Klassrumskartan is a teacher-first planning app for classroom grouping and seating.

The product direction in v0.2 resets the app away from a solver-first surface and back toward
clear classroom-management fundamentals:

- the landing page is the default first interaction
- grouping and seating are separate teacher workflows
- manual control comes first
- smart behavior remains possible, but it stays hidden until each concept is defined and approved
- saved outputs are named teacher-owned artifacts, not anonymous technical snapshots

## Goals

- Let teachers create, edit, save, cancel, close, and delete classes and classrooms from one
  intuitive landing page.
- Let teachers select one class and one classroom, then open the planner immediately.
- Make `Grupper` and `Sittplatser` the only top-level planner modes in the default workflow.
- Support manual grouping and manual seating as complete tasks before more intelligence is exposed.
- Preserve practical helpers such as `Slumpa`, but scope them to the active teacher mode.
- Let teachers save meaningful named groupings and seating arrangements that can later be found,
  edited, and deleted from the user vault.
- Preserve the normalized draft core from ADR-0069 while giving drafts an explicit server-owned
  lifecycle.

## Non-goals

- Re-exposing undeclared solver-era controls, rule-engine language, or advanced validation panels
  in the default teacher workflow.
- Treating `lesson_mode_id` as a visible top-level teacher mode in the fundamentals workflow.
- Making whole-workspace finalize snapshots the primary teacher-facing save model.
- Requiring teachers to understand profile weights, trade-off sliders, or planning jargon in order
  to complete basic grouping or seating tasks.
- Delivering PDF/XLSX export in this product reset, even if later stories build on the saved-output
  model introduced here.

## User Roles

- **Teacher**: creates and maintains classes/classrooms, groups students, seats students, saves
  arrangements, and later uses optional smart-placement support.
- **Admin / superuser**: governs app availability and infrastructure, but is not the primary
  product user for this workflow.

## Requirements

### 1. Landing page and asset management

- The landing page is the default first interaction.
- It focuses on selecting and managing classes and classrooms, not on planning-rule panels.
- Teachers can create, edit, save, cancel, close, and delete classes and classrooms intuitively.
- Dialogs must remain usable on normal laptop viewports and close safely.
- The planner opens when one class and one classroom are selected.
- The teacher can always return from the planner to the landing page.

### 2. Draft lifecycle and resume

- Resume remains supported, but it is explicit rather than automatic.
- The server owns draft lifecycle semantics such as `active`, `abandoned`, and `superseded`.
- Draft creation should resolve a compatible active draft when appropriate instead of silently
  accumulating orphaned mutable drafts.
- Draft edits must use robust optimistic concurrency semantics.

### 3. Planner mode separation

- The only top-level modes in the default planner workflow are `Grupper` and `Sittplatser`.
- Mode separation is reflected in routing, browser history, visible controls, randomize behavior,
  save behavior, and validation scope.
- Grouping should not leak seating-specific context by default.
- Seating should not leak grouping-specific context by default.
- Advanced controls remain hidden from the default shell.

### 4. Grouping fundamentals

- Teachers can assign students into groups manually from the roster.
- Teachers can add, remove, rename, and restructure groups.
- Group panels/layout must adapt so the current student cards fit cleanly inside the group surface.
- `Slumpa` in `Grupper` creates or reshuffles groups only.
- Individual groups can have teacher-defined names.
- Completed group assignments can be saved as named saved groupings.

### 5. Seating fundamentals

- Teachers can place students on seats manually.
- Teachers can move, swap, and remove students without hidden automation overriding those actions.
- `Slumpa` in `Sittplatser` creates or reshuffles seating only.
- Completed seating assignments can be saved as named saved seating arrangements.
- The room view should support a credible classroom representation for later export stories,
  including fixtures such as whiteboard, teacher desk, windows, and door.

### 6. Saved outputs and vault surfacing

- Saved groupings and saved seating arrangements are teacher-owned artifacts with meaningful names.
- If the teacher does not provide a name, the default name is the saved date plus time.
- Saved outputs can be edited later, renamed later, and deleted later.
- Editing a saved output creates a new immutable revision and must not mutate the live draft by
  accident.
- Saved outputs appear in the user vault together with the relevant settings used when saved.
- The planner domain remains authoritative; the vault is a synchronized projection.

### 7. Smart placement boundaries

- Teacher-authored placement knowledge remains a valid long-term feature direction.
- Smart defaults may quietly support grouping and seating later, but they do not dominate the
  default fundamentals workflow.
- Advanced settings, pair rules, zone preferences, history rules, and tuning controls stay outside
  the default main view until each concept is separately approved.

### 8. Product and architecture constraints

- ADR-0069's normalized draft core remains the structural foundation.
- The curated app continues to use bespoke planner endpoints rather than generic tool/run plumbing.
- Existing pure-domain rule logic, handler orchestration, and UoW/repository boundaries should be
  preserved while the workflow contracts are reshaped.

## Metrics

- A teacher can reach the planner from the landing page without hidden blockers.
- A teacher can complete a manual grouping workflow without interacting with seating controls.
- A teacher can complete a manual seating workflow without interacting with grouping controls.
- A teacher can save a named grouping or seating arrangement and find it again in the user vault.
- Resumable draft work is discoverable without auto-hijacking the teacher away from the landing
  page.
