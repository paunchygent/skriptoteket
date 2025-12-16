---
type: story
id: ST-06-04
title: "Add unit tests for script bank tools (IST guardian email extractor)"
status: done
owners: "agents"
created: 2025-12-16
epic: "EPIC-06"
acceptance_criteria:
  - "`ist_vh_mejl_bcc.py` reaches >70% coverage with behavior tests."
  - "CSV input produces a semicolon-separated email list and writes output/emails.txt."
  - "Duplicate emails are de-duplicated and normalized to lowercase."
  - "Unsupported file types return a user-friendly error HTML."
---

## Context

Script-bank tools are shipped and seeded from the repository. They should have lightweight behavior tests to prevent
regressions when refactoring or updating dependencies.

## Scope

- Add unit tests for `src/skriptoteket/script_bank/scripts/ist_vh_mejl_bcc.py`:
  - `prioritized_columns` ordering behavior.
  - `harvest_emails_from_cells` extraction + de-dup.
  - `run_tool` end-to-end for CSV: writes `emails.txt` and returns a summary HTML.
