---
type: pr
id: PR-0074
title: "Textbook corpus — deterministic mechanical cleanup and issue ledger"
status: ready
owners: "agents"
created: 2026-03-04
updated: 2026-03-04
stories:
  - "ST-22-01"
tags: ["data", "quality", "pipeline"]
acceptance_criteria:
  - "Mechanical cleanup output is deterministic (same input hash => same output hash)."
  - "No-autofix semantic zones are enforced (tasks, answer keys, formulas, definitions are not auto-rewritten)."
  - "All uncertain or semantic issues are emitted to machine-readable ledgers and manual restoration queue files."
---

## Problem

Raw OCR markdown contains many mechanical defects, but automatic cleanup can also corrupt meaning if unrestricted.

## Goal

Perform only low-risk deterministic cleanup and explicitly surface everything that needs human/manual restoration.

## Non-goals

- No semantic reconstruction by script.
- No direct pristine promotion from mechanical output.

## Implementation plan

1. Reuse strict normalization utilities for bounded mechanical transforms.
2. Add textbook-specific protected-zone detection for semantic sections.
3. Emit:
   - mechanical output markdown,
   - issue ledger,
   - manual restoration queue.
4. Log all transforms with before/after fingerprints.
5. Add fixture tests for known problematic regions.

## Test plan

- Golden-fixture tests for deterministic output.
- Negative tests proving protected zones are not rewritten.
- Quality report comparison before/after cleanup.

## Rollback plan

- Remove mechanical output and ledgers from this slice.
- Keep immutable raw baseline from PR-0073 intact.
