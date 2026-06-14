---
type: review
id: REV-PR-0351
title: "Review: PR-0351 Transcript completion, progress, and export UX"
status: pending
owners: "agents"
created: 2026-06-14
updated: 2026-06-14
reviewer: "skriptoteket_reviewer"
prs:
  - PR-0351
links:
  - ST-21-08
  - EPIC-21
  - MOCK-pr-0351-transcript-progress-export-ux
---

## TL;DR

Pending review gate for `PR-0351`, which turns the approved transcript
progress/completion/export UX direction into the runtime Conversion Hub
transcript workspace.

## Problem Statement

The implementation must remove the confusing transcript completion/export UX
without regressing the product-owned replay/export boundary from `PR-0350`.
The review should focus on teacher-visible behavior, stable layout, and proof
that the browser does not regain producer-workflow ownership.

## Proposed Solution

Implement the approved mockup direction:

- truthful running progress with normal Swedish copy;
- autosaved transcript completion with no generic manual save gate;
- transcript reading surface plus `Talare och export` inspector;
- stable format selector plus one-line `Ladda ner` and `Mina filer` actions;
- planned/reserved pending, running, failed, and warning states.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0351-st-21-08-transcript-completion-progress-and-export-ux.md` | Scope, non-goals, acceptance | 10 min |
| `docs/mockups/pr-0351-transcript-progress-export-ux/README.md` | Approved UX contract | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/conversion-hub-transcript/` | Runtime transcript workspace | 40 min |
| `frontend/apps/skriptoteket/src/api/` transcript/export clients | Product endpoint ownership | 20 min |
| Focused Vitest/backend/browser proof artifacts | Behavioral coverage | 30 min |

**Total estimated time:** ~110 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Autosave on successful transcript completion | Manual `Spara` is not a meaningful teacher choice after successful STT completion and currently hides the useful workspace. | [ ] |
| Stable export control block | Format is selected once; actions stay `Ladda ner` and `Mina filer` without duplicated download buttons or dynamic two-line labels. | [ ] |
| No jump-scare status surfaces | Pending/running/failed/warning states must have reserved layout or separate planned state layouts. | [ ] |
| No internal/Swenglish copy | Producer stages must map to normal Swedish teacher language. | [ ] |
| Browser remains product-observer only | `PR-0351` must not restore browser-owned Sir Convert replay submit/poll/download/base64/complete behavior. | [ ] |

## Review Checklist

- [ ] Scope is bounded to transcript progress/completion/export UX.
- [ ] Runtime follows the approved mockup hierarchy without pixel-match
  cargo-culting.
- [ ] Transcript column keeps readable width at desktop and moves inspector
  below before the transcript is squeezed.
- [ ] Running state does not show a fake full workspace before transcript
  content exists.
- [ ] Progress bar/ETA is based on available product/producer data and does
  not fabricate completion from heartbeat alone.
- [ ] Visible Swedish copy avoids internal terms such as raw diarization stage
  names.
- [ ] Completed transcript autosaves and lands directly in the useful
  workspace.
- [ ] Export has no duplicated download affordance, no selected-file metadata
  cards, no dropdown chevron without a menu, and no dynamic format suffix in
  visible action labels.
- [ ] Pending/running/failed/warning UI states are planned and do not alter
  layout unexpectedly.
- [ ] Focused tests prove old labels/actions are absent on the normal path.
- [ ] Browser proof uses the HuleEdu browser-session ceremony only.

## Review Feedback

**Reviewer:** @skriptoteket_reviewer
**Date:** 2026-06-14
**Verdict:** pending

### Required Changes

Pending implementation.

### Suggestions (Optional)

Pending implementation.

### Decision Approvals

- [ ] Autosave completion path
- [ ] Stable export control block
- [ ] No jump-scare status surfaces
- [ ] No internal/Swenglish copy
- [ ] Browser remains product-observer only

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0351` | Pending implementation. |
