---
type: story
id: ST-27-02
title: "Klassrumskartan — Export checkpoints for smart history"
status: done
owners: "agents"
created: 2026-03-25
updated: 2026-03-27
epic: "EPIC-27"
dependencies: ["EPIC-24", "ST-26-01", "ST-27-01"]
acceptance_criteria:
  - "Given a teacher completes a seating export with changed assignments for one class list / roster, when the export succeeds, then the system records one eligible seating checkpoint for smart-history use."
  - "Given a teacher repeats an export without changing the relevant assignments, when the export succeeds again, then the system does not create a duplicate checkpoint for that unchanged state."
  - "Given seating checkpoints are deduplicated, when the system computes the seating assignment hash, then it hashes normalized seating state only: deterministic placed student-to-seat assignments plus unplaced students, excluding export layout or presentation details."
  - "Given the teacher has only autosave, undo/redo, or abandoned draft state, when smart history is evaluated, then those draft mechanics are not treated as eligible checkpoints."
  - "Given class-global `Keep apart`, `Keep near`, and `Närmare läraren` rules already exist for the roster, when seating checkpoints are recorded, then those checkpoints remain separate history artifacts and do not become the authoritative home for those rules."
ui_impact: "No direct new teacher-facing flow beyond smarter history eligibility"
data_impact: "Yes (checkpoint registry and assignment-hash dedupe)"
---

## Context

Smart assignment needs history, but the accepted product direction is clear that raw drafts and
undo/redo trails are the wrong source. This story establishes explicit export-backed checkpoints as
the only eligible history input for V1.

## Notes

- Start with export-backed checkpoints only.
- Keep checkpoints separate from roster-global smart-rule ownership.
- Assignment-hash dedupe is required so repeated export testing does not pollute history.
- For seating v1, the canonical hash should cover normalized assignment state, not rendered export
  artifacts or presentation payloads.
- Checkpoint identity is roster plus normalized room-context identity; copied template ids,
  seat/fixture ids, seat zones, and fixture labels must not fork otherwise identical room geometry.
- Seating checkpoints are the first practical history source because seating export already exists.
- Teacher-distance fairness-over-time must also read from those explicit checkpoints only; autosave
  and undo/redo are never a substitute history source.
- The checkpoint registry should be designed so later grouping exports can plug into it cleanly.
- Later smart seating/grouping stories consume these checkpoints; this story only ships the
  checkpoint foundation and dedupe boundary they depend on.
