---
type: pr
id: PR-0357
title: "ST-21-10 public Exam Converter source-only alignment"
status: ready
owners: "agents"
created: 2026-06-15
updated: 2026-06-15
stories:
  - "ST-21-10"
tags:
  - frontend
  - backend
  - public
  - exam-converter
  - docs
dependencies:
  - "ST-21-03"
  - "ST-21-10"
acceptance_criteria:
  - "Given the public one-time Exam Converter lane remains available, when the public upload surface renders, then it requires only the governed `.dxe` source file and shows no optional graded-result/supporting PDF upload or early target selection controls."
  - "Given the public browser runtime submits a job, when Skriptoteket builds the public multipart request and backend job spec, then it sends no `graded_result_pdf`, no `targets_json`, and requests the currently supported target artifacts by default."
  - "Given the public route and upstream-client contracts still expose historical graded-result or target-selection fields, when this slice lands, then the frontend, public API handlers, and focused backend tests are updated together so the public lane matches the authenticated source-only product contract."
---

# PR-0357: ST-21-10 Public Exam Converter Source-Only Alignment

## Problem

`PR-0356` removes stale optional graded-result upload and early target
selection from the authenticated Exam Converter lane only. The public one-time
lane still exposes the older product contract through its upload panel,
browser runtime payload, and backend public route tests.

## Goal

Align the public one-time Exam Converter lane with the same source-only intake
contract used by the authenticated lane.

## Non-goals

- No new public capability or abuse-control expansion.
- No change to direct-download-only public artifact ownership.
- No DOCX, QTI editor, or question-pool work.

## Implementation plan

1. Remove optional graded-result PDF and target-selection controls from the
   public upload panel and runtime state.
2. Update the public browser API payload so source-only submits omit
   `graded_result_pdf` and `targets_json`.
3. Update the public backend route and Sir Convert upstream adapter tests so
   default target requests remain producer-owned without browser-selected
   target state.
4. Refresh `ST-21-03`, `ST-21-10`, and the relevant public Exam Converter docs
   with the final source-only public contract.

## Test plan

- `pdm run fe-test -- --run src/views/apps/ExamConverterPublicView.spec.ts`
- `pdm run test tests/unit/web/test_public_apps_exam_converter_runtime.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_public_exam_converter_upstream_clients.py`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`

## Rollback plan

Revert the public lane alignment as one slice if the public route cannot yet
consume producer-owned default targets without the historical fields.
