---
type: epic
id: EPIC-27
title: "Klassrumskartan smart assignment v1"
status: active
owners: "agents"
created: 2026-03-25
updated: 2026-03-27
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
- Allow one explicit grouping-only seat-distance toggle without turning it into a fifth shared
  smart control.
- Make `Regler` the first-class home for smart-rule creation and editing:
  - `Planeringskarta` is the default authoring map and preserves room geometry while placing
    students alphabetically in simple seat-reading order
  - `Sittschema` is an optional alternative that mirrors the current seating draft when one exists
  - both map views share the same active tool and selection state
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
- Tool state, cursor state, and student-selection feedback must stay strong enough that rule
  authoring feels deliberate rather than hidden behind weak color-only affordances.
- Smart grouping history partly depends on seating export checkpoints until grouping export
  checkpoints exist later under the export lane.
- The package must define one explicit no-checkpoint behavior for `Use history`; teams must not
  infer their own fallback semantics.
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
- [ ] [ST-27-07: Dedicated rules workspace and dual-map authoring](../stories/story-27-07-klassrumskartan-rules-workspace-and-dual-map-authoring.md)
- [ ] [ST-27-04: Smart grouping v1](../stories/story-27-04-klassrumskartan-smart-grouping-v1.md)
- [ ] [ST-27-05: Smart explanations and rerun messaging](../stories/story-27-05-klassrumskartan-smart-explanations-and-alternate-options.md)

## Notes

- This epic intentionally follows the accepted fundamentals/export direction rather than reopening
  the old slice-2 solver shell.
- The metadata drawer may remain for advanced notes/history, but it is not the primary smart-rule
  authoring concept.
- `Regler` is now the dedicated smart-rule authoring home:
  - `Planeringskarta` is the default normalized map
  - `Sittschema` is the optional exact-current-arrangement map
  - `Sittplatser` and `Grupper` keep compact summary/settings affordances only
- The first visible smart-rule interaction model is locked:
  - `Närmare läraren` is unary click-to-toggle
  - `Keep apart` / `Keep near` are 2+ student clusters authored through multi-select plus explicit
    commit
  - overlapping visible relationship clusters are blocked in V1
- Smart history must start from explicit exports, not from draft mechanics.
- The first grouping-history source may be seating checkpoints before grouping export checkpoints
  exist later under the export lane.
- `ST-27-06` is now a required remediation slice before `ST-27-03` and `ST-27-04`.
- `ST-27-07` is the required UI cut-over before `ST-27-04` and `ST-27-05`; it replaces the
  seating-embedded rule editor with a shared `Regler` workspace plus compact task-pane summaries.
- Later smart seating/grouping work must build on the explicit session-controller + lane split, not
  on planner-wide flush/save-status/shared-timer semantics.
- A review doc must approve this package before implementation begins.

## Implementation Summary (as of 2026-03-27)

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
- The frontend prerequisite for ST-27-04 is now satisfied by PR-0152 plus PR-0154.
- 2026-03-27 planning refinement:
  - `ST-27-07` and `PR-0155` now carry the dedicated `Regler` workspace, the
    `Planeringskarta` / `Sittschema` toggle, and the summary-link cut-over so later smart seating
    and smart grouping UI does not grow around task-pane drawers
