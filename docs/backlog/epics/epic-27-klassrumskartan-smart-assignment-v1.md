---
type: epic
id: EPIC-27
title: "Klassrumskartan smart assignment v1"
status: active
owners: "agents"
created: 2026-03-25
updated: 2026-05-12
outcome: "Teachers can opt into smart grouping and smart seating through small per-draft mode toggles, author a deliberately small visual rule model from a dedicated `Regler` workspace, rely on export-backed checkpoints rather than draft history, and receive short teacher-language reasons without being exposed to solver jargon."
dependencies: ["ADR-0069", "ADR-0071", "ADR-0072", "ADR-0074", "EPIC-24", "EPIC-26"]
---

## Scope

- Reintroduce smart assignment through a fresh, explicitly approved contract rather than by
  reviving the removed solver-era surface.
- Keep the visible teacher model intentionally small and authored from a dedicated `Regler`
  workspace rather than from per-student drawer editing or always-open task-pane panels:
  - `Keep apart`
  - `Keep near`
  - `Use history`
- Allow one seating-only rule:
  - `Närmare läraren`
- Allow one classroom-template-scoped hard seating rule:
  - `Fast plats`
- Allow one explicit grouping-only seat-distance toggle without turning it into a fifth shared
  smart control.
- Make `Regler` the first-class home for smart-rule creation and editing:
  - the classroom-faithful view is the default authoring map when a classroom exists
  - `Planeringskarta` remains an optional abstract planning map and always keeps one normalized
    alphabetical planning layout independent of classroom geometry or the active seating draft
  - existing `Sittschema` wording denotes the classroom-faithful projection; future teacher-facing
    copy should use `Klassrumsvyn` / `klassrumsvyn`
  - `Fast plats` is authored only from the classroom-faithful view because it needs one physical
    student-to-seat target
  - both map views share the same active tool and selection state where the active tool can be
    validly used from both maps
- Keep `Sittplatser` and `Grupper` calm:
  - retain the small `Smart` toggle in the main task toolbar
  - allow one compact or collapsed smart summary near that toggle
  - route rule editing through a small settings affordance near `Smart` that opens `Regler`
  - do not keep or introduce full rule editing inside task-pane drawers or overflow affordances
- Add one small `Smart` toggle per mode, persisted per draft and defaulting to `off` on new drafts.
- Keep `Slumpa` as the main action in both `Grupper` and `Sittplatser`.
- Delete the old visible planner metadata semantics and related persistence without migration or
  compatibility work.
- Introduce normalized relational persistence for smart preferences, relation rules, checkpoints,
  and smart-toggle state.
- Define export-backed checkpoints as the only smart-history source.
- Deduplicate checkpoint creation by assignment hash so unchanged repeated exports do not create new
  history entries.
- Ship smart seating and smart grouping from day one.
- Let smart grouping use seating distance only through an explicit teacher-facing toggle:
  `Ska hur nära de sitter räknas?`
- Keep the backend authoritative for smart scoring and search.
- Keep explanations short, teacher-facing, and low-drama.

## Out of scope

- Reusing autosave state, undo/redo stacks, or abandoned drafts as history inputs.
- Preserving or mapping forward the old visible planner-note / proximity / stability model.
- Re-exposing multi-slider planning profiles, suggestion panels, or raw score surfaces.
- Making the student metadata drawer a primary smart-rule editing workflow.
- Making a seating/grouping task-pane drawer or overflow menu the primary smart-rule editing
  workflow.
- Shipping a general teacher-facing checkpoint UX before export-backed checkpoints are trusted.
- Treating grouping and seating as one blended visible task.
- Long-form debugging or score-breakdown panels for teachers.
- New compatibility shims for deleted planner semantics.

## Risks

- The `Slumpa` + `Smart` toggle design must stay readable so teachers do not confuse random and
  smart behavior.
- The toolbar-based class overview must stay comprehensible so rule selection and rule targets are
  visible without overwhelming the teacher.
- The new `Regler` workspace must feel clearly different from `Sittplatser` and `Grupper` without
  becoming a heavier secondary application inside the planner.
- The classroom-view-first refinement must not erase the useful planning-map abstraction; teachers
  should still be able to choose `Planeringskarta` deliberately.
- `Fast plats` is a hard seating invariant, so implementation must prevent partial draft writes
  when fixed placements conflict with roster or room state.
- Tool state, cursor state, and student-selection feedback must stay strong enough that rule
  authoring feels deliberate rather than hidden behind weak color-only affordances.
- Smart grouping history partly depends on seating export checkpoints until grouping export
  checkpoints exist later under the export lane.
- The package must define one explicit no-checkpoint behavior for `Use history`: first runs with no
  eligible checkpoints soft-degrade to no-history Smart runs, while drafts and undo/redo still never
  become history inputs.
- Deleting old visible semantics is the cleaner design choice, but it makes rollback to the older
  model intentionally expensive.
- Solver latency or weak explanations could reduce trust even if the assignment quality is strong.
- The current shared frontend planner persistence contract must be replaced before more smart
  seating/grouping implementation lands, or draft-local and roster-global transitions will keep
  recoupling under new bug names.

## Stories

- [x] [ST-27-01: Smart-assignment contract reset and control model](../stories/story-27-01-klassrumskartan-smart-assignment-contract-reset-and-control-model.md)
- [x] [ST-27-02: Export checkpoints for smart history](../stories/story-27-02-klassrumskartan-export-checkpoints-for-smart-history.md)
- [x] [ST-27-06: Planner session lanes and transition matrix remediation](../stories/story-27-06-klassrumskartan-planner-session-lanes-and-transition-matrix-remediation.md)
- [x] [ST-27-03: Smart seating v1](../stories/story-27-03-klassrumskartan-smart-seating-v1.md)
- [x] [ST-27-07: Dedicated rules workspace with separate planning and seating maps](../stories/story-27-07-klassrumskartan-rules-workspace-and-dual-map-authoring.md)
- [x] [ST-27-08: Retire student notes drawer and seating-mode student activation](../stories/story-27-08-klassrumskartan-retire-student-notes-drawer-and-seating-mode-student-activation.md)
- [ ] [ST-27-09: Fixed-seat rules and classroom-view-first rule authoring](../stories/story-27-09-klassrumskartan-fixed-seat-rules-and-classroom-view-first-authoring.md)
- [ ] [ST-27-04: Smart grouping v1](../stories/story-27-04-klassrumskartan-smart-grouping-v1.md)
- [ ] [ST-27-05: Smart explanations and rerun messaging](../stories/story-27-05-klassrumskartan-smart-explanations-and-alternate-options.md)

## Notes

- This epic intentionally follows the accepted fundamentals/export direction rather than reopening
  the old slice-2 solver shell.
- The metadata drawer is not part of the intended end-state; the remaining retirement/removal
  slice is now tracked under `ST-27-08`.
- `Regler` is now the dedicated smart-rule authoring home:
  - as of `ST-27-09`, the classroom-faithful view is the default when a classroom exists
  - `Planeringskarta` is the optional normalized map
  - `Sittschema` is the older name for the exact-current-arrangement map; future user-facing copy
    should use `Klassrumsvyn`
  - `Sittplatser` and `Grupper` keep compact summary/settings affordances only
- `Planeringskarta` must remain a clean alphabetical planning abstraction even after classroom or
  seating context exists; it must not collapse back into the classroom canvas.
- `Fast plats` is a classroom-template-scoped hard rule:
  - it binds one roster student to one physical seat in the active classroom template
  - it cannot be authored from `Planeringskarta`
  - from `Planeringskarta`, the `Fast plats` tool should prompt:
    `Fast plats kräver en fysisk plats. Vill du byta till klassrumsvyn?`
  - choosing `Ja` switches to the classroom view and activates the tool
  - choosing `Nej` or closing the prompt leaves the teacher on `Planeringskarta`
  - Smart seating must seed fixed placements before solving remaining seats and score all other
    rules against the merged fixed + candidate mapping
- The first visible smart-rule interaction model is locked:
  - `Nära läraren` uses the same rail-owned pending selection plus explicit create/save confirmation
    as the relationship rules, but still persists as one consolidated seating-only rule
  - `Keep apart` / `Keep near` are 2+ student clusters authored through multi-select plus explicit
    commit
  - overlapping visible relationship clusters are blocked in V1
- Smart history must start from explicit exports, not from draft mechanics.
- When `Historik` is on but no eligible checkpoint exists, Smart seating/grouping must run without
  history, report `used_history=false`, and avoid warning/blocking the teacher in this normal
  first-run state.
- The first grouping-history source may be seating checkpoints before grouping export checkpoints
  exist later under the export lane.
- `ST-27-06` is now a required remediation slice before `ST-27-03` and `ST-27-04`.
- `ST-27-07` is the required UI cut-over before `ST-27-04` and `ST-27-05`; it replaces the
  seating-embedded rule editor with a shared `Regler` workspace plus compact task-pane summaries.
- `ST-27-08` removes the remaining seating-only notes drawer and click-activation semantics so
  `Sittplatser` becomes drag/drop-only while `Regler` remains the sole click-based student
  authoring surface.
- Later smart seating/grouping work must build on the explicit session-controller + lane split, not
  on planner-wide flush/save-status/shared-timer semantics.
- `ST-27-09` refines the completed `ST-27-07` map-default contract without reopening its
  implementation: `Planeringskarta` remains stable and abstract when selected, but the classroom
  view becomes the default and the only fixed-seat authoring surface.
- A review doc must approve this package before implementation begins.

## Planned Follow-up (2026-05-05)

- ST-27-09 is ready:
  - PR-0296 captured the fixed-seat and classroom-view-first contract in docs.
  - PR-0297 is the backend slice for fixed-seat persistence, hard validation, and score-aware
    solver seeding.
  - PR-0298 is the frontend slice for `Klassrumsvyn` defaulting, the `Fast plats` prompt,
    fixed-seat markers, and live UX proof.

## Planned Follow-up (2026-05-11)

- ST-27-05 now owns the Smart history first-run refinement:
  - PR-0316 should remove the normal no-checkpoint block for Smart seating and Smart grouping
  - the run should still be checkpoint-honest by reporting `used_history=false`
  - no draft, undo/redo, abandoned draft, history-drawer, or public guest local state may be used as
    a substitute history source
  - eligible export/share checkpoints should continue to set `used_history=true` and influence the
    solver

## Planned Follow-up (2026-05-12)

- ST-27-03 / ST-27-05 now own the Smart seating diversity correction:
  - PR-0317 adds history-backed diversity scoring for accepted share/export checkpoints
  - the solver must vary full layouts, per-student seat/zone use, `Håll nära` unordered pair
    placement, and `Håll isär` unordered seat-pair and block spread patterns across new drafts
  - pair swaps inside the same two seats do not count as distinct teacher-visible patterns
  - `Fast plats` remains the hard non-variable exception

## Implementation Summary (as of 2026-04-01)

- ST-27-01 is done:
  - PR-0147 reset the seating-only smart-rule contract
  - PR-0149 delivered the seating smart-rule authoring surface and visible V1 interaction model
  - PR-0151 completed the roster-owned smart-rule boundary, concurrency/autosave/hydration hardening, forward repair migration, Docker dev auto-upgrade path, and approved implementation review
- ST-27-06 is done:
  - PR-0152 split the planner into one session controller, one draft persistence lane, one
    roster smart-rule lane, one smart-rule UI bucket, and explicit transition policies
  - the route shell now uses explicit workspace/export/exit transition APIs, `clearWorkspace()`
    stays teardown-only, exit timeout returns confirm-discard, and late responses are ignored
- ST-27-02 is done:
  - PR-0150 shipped the seating checkpoint registry, normalized assignment hashing, normalized
    room-context dedupe, migration coverage, and export-success checkpoint wiring
  - later smart seating/grouping stories still consume this checkpoint foundation rather than being
    part of ST-27-02 itself
- ST-27-03 is done:
  - PR-0154 shipped the backend-owned smart seating run, strict checkpoint-history read seam,
    draft-local `Use history` control, `Smart`/`Slumpa` branching, teacher-edge inference, and
    rerun diversity on the same control
  - close-out included live proof on `http://127.0.0.1:5173`, reviewer-follow-up fixes for the
    strict last-12 history seam plus route-level `404` / `409` / `422` HTTP coverage, and a final
    clean `skriptoteket_reviewer` pass
- ST-27-07 is done with the corrected planning-map contract on 2026-04-01:
  - PR-0155 now keeps `Planeringskarta` as a permanent abstract alphabetical planning grid instead
    of reusing classroom geometry when seating/classroom context exists
  - the planning roster no longer shows the seating-only guidance banner; that guidance now stays
    scoped to the seating projection path
  - `Sittschema` remains the only classroom-faithful map projection
  - close-out included focused Vitest coverage, Vue typecheck, frontend lint, a refreshed
    Playwright proof script, and live proof on `http://127.0.0.1:5173`
- ST-27-08 is done on 2026-04-01:
  - PR-0186 removed the remaining `PlannerMetadataDrawer` surface and all seating-mode
    selected-student activation semantics so `Sittplatser` student click is now a true no-op
  - the active planner contract no longer carries `student_planning_meta` through frontend state,
    draft PATCHes, API DTOs, domain/application models, repository snapshots/history, or the live
    database schema
  - migration `b7f9c2d4e1a6_drop_classroom_planner_student_notes.py` drops the retired table and
    strips the old key from persisted draft history payloads
- The frontend prerequisite for ST-27-04 is now satisfied by PR-0152 plus PR-0154.
- 2026-03-27 planning refinement:
  - `ST-27-07` and `PR-0155` now carry the dedicated `Regler` workspace, the
    `Planeringskarta` / `Sittschema` toggle, and the summary-link cut-over so later smart seating
    and smart grouping UI does not grow around task-pane drawers
