---
type: pr
id: PR-0003
title: "Gate submit-review + help surfaces (no panels)"
status: done
owners: "agents"
created: 2026-01-05
updated: 2026-01-06
stories:
  - "ST-14-02"
  - "ST-04-04"
tags: ["backend", "frontend", "ux"]
acceptance_criteria:
  - "Given a draft tool has a draft-* slug or missing taxonomy, when a contributor/admin tries to submit for review, then the request is rejected with a clear validation error and no state change occurs."
  - "Given the editor UI, when minimum publish requirements are not met, then the 'Begar publicering' CTA is still clickable, a hover help message explains what is missing, and clicking the CTA opens a focused modal with the missing requirements."
  - "Given a blocked submit attempt, then the modal provides a clear help link to the editor help section."
  - "No new panels are added to the editor UI; help is delivered via help modal, hover, and a focused modal only."
---

## Problem

Draft tools can be submitted for review even when they fail minimum publish requirements
(draft-* slug, missing taxonomy). The block only happens later at tool publish,
creating confusing UX and low-quality review submissions.

## Goal

Hard-gate submit-review on minimum publish requirements and provide help surfaces
that teach the requirements without adding new panels.

## Non-goals

- Changing publish-tool guards (they remain as-is).
- Changing workflow states or roles.
- Adding new editor panels or persistent cards.

## Implementation plan

1) Backend guard
   - Add a minimum requirements check in `SubmitForReviewHandler`.
   - Reuse the same validation rules as publish-tool for slug and taxonomy
     (draft-* slug not allowed; at least one profession + category).
   - Return a validation error with actionable message and details.

2) Frontend gating
   - Allow `Begär publicering` to open the workflow modal even when requirements
     are missing.
   - Provide a hover help popover on the CTA with missing items (or a brief
     action explanation when requirements are met).
   - When blocked, show a focused modal listing the missing requirements and a
     help link (no toasts).

3) Help surfaces (no panels)
   - Add help copy to the editor help modal describing minimum publish
     requirements and where to fix them.

## Test plan

- Backend unit test for submit-review guard (slug + taxonomy failures).
- Frontend unit test for gating logic + tooltip content.
- Manual: create draft tool, attempt submit-review with draft-* slug and no
  taxonomy, confirm rejection + modal + help link.

## Rollback plan

- Revert submit-review guard and UI gating to restore previous behavior.
