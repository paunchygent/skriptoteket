---
type: template
id: TPL-review
title: "Review template"
status: active
owners: "agents"
created: 2025-12-26
updated: 2026-04-06
for_type: review
---

Copy, fill in, and save under `docs/backlog/reviews/`.

Use a target-based review record:

- Epic review filename: `review-epic-XX-short-name.md`
- Story review filename: `review-st-XX-YY-short-name.md`
- PR review filename: `review-pr-XXXX-short-name.md`

The frontmatter `id` must match the primary target:

- Epic review: `REV-EPIC-XX`
- Story review: `REV-ST-XX-YY`
- PR review: `REV-PR-XXXX`

Choose one primary target family that drives the review `id`:

- `epic: EPIC-XX` for epic reviews
- `stories:` for story reviews
- `prs:` for PR reviews

If `stories:` or `prs:` contains multiple items, put the primary target first because the review
`id` derives from the first entry.

Supporting governed items may still appear in `stories:`, `prs:`, or `adrs:` when the review
genuinely covers them together. Use `adrs:` for governed ADRs; standalone ADR-target review docs
are not a current shape in this repo.

Put broader context, such as parent epics or adjacent stories, in `links:` or in the body instead
of forcing every related item into the primary-target contract.

```markdown
---
type: review
id: REV-PR-0229
title: "Review: [Target title]"
status: pending
owners: "agents"
created: YYYY-MM-DD
updated: YYYY-MM-DD
reviewer: "lead-developer"
prs:
  - PR-0229
adrs:
  - ADR-XXXX
links:
  - EPIC-29
  - ST-29-11
---

## TL;DR

[One-paragraph summary of what is being reviewed and why]

## Problem Statement

[What user, product, or system problem this review is checking]

## Proposed Solution

[High-level approach or decision shape being reviewed]

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-XXXX-*.md` | Scope and contract | X min |
| `docs/backlog/stories/story-XX-YY-*.md` | Parent story expectations | X min |
| `frontend/...` | Implementation/proof surface | X min |

**Total estimated time:** ~XX minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| [Decision 1] | [Why this choice] | [ ] |
| [Decision 2] | [Why this choice] | [ ] |

## Review Checklist

- [ ] Scope is bounded and appropriate
- [ ] Acceptance criteria or proof obligations are reviewable
- [ ] Risks and structural fault lines are called out explicitly
- [ ] Verification plan matches the claimed contract

## Review Feedback

**Reviewer:** @reviewer-name
**Date:** YYYY-MM-DD
**Verdict:** pending

### Required Changes

[Blocking changes, or "None" if approved]

### Suggestions (Optional)

[Non-blocking recommendations]

### Decision Approvals

- [ ] Decision 1
- [ ] Decision 2

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-XXXX` | [What changed] |
```
