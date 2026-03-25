---
type: epic
id: EPIC-27
title: "Klassrumskartan smart assignment v1"
status: active
owners: "agents"
created: 2026-03-25
outcome: "Teachers can opt into smart grouping and smart seating through small per-draft mode toggles, use a deliberately small visible rule model, rely on export-backed checkpoints rather than draft history, and receive short teacher-language reasons without being exposed to solver jargon."
dependencies: ["ADR-0069", "ADR-0071", "ADR-0072", "ADR-0074", "EPIC-24", "EPIC-26"]
---

## Scope

- Reintroduce smart assignment through a fresh, explicitly approved contract rather than by
  reviving the removed solver-era surface.
- Keep the visible teacher model intentionally small:
  - `Support seat`
  - `Keep apart`
  - `Keep near`
  - `Use history`
- Allow one explicit grouping-only seat-distance toggle without turning it into a fifth shared
  smart control.
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
- Shipping a general teacher-facing checkpoint UX before export-backed checkpoints are trusted.
- Treating grouping and seating as one blended visible task.
- Long-form debugging or score-breakdown panels for teachers.
- New compatibility shims for deleted planner semantics.

## Risks

- The `Slumpa` + `Smart` toggle design must stay readable so teachers do not confuse random and
  smart behavior.
- Smart grouping history partly depends on seating export checkpoints until grouping export
  checkpoints exist later under the export lane.
- The package must define one explicit no-checkpoint behavior for `Use history`; teams must not
  infer their own fallback semantics.
- Deleting old visible semantics is the cleaner design choice, but it makes rollback to the older
  model intentionally expensive.
- Solver latency or weak explanations could reduce trust even if the assignment quality is strong.

## Stories

- [ ] [ST-27-01: Smart-assignment contract reset and control model](../stories/story-27-01-klassrumskartan-smart-assignment-contract-reset-and-control-model.md)
- [ ] [ST-27-02: Export checkpoints for smart history](../stories/story-27-02-klassrumskartan-export-checkpoints-for-smart-history.md)
- [ ] [ST-27-03: Smart seating v1](../stories/story-27-03-klassrumskartan-smart-seating-v1.md)
- [ ] [ST-27-04: Smart grouping v1](../stories/story-27-04-klassrumskartan-smart-grouping-v1.md)
- [ ] [ST-27-05: Smart explanations and alternate options](../stories/story-27-05-klassrumskartan-smart-explanations-and-alternate-options.md)

## Notes

- This epic intentionally follows the accepted fundamentals/export direction rather than reopening
  the old slice-2 solver shell.
- Smart history must start from explicit exports, not from draft mechanics.
- The first grouping-history source may be seating checkpoints before grouping export checkpoints
  exist later under the export lane.
- A review doc must approve this package before implementation begins.
