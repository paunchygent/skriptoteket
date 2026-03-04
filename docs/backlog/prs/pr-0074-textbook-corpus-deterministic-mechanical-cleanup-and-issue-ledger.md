---
type: pr
id: PR-0074
title: "Textbook corpus — deterministic mechanical cleanup and issue ledger"
status: done
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

## Implementation notes (2026-03-04)

1. Added deterministic mechanical cleanup script:
   - `scripts/build_textbook_corpus_mechanical_cleanup.py`
   - Copy-only behavior (source markdown is never modified in place).
2. Added explicit no-autofix protection:
   - Protected section detection for answer/task zones.
   - Standalone numeric page-line candidates in protected zones are queued for manual review (not auto-converted).
3. Added machine-readable artifacts:
   - mechanical output markdown
   - issue ledger JSONL
   - manual queue JSONL
   - transform log JSON
   - run summary JSON
4. Added deterministic unit tests:
   - `tests/unit/scripts/test_build_textbook_corpus_mechanical_cleanup.py`
5. Added CLI alias:
   - `pdm run textbook-corpus-mechanical`
6. Executed on full OCR textbook:
   - Input:
     `/Users/olofs_mba/Documents/Repos/html_to_pdf_handout_templates/Kemi/Syntes 1 - hela boken (1).full_ocr.md`
   - Output root:
     `.artifacts/textbook_corpus/mechanical-kemi`
   - Summary:
     - `transform_count=71`
     - `issue_count=649`
     - `manual_queue_count=63`
   - Issue distribution:
     - `image_marker_present=586`
     - `long_line_extreme=57`
     - `protected_zone_page_anchor_candidate=4`
     - `heading_artifact_dots=2`

## Rollback plan

- Remove mechanical output and ledgers from this slice.
- Keep immutable raw baseline from PR-0073 intact.
