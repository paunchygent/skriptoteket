---
type: story
id: ST-14-33
title: "Script bank curation + group generator tool"
status: ready
owners: "agents"
created: 2026-01-12
epic: "EPIC-14"
dependencies:
  - "ST-14-19"
  - "ADR-0056"
acceptance_criteria:
  - "Given script bank seeding runs with profile=dev, when seeded, then curated + test tools are created in dev/staging DB."
  - "Given script bank seeding runs with profile=prod, when seeded, then only curated tools are created (test tools are not seeded at all)."
  - "Given curated script bank tools are updated, when executed, then they read inputs/actions/settings via runner toolkit helpers and action field kinds use enum."
  - "Given a roster file (CSV/XLSX) and a group size, when the group generator tool runs, then it outputs student groups and exports an artifact."
  - "Given a class roster is saved in tool settings, when the tool runs again, then the teacher can select exactly one saved class and assign a user-provided group set name."
---

## Context

We need a strict separation between curated production tools and dev/test tools, while keeping dev/staging seeded with
both sets for QA. At the same time, curated tools should demonstrate the latest runner toolkit helpers for inputs,
actions, and settings. A new teacher-facing “group generator” tool is also needed as a curated example.

## Notes

- Curated set must include:
  - `demo_inputs.py`
  - `ist_vh_mejl_bcc.py`
  - `yrkesgenerator.py`
  - `markdown_to_docx.py`
  - `html_to_pdf_preview.py`
- Test/demo tools must not be seeded into production at all.
- Group generator tool requirements:
  - Accept CSV/XLSX (incl. Google Sheets export) with student names.
  - Accept group size input.
  - Optionally accept previous groups input to avoid repeats.
  - Persist class rosters in settings (memory.json) for reuse.
  - Allow selecting one saved class at a time and naming the group set.
