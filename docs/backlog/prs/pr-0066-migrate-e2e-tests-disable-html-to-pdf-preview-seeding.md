---
type: pr
id: PR-0066
title: "Conversion Hub: migrate E2E/unit tests + disable html-to-pdf-preview seeding in prod"
status: ready
owners: "agents"
created: 2026-03-01
updated: 2026-03-01
stories:
  - "ST-21-02"
tags: ["tests", "migration", "curated-apps"]
acceptance_criteria:
  - "Playwright E2Es that currently use `/tools/html-to-pdf-preview/run` are migrated to the Conversion Hub curated app while preserving the intent (session file persistence + vault save flows)."
  - "`html-to-pdf-preview` is no longer seeded/published for the production seed profile."
  - "Unit tests that directly import `html_to_pdf_preview.py` are removed or migrated to validate v2-driven conversion behavior, keeping coverage high."
---

## Problem

Today, production and tests depend on the legacy tool `html-to-pdf-preview` registered in the script bank
(`src/skriptoteket/script_bank/bank.py`). After we ship the curated Conversion Hub, this becomes legacy slop and a
security/maintenance liability.

## Goal

- Update tests to use the curated Conversion Hub surface.
- Disable production seeding of `html-to-pdf-preview` (clean break; we update our callers).

## Non-goals

- No changes to Sir Convert-a-Lot itself (this repo consumes v2).

## Implementation plan

- [ ] Disable prod seeding:
  - change `seed_group` of the `html-to-pdf-preview` ScriptBankEntry from `CURATED` to `TEST` in
    `src/skriptoteket/script_bank/bank.py` so `--profile prod` seeding omits it.
- [ ] Migrate Playwright scripts:
  - `scripts/playwright_st_12_05_session_file_persistence_e2e.py` (replace tool-run flow with curated app conversion)
  - `scripts/playwright_st_14_36_vault_ui_e2e.py` (replace tool-run flow; keep vault save + reuse assertions)
  - Prefer artifact assertions like "download is a valid PDF" rather than hardcoded `output/<name>.pdf`.
- [ ] Update unit tests:
  - remove/migrate `tests/unit/test_html_to_pdf_preview.py` to new conversion hub units (backend client orchestration)
  - preserve the valuable HTML rewrite/idempotency tests only if the curated app still uses them; otherwise delete.
- [ ] Update any diagnostics/scripts hardcoding the slug:
  - `scripts/diagnose_edit_ops.py` (stop assuming this tool exists in seeded DB).
- [ ] Verification:
  - `pdm run test`
  - relevant Playwright scripts run successfully against local dev.

## Test plan

- `pdm run test`
- `pdm run ui-smoke` (or run the specific Playwright scripts above)

## Rollback plan

- Revert the seed-group change and restore old tests if the curated app is not ready for production yet.
