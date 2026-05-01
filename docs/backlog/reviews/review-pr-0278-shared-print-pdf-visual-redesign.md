---
type: review
id: REV-PR-0278
title: "Review: PR-0278 shared print PDF visual redesign"
status: pending
owners: "agents"
created: 2026-05-01
updated: 2026-05-01
reviewer: "lead-developer"
prs:
  - PR-0278
links:
  - EPIC-26
  - ST-26-08
  - ST-26-06
  - PR-0276
---

## TL;DR

`PR-0278` is the pre-implementation review gate for redesigning the actual
Klassrumskartan PDFs so workspace exports and share-link downloads inherit from
the approved shared-link visual language without using responsive share HTML as
the PDF source.

## Problem Statement

`PR-0276` improved the public shared grouping and seating renders, but the
downloaded PDFs still need a governed visual redesign. The review must confirm
that the task is scoped to print-owned renderers, keeps share PDFs immutable and
payload-derived, preserves compact branded PDF headers, and demands real PDF
artifact proof rather than CSS-string assertions.

## Proposed Solution

Approve `ST-26-08`/`PR-0278` as a new EPIC-26 slice. Prefer a narrow extraction
of print-owned scene/card/header primitives when that keeps workspace and
share-link PDFs aligned without over-abstracting. Otherwise, allow direct
refactoring of the existing export PDF renderers while retaining parity tests
and proof obligations.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/stories/story-26-08-klassrumskartan-shared-print-pdf-visual-parity.md` | Parent story scope and acceptance | 8 min |
| `docs/backlog/prs/pr-0278-st-26-08-shared-print-pdf-visual-redesign.md` | PR slice, options, proof, stop conditions | 12 min |
| `docs/backlog/epics/epic-26-klassrumskartan-explicit-exports-and-class-list-import.md` | EPIC-26 fit and sequencing | 5 min |
| `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_pdf_renderer.py` | Existing immutable share-PDF delegation contract | 5 min |
| `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/grouping_pdf_renderer.py` | Grouping print renderer redesign surface | 5 min |
| `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/poster_renderer.py` | Seating print renderer redesign surface | 5 min |

**Total estimated time:** ~40 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Create `ST-26-08` rather than reopening `PR-0276` | The new work spans older workspace PDF exports and share-link PDF downloads, while `PR-0276` is closed and approved. | [ ] |
| Prefer narrow shared print primitives over divergent renderers | Workspace exports and share-link downloads should use the same print-owned renderer behavior. | [ ] |
| Keep share PDFs payload-derived | Immutable share artifacts must continue rendering from `presentation_payload`, not responsive browser HTML. | [ ] |
| Require real PDF/PNG proof for all four paths | Visual regressions cannot be approved from CSS strings or mocked WeasyPrint calls alone. | [ ] |

## Review Checklist

- [ ] Scope stays inside PDF visual redesign and renderer proof.
- [ ] Header/branding constraint is explicit and reviewable.
- [ ] No share-token, revocation, expiry, public-read, or guest-helper semantics
  are changed.
- [ ] No export payload schema change is required.
- [ ] Workspace export PDFs and share-link PDF downloads share renderer behavior.
- [ ] Share-link PDFs remain derived from immutable `presentation_payload`.
- [ ] Test plan includes real PDF generation, media boxes, first-page PNGs, and
  occupancy/layout checks.
- [ ] Stop conditions are explicit enough to halt implementation before a
  contract fork.

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-05-01`
**Verdict:** pending

### Required Changes

Pending review.

### Suggestions (Optional)

Pending review.

### Decision Approvals

- [ ] Create `ST-26-08` rather than reopening `PR-0276`
- [ ] Prefer narrow shared print primitives over divergent renderers
- [ ] Keep share PDFs payload-derived
- [ ] Require real PDF/PNG proof for all four paths

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `ST-26-08` | Added story for shared print PDF visual parity across workspace and share-link downloads. |
| 2 | `PR-0278` | Added implementation-ready slice with decision checkpoints, validation, artifact proof, and stop conditions. |
| 3 | `EPIC-26` | Linked the new story into the export/import epic. |
