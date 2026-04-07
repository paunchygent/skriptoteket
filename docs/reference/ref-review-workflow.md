---
type: reference
id: REF-review-workflow
title: "Review workflow for backlog items and retained decision records"
status: active
owners: "agents"
created: 2025-12-26
updated: 2026-04-06
topic: "review-workflow"
---

This document defines how review records work in this repo. Reviews are retained decision records,
but they are now target-based rather than epic-ledger catch-alls.

## When reviews are required

All proposed implementation packages still require review before implementation begins:

| Artifact | Trigger | Reviewer |
|----------|---------|----------|
| ADR | Status = `proposed` | Lead developer or architect |
| EPIC | Status = `proposed` | Lead developer |
| Stories in a proposed epic package | Reviewed with the epic package | Lead developer |
| Story or PR follow-up slice with its own decision gate | When the backlog item explicitly calls for retained review | Lead developer or delegated reviewer |

ADRs still require review, but they are recorded inside the governing epic, story, or PR review
doc via `adrs:`. Standalone ADR-target review docs are not a current shape in this repo; if a
proposed ADR has no governing backlog item yet, create the smallest backlog item that owns its
implementation gate first.

## Canonical review shape

### Location

Save review docs under:

```text
docs/backlog/reviews/review-{primary-target-lower}-{short-name}.md
```

Examples:

- `docs/backlog/reviews/review-epic-29-klassrumskartan-desktop-first-workspace-overhaul.md`
- `docs/backlog/reviews/review-st-23-01-classroom-planner-slice-1.md`
- `docs/backlog/reviews/review-pr-0229-planner-toolbar-breakpoint-overflow.md`

### Primary target rules

Each review doc has one primary target. The frontmatter `id` must match that target:

- Epic review: `id: REV-EPIC-XX` with `epic: EPIC-XX`
- Story review: `id: REV-ST-XX-YY` with `stories: [ST-XX-YY, ...]`
- PR review: `id: REV-PR-XXXX` with `prs: [PR-XXXX, ...]`

Primary-target precedence is:

1. `epic`
2. first item in `stories`
3. first item in `prs`

When `stories:` or `prs:` contains multiple items, put the primary target first because the review
`id` derives from that first entry.

Supporting governed items may still appear in `stories:`, `prs:`, or `adrs:` when the review
genuinely covers them together, but only one primary target drives the filename and `id`. Use
`links:` for broader context such as parent epics, adjacent stories, or related ADRs when those
items are not themselves governed by the review.

### Frontmatter expectations

Each review doc should include:

- the standard docs frontmatter fields required by the docs contract
- `reviewer`
- the primary-target field that drives the review `id`
- optional `stories:`, `prs:`, or `adrs:` for tightly coupled governed scope
- optional `links:` for broader context that should stay out of the primary-target contract

### What not to do

- Do not create new PR or story review gates as supplemental sections inside an epic review doc.
- Do not keep multiple unrelated review cycles bundled into one retained review ledger merely
  because they share an epic.
- Do not use review docs as ad hoc notes; they should freeze a reviewable decision surface.

Legacy epic-ledger reviews may still exist in history, but new review work should use one review
doc per primary target.

## Required sections

Every review doc should include:

1. `TL;DR`
2. `Problem Statement`
3. `Proposed Solution`
4. `Artifacts to Review`
5. `Key Decisions`
6. `Review Checklist`
7. `Review Feedback`
8. `Changes Made`

The exact depth can vary by scope, but the target, verification burden, and close-out path must be
clear enough that a reviewer does not have to infer hidden rules.

## Review status

```yaml
status: pending | approved | changes_requested | rejected
```

## Reviewer responsibilities

### Before starting

1. Read the target backlog item and its frozen decisions first.
2. Read the parent story or epic only as needed to understand scope boundaries.
3. Check whether the review claims shared behavior, parity, or proof obligations that extend beyond
   a single file or route.

### During review

For each review, evaluate:

| Criterion | Question |
|-----------|----------|
| Alignment | Does the target solve the stated problem without reopening settled scope? |
| Contract clarity | Are acceptance criteria, review widths, decisions, or verification rules explicit? |
| Structural risk | Are the real fault lines named, or is the task relying on vague symptoms? |
| Proof strength | Do tests and live checks actually exercise the claimed contract? |
| Closure honesty | Does the doc distinguish between an improved baseline and true close-out? |

### Recording feedback

Record reviewer output directly in the review doc under `## Review Feedback`.

If the reviewer finds structural issues:

- name the exact fault lines with file paths
- state which assumptions were disproven
- propose `2` to `3` fix directions with pros/cons

## Post-review actions

### If approved

1. Update the review doc status to `approved`.
2. Update the governed backlog item status if approval unblocks it.
3. Update linked story/epic notes or implementation summaries if the approved review changes the
   canonical direction.
4. Update `.agents/handoff.md`.
5. Run `pdm run docs-validate`.

### If changes are requested

1. Update the review doc status to `changes_requested`.
2. Address each required change in the governed backlog item or implementation.
3. Add or refresh `## Changes Made`.
4. Request re-review against the same retained review record.

### If rejected

1. Update the review doc status to `rejected`.
2. Record why the target is rejected.
3. Update the governed backlog item so the repo no longer implies approval is pending.

## Lifecycle

```text
pending -> approved
pending -> changes_requested -> approved
pending -> rejected
changes_requested -> rejected
```

Review docs are retained. They are not disposable checklists.

## Legacy migration note

- Old epic-ledger supplemental review patterns are legacy.
- When touched, split supplemental review sections into their own target-based review docs.
- A separate legacy migration pass can refactor older records that still bundle multiple review
  cycles or reuse the same epic review id across unrelated documents.

## Template

Use [template-review.md](../templates/template-review.md) when creating new reviews.
