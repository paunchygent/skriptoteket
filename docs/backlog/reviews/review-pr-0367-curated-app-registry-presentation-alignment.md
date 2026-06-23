---
type: review
id: REV-PR-0367
title: "Review: PR-0367 curated app registry presentation alignment"
status: approved
owners: "agents"
created: 2026-06-22
updated: 2026-06-22
reviewer: "codex-independent-reviewer"
prs:
  - PR-0367
links:
  - ST-37-04
  - EPIC-37
  - PR-0362
  - PR-0366
  - PR-0368
  - PR-0374
  - REF-app-presentation-decomposition-and-naming-plan-v1
  - REF-current-product-lanes-and-sir-convert-boundary-v1
---

## TL;DR

Approved after post-implementation review. The implementation stayed
registry-only: it changed the real curated-app registry metadata for
`documents.conversion_hub`, added focused regression coverage for the exposed
registry contract, preserved the technical app id and current public Exam
Converter capability, and left route-visible identity splitting plus
compatibility cleanup to `PR-0368` and `PR-0374`.

## Problem Statement

This review checks whether `PR-0367` can safely start implementation after
`PR-0366` made the shell copy truthful but before route-visible app identity
splitting. The risk is that a registry metadata slice might accidentally turn
the technical `documents.conversion_hub` compatibility host into a fake
Document Converter, change public Exam Converter contracts, or pre-solve the
later Exam Converter and Audio Transcription split.

## Proposed Solution

Approve if the PR remains limited to curated-app registry title/summary
alignment and directly affected bootstrap/detail consumers, adds focused
behavioral tests for the exposed metadata, and explicitly preserves app id,
route, public capability, backend/API schema, Sir Convert, HuleEdu, QTI, and
DOCX contracts.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0367-st-37-04-curated-app-registry-presentation-alignment.md` | Scope, non-goals, implementation plan, and proof gates | 15 min |
| `docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md` | Parent story sequence and accepted app-presentation decisions | 10 min |
| `docs/backlog/epics/epic-37-backlog-product-direction-inventory-and-app-surface-realignment.md` | Epic boundary and remaining ST-37-04 sequence | 5 min |
| `docs/reference/ref-app-presentation-decomposition-and-naming-plan-v1.md` | Registry-only classification, sequencing, stop conditions, and proof expectations | 15 min |
| `docs/reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md` | Product-lane truth and Sir Convert/Skriptoteket ownership boundary | 10 min |
| `docs/backlog/prs/pr-0368-st-37-04-route-visible-app-entrypoint-and-presentation-alignment.md` | Adjacent route-visible split that must stay out of PR-0367 | 8 min |
| `docs/backlog/prs/pr-0374-st-37-04-post-cutover-conversion-hub-compatibility-cleanup.md` | Later compatibility cleanup that must stay out of PR-0367 | 5 min |
| `src/skriptoteket/infrastructure/curated_apps/registry.py` | Current stale registry metadata and public capability shape | 8 min |
| `tests/unit/infrastructure/curated_apps/test_registry.py` | Existing focused proof seam for registry metadata/capability behavior | 5 min |

**Total estimated time:** ~81 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep `PR-0367` registry-only | The accepted plan classifies registry metadata alignment separately from route-visible and backend/API work | [x] |
| Preserve `documents.conversion_hub` as the technical compatibility app id | `PR-0368` owns route-visible app identities; changing app ids here would skip that review gate | [x] |
| Preserve public Exam Converter route and capability | The current registry exposes only the `exam_converter` public capability; generic public conversion must remain unsupported | [x] |
| Keep Document Converter inert | A truthful Document Converter host/backend MVP does not exist yet, so registry copy must not route teachers to the compatibility host under that label | [x] |
| Defer compatibility cleanup | `PR-0374` owns removal of the temporary `documents.conversion_hub?mode=...` compatibility path after `PR-0368` proves the split | [x] |

## Review Checklist

- [x] Scope is bounded to registry title/summary alignment and directly affected
  bootstrap/detail consumers.
- [x] The PR explicitly forbids app-id split, route rename, public Exam
  Converter route-contract change, backend API schema change, and Sir
  Convert/HuleEdu/QTI/DOCX contract change.
- [x] The PR stops if truthful metadata requires a new backend/API contract.
- [x] The parent story and references keep Document Converter planned/inert until
  a truthful route target exists.
- [x] The proof plan names a focused red/green registry test and leaves SPA
  consumer tests conditional on visible bootstrap/detail presentation changes.

## Review Feedback

**Reviewer:** `codex-independent-reviewer`
**Date:** `2026-06-22`
**Verdict:** `approved`

### Post-Implementation Review Pass - 2026-06-22

Decision: `approved`.

#### Scope Reviewed

- `src/skriptoteket/infrastructure/curated_apps/registry.py`
- `tests/unit/infrastructure/curated_apps/test_registry.py`
- `docs/backlog/prs/pr-0367-st-37-04-curated-app-registry-presentation-alignment.md`
- `docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md`
- `.codex/handoff.md`
- Governing references: `REF-app-presentation-decomposition-and-naming-plan-v1`,
  `REF-current-product-lanes-and-sir-convert-boundary-v1`, `ST-37-04`,
  `EPIC-37`, `PR-0368`, and `PR-0374`.

#### Findings

No findings.

The implementation satisfies the retained review gate:

- The production change is limited to the registry metadata for the existing
  `documents.conversion_hub` app definition. The title is now
  `Provhantering och ljudtranskribering`, and the summary names exam
  creation/conversion plus speech-to-text transcript saving rather than generic
  document conversion
  (`src/skriptoteket/infrastructure/curated_apps/registry.py:68`).
- The app id, `tool_id`, bespoke UI mode, authenticated-only general access, and
  active `exam_converter` public capability remain unchanged
  (`src/skriptoteket/infrastructure/curated_apps/registry.py:69`).
- The new focused regression test exercises the real in-memory registry through
  `get_by_app_id`, asserts the exposed title/summary, rejects the old generic
  `Konvertera dokument` and `PDF/HTML/Markdown/DOCX` wording, and preserves the
  public capability constraints
  (`tests/unit/infrastructure/curated_apps/test_registry.py:102`).
- The scoped diff contains no route, frontend host-registry, domain model,
  public API schema, OpenAPI, auth-edge, Sir Convert, HuleEdu, QTI, DOCX, or
  Document Converter implementation changes. `PR-0368` and `PR-0374` remain the
  route-visible split and compatibility-cleanup owners.
- The implementation evidence in `PR-0367` records the red/green test proof and
  keeps the no-route/no-schema/no-producer-contract boundary explicit
  (`docs/backlog/prs/pr-0367-st-37-04-curated-app-registry-presentation-alignment.md:61`).

Reviewer-run validation:

```bash
pdm run test tests/unit/infrastructure/curated_apps/test_registry.py
pdm run docs-validate
git diff --check
```

Results:

- Focused registry test: passed, `5` tests.
- `pdm run docs-validate`: passed.
- `git diff --check`: passed.

Worker validation accepted but not rerun by this reviewer:

- `pdm run lint`: passed.
- `pdm run typecheck`: passed.
- `pdm run handoff-validate`: passed.

### Pre-Implementation Review Pass - 2026-06-22

Decision: `approved`.

### Required Changes

None.

### Suggestions (Optional)

- During implementation, make the new registry assertion outcome-based: the
  exposed `documents.conversion_hub` metadata should no longer advertise generic
  document conversion, while `app_id`, authenticated access, and the active
  `exam_converter` public capability remain unchanged.
- If implementation discovers that bootstrap/detail DTOs cannot present truthful
  metadata without schema changes, stop and route the blocker to `PR-0369`
  instead of expanding this slice.

### Decision Approvals

- [x] Approve `PR-0367` as registry-only implementation-ready.
- [x] Approve the current proof plan for a narrow metadata/capability slice.
- [x] Do not approve route-visible identity split, backend/API decomposition, or
  compatibility cleanup in this review.

### Findings

No findings.

### Evidence And Validation

- `PR-0367` acceptance criteria require registry titles/summaries to stop
  advertising the active compatibility host as generic Document Converter
  behavior while preserving app ids, public Exam Converter capability behavior,
  route contracts, backend API schema, and producer contracts
  (`docs/backlog/prs/pr-0367-st-37-04-curated-app-registry-presentation-alignment.md:19`).
- The implementation plan is scoped to
  `src/skriptoteket/infrastructure/curated_apps/registry.py` plus directly
  affected bootstrap/detail consumers and includes a stop condition if truthful
  metadata needs a new backend/API contract
  (`docs/backlog/prs/pr-0367-st-37-04-curated-app-registry-presentation-alignment.md:51`).
- The accepted naming plan classifies `PR-0367` as registry-only and excludes
  app-id split, route change, Sir Convert/HuleEdu/QTI/DOCX contract change, and
  fake Document Converter implementation
  (`docs/reference/ref-app-presentation-decomposition-and-naming-plan-v1.md:69`).
- The accepted sequencing keeps registry metadata alignment before route alias
  or app-id decomposition and reserves route-visible identity splitting for
  `PR-0368`
  (`docs/reference/ref-app-presentation-decomposition-and-naming-plan-v1.md:123`,
  `docs/reference/ref-app-presentation-decomposition-and-naming-plan-v1.md:151`).
- The accepted stop conditions forbid labeling the current compatibility host,
  Exam Converter, Audio Transcription, catalog, or fallback path as Document
  Converter before a real document route exists
  (`docs/reference/ref-app-presentation-decomposition-and-naming-plan-v1.md:161`).
- The implemented registry now uses `app_id="documents.conversion_hub"` with
  title `Provhantering och ljudtranskribering`, while retaining only the active
  `exam_converter` public capability
  (`src/skriptoteket/infrastructure/curated_apps/registry.py:68`).
- Registry tests cover authenticated-only general access, the active public Exam
  Converter capability, and the new stale-copy regression assertion
  (`tests/unit/infrastructure/curated_apps/test_registry.py:79`,
  `tests/unit/infrastructure/curated_apps/test_registry.py:102`).

Validation commands and outcomes:

- `pdm run test tests/unit/infrastructure/curated_apps/test_registry.py`: passed
  with 5 tests.
- `pdm run docs-validate`: passed.
- `git diff --check`: passed.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REV-PR-0367` | Created the retained pre-implementation review gate and approved `PR-0367` as registry-only implementation-ready. |
| 2 | `REV-PR-0367` | Added the post-implementation review pass and approved the completed registry-only implementation. |
