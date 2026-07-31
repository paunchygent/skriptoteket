---
type: story
id: ST-SKRIPT-14-35
title: 'Tool datasets: per-user CRUD + picker'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-14
acceptance_criteria:
- Given a user has datasets for a tool, when they open the tool run view, then a dataset
  picker lists their datasets and allows selecting one for the run.
- Given a user saves a dataset with a name and payload, when they submit, then it
  is stored per user+tool and appears in the picker.
- Given a user edits or deletes a dataset, when they confirm, then the change is persisted
  and does not affect other users.
- Given a dataset is selected, when a run starts, then the runner receives it in memory
  per ADR-0058 (dataset + dataset_meta).
- Given a dataset payload exceeds size limits or is invalid JSON, when saving, then
  the UI shows an actionable validation error.
retired_ids:
- ST-14-35
dependencies:
- ADR-SKRIPT-0058
---

## Context
Tools like group generators need reusable, per-user lists (classes, rosters, templates). Settings alone are not enough.

## Epic Contract Slice
The source record did not define a separate section for this package heading.

## ADR Coverage
The source record did not define a separate section for this package heading.

## Contract Inputs
The source record did not define a separate section for this package heading.

## Live Verification Plan
The source record did not define a separate section for this package heading.

## Non-Goals
The source record did not define a separate section for this package heading.

## Notes
- Integrate with the "settings suggestions" UX (ST-14-34) once available so tools can propose dataset saves.
- Keep dataset selection optional; tools must handle `memory["dataset"]` missing.

## Decision And Assumption Ledger
The source record did not define a separate section for this package heading.

## Plan Document Review
The source record did not define a separate section for this package heading.

## Story Closeout Review
The source record did not define a separate section for this package heading.
