---
type: review
id: REV-EPIC-37
title: "Review: Backlog product-direction inventory and app surface realignment"
status: approved
owners: "agents"
created: 2026-06-17
updated: 2026-06-18
reviewer: "codex-ruthless-reviewer"
epic: EPIC-37
stories:
  - ST-37-01
  - ST-37-02
  - ST-37-03
  - ST-37-04
links:
  - REF-current-product-direction-and-backlog-inventory-2026-06-17
  - REF-current-product-lanes-and-sir-convert-boundary-v1
  - REF-pr-0358-active-backlog-inventory-2026-06-17
  - REF-review-workflow
  - REV-PR-0359
  - EPIC-21
  - EPIC-29
---

## TL;DR

`EPIC-37` proposes a staged reset: first make the backlog truthful, then freeze
the current product-lane and Sir Convert boundary, then resume service-shell and
app-presentation UI work. The package intentionally preserves valuable
script/editor/runner capabilities while moving front-door product focus toward
bespoke teacher productivity applications.

## Problem Statement

The backlog contains old active/proposed/ready/in-progress/blocked work from
several product eras. Some items likely remain valuable, some are already done
but not closed, and some are now superseded by later architecture or product
direction. Starting the next UI/app-presentation work without first repairing
that state would make the dashboard and app entries inherit stale assumptions.

## Proposed Solution

Approve `EPIC-37` as the governing package for:

1. evidence-backed inventory and stale-state repair
2. current product-lane and Sir Convert boundary documentation
3. main service shell/dashboard realignment planning
4. app presentation decomposition and naming planning

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/reference/ref-current-product-direction-and-backlog-inventory-2026-06-17.md` | Product-lane and classification rules | 8 min |
| `docs/backlog/epics/epic-37-backlog-product-direction-inventory-and-app-surface-realignment.md` | Scope, story order, risks | 8 min |
| `docs/backlog/stories/story-37-01-backlog-inventory-and-stale-state-repair.md` | Inventory and cleanup authority | 5 min |
| `docs/backlog/stories/story-37-02-current-product-lane-and-sir-convert-boundary-reset.md` | Sir Convert/native boundary | 5 min |
| `docs/backlog/stories/story-37-03-service-shell-and-dashboard-ux-realignment.md` | Shell/dashboard sequencing | 4 min |
| `docs/backlog/stories/story-37-04-app-presentation-decomposition-and-naming-reset.md` | App presentation split | 4 min |
| `docs/backlog/prs/pr-0358-st-37-01-active-backlog-inventory-and-classification-matrix.md` | First executable inventory slice | 4 min |
| `docs/reference/ref-pr-0358-active-backlog-inventory-2026-06-17.md` | Deep-audit inventory evidence and cleanup queue | 10 min |
| `docs/backlog/prs/pr-0359-st-37-01-stale-state-repair-and-supersession-cleanup-batch.md` | Reviewed cleanup execution and retained gate language | 5 min |
| `docs/backlog/reviews/review-pr-0359-stale-state-repair-and-supersession-cleanup-batch.md` | Independent cleanup review and validation evidence | 5 min |
| `docs/reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md` | Durable product-lane and ownership doctrine | 8 min |
| `docs/backlog/prs/pr-0360-st-37-02-current-product-lane-and-sir-convert-boundary-reference.md` | Product-lane doctrine execution scope | 4 min |
| `docs/backlog/prs/pr-0361-st-37-03-service-shell-ux-realignment-planning-package.md` | Next unblocked shell planning slice | 4 min |
| `docs/backlog/prs/pr-0362-st-37-04-app-presentation-decomposition-and-naming-package.md` | Later app-presentation planning slice | 4 min |

**Total estimated time:** ~78 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Create `EPIC-37` instead of reopening closed `EPIC-34` | This is broader than docs-as-code mechanics: it ties backlog truth to product direction and future app surfaces | [x] |
| Inventory before UI/app-presentation implementation | Prevents stale backlog structure from driving the next dashboard and app-entry design | [x] |
| Preserve script/editor/runner value while demoting script-first product positioning | Matches current bespoke-app direction without throwing away useful platform capabilities | [x] |
| Keep Sir Convert-a-Lot for heavy conversion/model/runtime work, not lightweight native app-state manipulation | Avoids replay/fingerprint complexity for workflows that should live inside Skriptoteket | [x] |
| Split app presentation into teacher job lanes | Makes Exam Converter, Audio Transcription, Document Converter, and Klassrumskartan legible as distinct product applications | [x] |

## Review Checklist

- [x] The package is scoped to backlog truth, boundary doctrine, and planning
      before UI/API implementation.
- [x] The classification rules are concrete enough to prevent arbitrary cleanup.
- [x] The script/editor/runner preservation rule is explicit.
- [x] The Sir Convert boundary is specific enough to guide future Exam Converter
      and transcript work.
- [x] The UI/app-presentation stories are correctly sequenced on inventory and
      product-lane direction.
- [x] The completed docs-only slices made no production code or test changes.

## Review Feedback

**Reviewer:** `codex-ruthless-reviewer`
**Date:** `2026-06-18`
**Verdict:** `approved`

### Required Changes

None.

### Suggestions (Optional)

- Start `ST-37-03` / `PR-0361` next. Keep it as a planning package until it
  produces PR-sized implementation slices with exact Vitest, typecheck, and
  HuleEdu browser-session proof obligations for route-visible work.
- Keep `ST-37-04` / `PR-0362` blocked until the service-shell planning package
  closes, because route or registry naming work should consume the approved
  shell direction rather than racing it.

### Decision Approvals

- [x] Create `EPIC-37` instead of reopening closed `EPIC-34`
- [x] Inventory before UI/app-presentation implementation
- [x] Preserve script/editor/runner value while demoting script-first product positioning
- [x] Keep Sir Convert-a-Lot for heavy conversion/model/runtime work, not lightweight native app-state manipulation
- [x] Split app presentation into teacher job lanes

### Findings

No findings.

### Evidence And Validation

- The retained `PR-0358` inventory and deep-audit artifact classify the active
  backlog using concrete outcomes instead of arbitrary cleanup.
- `REV-PR-0359` independently approved the first docs-only stale-state repair
  batch and confirmed `REV-EPIC-37` stayed pending until this review.
- `PR-0360` / `ST-37-02` produced the durable current product-lane and Sir
  Convert/Skriptoteket ownership reference without route, registry, API, QTI,
  DOCX, Sir Convert, or HuleEdu contract changes.
- `PR-0361` and `PR-0362` remain planning slices. They require focused
  frontend tests and sanctioned HuleEdu browser-session proof before any later
  route-visible or protected-path UI implementation closes.
- Validation commands and outcomes:
  - `pdm run docs-validate`: passed.
  - `pdm run handoff-validate`: passed.
  - `git diff --check`: passed.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `REF-current-product-direction-and-backlog-inventory-2026-06-17` | Captured the product-direction lens and inventory classification rules |
| 2 | `EPIC-37` | Added the proposed backlog inventory and app-surface realignment epic |
| 3 | `ST-37-01` to `ST-37-04` | Added the ordered story stack |
| 4 | `PR-0358` to `PR-0362` | Added the first PR-sized discovery, cleanup, and planning slices |
| 5 | `REV-EPIC-37` | Opened the retained review gate |
| 6 | `REV-EPIC-37` | Approved the epic package after `ST-37-01` and `ST-37-02` completed as docs-only slices with retained review evidence |
| 7 | `EPIC-37`, `ST-37-03`, `PR-0361` | Activated the epic and unblocked the next service-shell planning slice |
