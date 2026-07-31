---
type: story
id: ST-SKRIPT-21-02
title: 'Migration: retire html-to-pdf-preview + update tests'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: user closure 2026-07-31
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-21
acceptance_criteria:
- Given production seed profile is used, when the script bank is seeded, then the
  `html-to-pdf-preview` tool is not seeded/published as a production tool.
- Given the Conversion Hub curated app exists, when Playwright E2Es run, then they
  exercise conversion through the curated app (not `/tools/html-to-pdf-preview/run`)
  while still validating session file persistence + vault save flows.
- Given unit tests previously depended on `html_to_pdf_preview.py`, when tests are
  run, then coverage remains high and tests validate the new v2-driven conversion
  behavior rather than local WeasyPrint-specific details.
retired_ids:
- ST-21-02
---

## Context

### Context

Multiple code paths hardcode the legacy tool slug `html-to-pdf-preview`:

- Script bank registration: `src/skriptoteket/script_bank/bank.py` (seed group is currently production-visible)
- Playwright E2Es:
  - `scripts/playwright_st_12_05_session_file_persistence_e2e.py`
  - `scripts/playwright_st_14_36_vault_ui_e2e.py`
- Unit tests: `tests/unit/test_html_to_pdf_preview.py`
- Diagnostics script: `scripts/diagnose_edit_ops.py`

This story removes production reliance on that legacy tool and migrates tests to the Conversion Hub curated app.

### PR Tasks (ordered)

- [ ] 1. PR-0066: Migrate E2Es + unit tests + disable prod seeding of `html-to-pdf-preview`

### Notes

- Preferred "disable without shims" approach:
  change `seed_group` from `CURATED` to `TEST` in `src/skriptoteket/script_bank/bank.py`
  so `--profile prod` seeding no longer publishes it.

## Epic Contract Slice

The source material below remains authoritative for this section.

## Contract Inputs

The source material below remains authoritative for this section.

## Live Verification Plan

Verification expectations remain in the retained source material below.

## Non-Goals

The source boundaries and recovery limits remain preserved below.

## Notes

The source material below remains authoritative for this section.

## Decision And Assumption Ledger

The source material below remains authoritative for this section.

## Plan Document Review

The source material below remains authoritative for this section.

## Story Closeout Review

The source material below remains authoritative for this section.
