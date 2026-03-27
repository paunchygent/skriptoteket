---
type: story
id: ST-27-02
title: "Klassrumskartan — Export checkpoints for smart history"
status: ready
owners: "agents"
created: 2026-03-25
epic: "EPIC-27"
dependencies: ["EPIC-24", "ST-26-01", "ST-27-01"]
acceptance_criteria:
  - "Given a teacher completes a seating export with changed assignments for one class list / roster, when the export succeeds, then the system records one eligible seating checkpoint for smart-history use."
  - "Given a teacher repeats an export without changing the relevant assignments, when the export succeeds again, then the system does not create a duplicate checkpoint for that unchanged state."
  - "Given seating checkpoints are deduplicated, when the system computes the seating assignment hash, then it hashes normalized seating state only: deterministic placed student-to-seat assignments plus unplaced students, excluding export layout or presentation details."
  - "Given the teacher has only autosave, undo/redo, or abandoned draft state, when smart history is evaluated, then those draft mechanics are not treated as eligible checkpoints."
  - "Given class-global `Keep apart`, `Keep near`, and `Närmare läraren` rules already exist for the roster, when seating checkpoints are recorded, then those checkpoints remain separate history artifacts and do not become the authoritative home for those rules."
  - "Given `Use history` is enabled for smart seating and a student does not have `Närmare läraren`, when multiple eligible seating checkpoints exist, then those checkpoints are the only source used to balance that student's teacher-distance more fairly over time."
  - "Given a student has an explicit `Närmare läraren` rule, when seating history is evaluated, then the default teacher-distance fairness balancing is cancelled or strongly downweighted for that student."
  - "Given smart grouping wants to use prior seating context, when eligible seating checkpoints exist, then grouping may consume them for relation carry-over and for the optional seating-distance signal without treating raw drafts as history."
  - "Given later grouping export artifacts create grouping checkpoints, when those exports are introduced, then grouping checkpoints become the primary grouping-history source while seating checkpoints remain a secondary mode-crossing source for relation carry-over and optional seating-distance signals."
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
- Seating checkpoints are the first practical history source because seating export already exists.
- Teacher-distance fairness-over-time must also read from those explicit checkpoints only; autosave
  and undo/redo are never a substitute history source.
- The checkpoint registry should be designed so later grouping exports can plug into it cleanly.
