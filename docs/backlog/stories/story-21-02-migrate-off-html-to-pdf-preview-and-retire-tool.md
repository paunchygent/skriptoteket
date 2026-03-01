---
type: story
id: ST-21-02
title: "Migration: retire html-to-pdf-preview + update tests"
status: ready
owners: "agents"
created: 2026-03-01
epic: "EPIC-21"
dependencies:
  - "ST-21-01"
acceptance_criteria:
  - "Given production seed profile is used, when the script bank is seeded, then the `html-to-pdf-preview` tool is not seeded/published as a production tool."
  - "Given the Conversion Hub curated app exists, when Playwright E2Es run, then they exercise conversion through the curated app (not `/tools/html-to-pdf-preview/run`) while still validating session file persistence + vault save flows."
  - "Given unit tests previously depended on `html_to_pdf_preview.py`, when tests are run, then coverage remains high and tests validate the new v2-driven conversion behavior rather than local WeasyPrint-specific details."
ui_impact: "Yes (E2E test surface migrates to curated app UI)"
data_impact: "No (migration is in code/tests; prod disable is via seed profile + governance ops)"
---

## Context

Multiple code paths hardcode the legacy tool slug `html-to-pdf-preview`:

- Script bank registration: `src/skriptoteket/script_bank/bank.py` (seed group is currently production-visible)
- Playwright E2Es:
  - `scripts/playwright_st_12_05_session_file_persistence_e2e.py`
  - `scripts/playwright_st_14_36_vault_ui_e2e.py`
- Unit tests: `tests/unit/test_html_to_pdf_preview.py`
- Diagnostics script: `scripts/diagnose_edit_ops.py`

This story removes production reliance on that legacy tool and migrates tests to the Conversion Hub curated app.

## PR Tasks (ordered)

- [ ] 1. PR-0066: Migrate E2Es + unit tests + disable prod seeding of `html-to-pdf-preview`

## Notes

- Preferred "disable without shims" approach:
  change `seed_group` from `CURATED` to `TEST` in `src/skriptoteket/script_bank/bank.py`
  so `--profile prod` seeding no longer publishes it.
