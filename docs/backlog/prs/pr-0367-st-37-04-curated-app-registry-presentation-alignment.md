---
type: pr
id: PR-0367
title: "ST-37-04 curated app registry presentation alignment"
status: blocked
owners: "agents"
created: 2026-06-18
updated: 2026-06-18
stories:
  - "ST-37-04"
tags:
  - backend
  - frontend
  - curated-apps
dependencies:
  - "PR-0362"
  - "PR-0366"
  - "REF-app-presentation-decomposition-and-naming-plan-v1"
acceptance_criteria:
  - "Given teacher-facing shell copy is already truthful, when curated-app registry metadata is aligned, then registry titles and summaries stop advertising the active compatibility host as generic Document Converter behavior."
  - "Given the compatibility app id still exists, when registry metadata changes, then the slice preserves current app ids, public Exam Converter capability behavior, and route contracts."
  - "Given this slice is registry-only, when it closes, then no Sir Convert, HuleEdu, QTI, DOCX, or backend API schema change is introduced."
---

# PR-0367: ST-37-04 Curated App Registry Presentation Alignment

## Problem

The current curated-app registry still exposes `documents.conversion_hub` as
generic document conversion even though the active host is Exam Converter plus
transcript mode.

## Goal

Make curated-app metadata truthful without changing the compatibility app id or
route structure.

## Non-goals

- No app-id split or route rename.
- No public Exam Converter route-contract change.
- No backend API schema shape change.
- No Sir Convert, HuleEdu, QTI, or DOCX contract change.

## Review gate

`REV-PR-0367` must be approved before code implementation begins.

## Implementation plan

1. Add a focused red test for the registry/bootstrap consumer that still
   exposes stale generic document-conversion naming.
2. Align `src/skriptoteket/infrastructure/curated_apps/registry.py` and any
   directly affected bootstrap/detail consumers to
   [REF-app-presentation-decomposition-and-naming-plan-v1](../../reference/ref-app-presentation-decomposition-and-naming-plan-v1.md).
3. Keep `documents.conversion_hub` as a technical compatibility app id unless a
   later reviewed route-visible slice proves a stronger change is needed.
4. Stop and return to planning if truthful metadata cannot be expressed without
   a new backend/API contract.

## Test plan

- Red first:
  `pdm run test tests/unit/infrastructure/curated_apps/test_registry.py`
- Green:
  `pdm run test tests/unit/infrastructure/curated_apps/test_registry.py`
- Add or extend focused frontend consumer tests if bootstrap or app-detail
  presentation changes are visible in the SPA.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `git diff --check`

## Rollback plan

Restore the prior registry titles and summaries while leaving copy-only shell
surfaces intact.
