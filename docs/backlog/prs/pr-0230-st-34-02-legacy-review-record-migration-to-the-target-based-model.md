---
type: pr
id: PR-0230
title: "ST-34-02 legacy review-record migration to the target-based model"
status: done
owners: "agents"
created: 2026-04-06
updated: 2026-04-06
stories:
  - "ST-34-02"
tags: ["docs", "planning", "review", "governance", "migration"]
dependencies:
  - "ST-34-01"
  - "REF-review-workflow"
  - "REF-sprint-planning-workflow"
acceptance_criteria:
  - "Given the remaining duplicate review-id families still conflict with the current docs-as-code contract, when this task is complete, then the touched review records have unique target-based ids/filenames or explicit legacy framing with corrected crosslinks."
  - "Given the migration changes retained decision records rather than product behavior, when this task is complete, then the scope is limited to review docs, supporting backlog/index references, and related docs-governance surfaces needed to keep the planning trail coherent."
  - "Given the target-based review workflow is the canonical rule now, when this task is complete, then `docs/index.md`, `.agents/handoff.md`, and the touched backlog docs all point to the migrated review records consistently and `pdm run docs-validate` passes."
---

## Problem

The repo now documents and validates a target-based retained review model, but several older review
families still reuse one epic review id across multiple files. That leaves historical ambiguity in
the backlog and makes the docs-as-code contract look newer than the actual retained review archive.

## Goal

Migrate the remaining legacy review-record families to the current target-based model without
destroying historical decision context.

This slice should:

1. inventory the current duplicate-id families that still conflict with the target-based model
2. map each touched record to a primary epic/story/PR target or to an explicit legacy exception
3. rewrite or relabel the records so ids, filenames, links, and backlog references tell the same
   story as `REF-review-workflow`
4. leave the repo with one discoverable planning contract for retained review records

## Non-goals

- No product, runtime, UI, or API behavior changes.
- No blanket rewrite of every historical backlog doc that mentions old planning language.
- No deletion of retained review records without an explicit migration rationale.
- No invention of a new review-doc type beyond the current epic/story/PR target-based model.

## Migration taxonomy

Use this taxonomy when deciding how to handle each touched review doc.

### Type A. Canonical epic review

The review genuinely governs an epic-level decision surface and should remain the one retained
`REV-EPIC-*` record for that family.

Signals:

- the review is primarily about approving or rejecting the epic package itself
- the review target is still best understood as the epic rather than one later story or PR
- later implementation slices can be linked as context rather than bundled into the same review

Action:

- keep one file as the canonical epic review
- rewrite it to the current review template shape if needed
- move non-epic follow-up material out into story/PR reviews when that material is actually its own
  decision surface

### Type B. Canonical story review

The review really governs a story-sized decision surface and should become `REV-ST-*`.

Signals:

- one story clearly drives the scope, acceptance criteria, or decision burden
- the review bundles related supporting stories, but one story is the real primary target
- the body reads like a story gate rather than an epic package approval or a single PR check

Action:

- rename to `review-st-XX-YY-*.md`
- change frontmatter `id` to `REV-ST-XX-YY`
- put the primary story first in `stories:`
- keep secondary stories only if the review genuinely governs them together

### Type C. Canonical PR review

The review really governs a bounded implementation slice and should become `REV-PR-*`.

Signals:

- the review title/body is about one named PR or one implementation follow-up slice
- verification and risks are PR-scoped rather than story- or epic-scoped
- the doc reviews implementation alignment after planning decisions were already accepted elsewhere

Action:

- rename to `review-pr-XXXX-*.md`
- change frontmatter `id` to `REV-PR-XXXX`
- use `prs:` as the primary target field
- move broader epic/story context into `links:` or body text

### Type D. Canonicalized migrated legacy review

The historical record is worth retaining, but the current file shape or targeting is no longer
canonical. The content should still be normalized into the modern review template and mapped to one
primary target.

Signals:

- the doc is historically important, but currently uses a legacy epic-ledger or free-form shape
- the content spans more than one artifact, yet one primary target can still truthfully anchor it
- rewriting the structure improves clarity without falsifying the decision history

Action:

- retarget the doc to one epic/story/PR owner
- rewrite the body into the canonical section order from `template-review.md`
- add a short note in `TL;DR` or `Problem Statement` that the review was migrated from the legacy
  retained-review archive
- preserve historical context inside normal sections, not via bespoke structure or new frontmatter

### Type E. Split candidate

The file is carrying multiple real review surfaces and should be broken up so each retained review
matches one primary target.

Signals:

- multiple unrelated review cycles are bundled into one file
- one file contains both an original package approval and later implementation/re-review gates
- different sections clearly belong to different stories or PRs with different outcomes

Action:

- create separate target-based review docs for the distinct review surfaces
- keep one file per primary target
- leave cross-links between the resulting docs so the historical trail stays discoverable
- only keep multiple supporting targets in one file when they are still one genuine shared review

### Type F. Historical reference only

The doc contains useful historical context, but it is not itself a distinct retained review surface
once the migration is complete.

Signals:

- the file mostly duplicates decisions already retained more cleanly elsewhere
- the file is a review brief, checklist, or working packet rather than a completed retained review
- its useful content can be preserved by folding it into `Artifacts to Review`, `Review Feedback`,
  or `Changes Made` in a canonical target-based record

Action:

- prefer refactoring or splitting before considering retirement
- if the content is fully absorbed elsewhere, record that rationale explicitly in the migration notes
- do not silently delete or orphan the historical trail

## Decision tree

Use this sequence for every touched review doc.

1. Does the file already match the current review template shape and target-based frontmatter?
   - If yes, keep the structure and only retarget/rename if the primary target is wrong.
   - If no, rewrite it into the canonical review shape. Legacy meaning may stay; legacy structure may
     not.
2. What is the true primary target today?
   - If the doc primarily governs an epic package, classify as Type A.
   - If it primarily governs one story, classify as Type B.
   - If it primarily governs one PR slice, classify as Type C.
3. Does the file still contain only one real review surface?
   - If yes, migrate it as one canonical review doc.
   - If no, classify as Type E and split it into separate target-based review docs before final
     cleanup.
4. Can one primary target truthfully anchor the retained historical record after rewrite?
   - If yes, classify as Type D and normalize the content into the canonical template.
   - If no, split the file further until each resulting doc has one truthful primary target.
5. Is any remaining content just support material rather than its own retained review?
   - If yes, treat that material as Type F and fold it into canonical sections or cross-links rather
     than preserving a bespoke review file.
6. After migration, does the result look like a new review doc created today?
   - If no, the migration is not finished. Rewrite section order, title, frontmatter, and link shape
     until it does.

## Refactor-first rules for oddball reviews

- Do not preserve oddball structure merely because it is old.
- Prefer splitting a mixed review into multiple canonical reviews over forcing several unrelated
  decisions into one retained file.
- Prefer story/PR targets over epic targets when the body is really about one implementation slice
  or one follow-up decision gate.
- Preserve historical honesty through explicit notes in canonical sections, not through bespoke
  headings, ad hoc metadata, or free-form review ledgers.
- A migrated review should be understandable to a new developer without needing to know the legacy
  review model first.

## First-pass taxonomy checklist

This is the initial migration assessment for the currently known duplicate-id families. Treat it as
the default starting point for implementation. If a later close read disproves one of these
classifications, update this checklist in the same PR so the repo records why.

### `REV-EPIC-08` family

- [x] [review-epic-08-ai-completion.md](../reviews/review-epic-08-ai-completion.md)
  - First-pass type: **Type A. Canonical epic review**
  - First-pass action: keep as the sole `REV-EPIC-08` record; rewrite only as needed to match the
    current canonical review shape.

- [x] [review-st-08-24-ai-edit-ops-anchor-patch-v2.md](../reviews/review-st-08-24-ai-edit-ops-anchor-patch-v2.md)
  - First-pass type: **Type B. Canonical story review**
  - First-pass action: retarget to `ST-08-24` as `REV-ST-08-24` and normalize to the modern review
    template.

- [x] [review-st-08-27-editor-chat-virtual-file-context-retention-and-tokenizers.md](../reviews/review-st-08-27-editor-chat-virtual-file-context-retention-and-tokenizers.md)
  - First-pass type: **Type B. Canonical story review**
  - First-pass action: retarget to `ST-08-27` as `REV-ST-08-27` and normalize to the modern review
    template.

- [x] [ref-pr-0031-edit-ops-patch-workflow-brief.md](../../reference/ref-pr-0031-edit-ops-patch-workflow-brief.md)
  - First-pass type: **Type F. Historical reference only**
  - First-pass action: preserve the historical patch-workflow brief as linked support material for
    `REV-PR-0031` instead of retiring it as an absorbed review record.

- [x] [review-st-08-28-ai-chat-ops-response-capture-on-error.md](../reviews/review-st-08-28-ai-chat-ops-response-capture-on-error.md)
  - First-pass type: **Type B. Canonical story review**
  - First-pass action: retarget to `ST-08-28` as `REV-ST-08-28` and normalize to the modern review
    template.

- [x] [review-pr-0031-editor-ai-edit-ops-patch-only-alignment.md](../reviews/review-pr-0031-editor-ai-edit-ops-patch-only-alignment.md)
  - First-pass type: **Type C. Canonical PR review**
  - First-pass action: retarget to `PR-0031` as `REV-PR-0031` and normalize to the modern review
    template.

### `REV-EPIC-14` family

- [x] [review-epic-14-editor-sandbox-preview.md](../reviews/review-epic-14-editor-sandbox-preview.md)
  - First-pass type: **Type A. Canonical epic review**
  - First-pass action: keep as the sole `REV-EPIC-14` record; rewrite only as needed to match the
    current canonical review shape.

- [x] [review-st-14-35-tool-data-libraries.md](../reviews/review-st-14-35-tool-data-libraries.md)
  - First-pass type: **Type B. Canonical story review**
  - First-pass action: retarget to `ST-14-35` as `REV-ST-14-35`, keeping `ST-14-36` only as
    supporting governed scope if that still reflects the real decision surface.

- [x] [review-st-14-23-ui-contract-v2x-action-prefill.md](../reviews/review-st-14-23-ui-contract-v2x-action-prefill.md)
  - First-pass type: **Type B. Canonical story review**
  - First-pass action: retarget to `ST-14-23` as `REV-ST-14-23` and normalize to the modern review
    template.

### `REV-EPIC-23` family

- [x] [review-epic-23-group-seating-studio.md](../reviews/review-epic-23-group-seating-studio.md)
  - First-pass type: **Type A. Canonical epic review**
  - First-pass action: keep as the sole `REV-EPIC-23` record; rewrite only as needed to match the
    current canonical review shape.

- [x] [review-st-23-06-group-seating-studio-draft-persistence.md](../reviews/review-st-23-06-group-seating-studio-draft-persistence.md)
  - First-pass type: **Type D. Canonicalized migrated legacy review**
  - First-pass action: retarget to one story-owned review surface, with `ST-23-06` as the current
    preferred first-pass anchor unless a closer read proves another primary target is more honest;
    fully rewrite it into the modern review template while preserving its retrospective meaning in
    canonical sections.

### Watch-list items during execution

- [x] Re-check whether any material extracted from the historical patch-workflow brief should end up
  classified as **Type F. Historical reference only** after its real retained review surfaces have
  been split out. Result: the brief was preserved as linked support material for `REV-PR-0031`
  instead of being retired.
- [x] Re-check whether `review-st-23-06-group-seating-studio-draft-persistence.md` remains a single
  **Type D** migrated review after rewrite, or whether a closer pass shows it is actually a
  **Type E** split candidate. Result: it remains a single story review anchored on `ST-23-06`.

## Implementation plan

### Checkpoint A. Inventory and target mapping

1. Audit the remaining duplicate-id review families, starting with the current `REV-EPIC-08`,
   `REV-EPIC-14`, and `REV-EPIC-23` clusters.
2. Decide, for each touched record, whether it should become:
   - an epic-target review doc
   - a story-target review doc
   - a PR-target review doc
   - or a split set of target-based review docs when one file currently carries multiple review
     surfaces

3. Classify each touched review using the migration taxonomy above and record the intended action:
   keep, retarget, rewrite, split, or absorb as historical support material.

### Checkpoint B. Rewrite the retained review records

1. Update filenames, `id`, and primary-target frontmatter to match the chosen target-based shape.
2. Rewrite each touched review so it matches the current canonical review template shape and section
   order, even when the source document began as a legacy or free-form review record.
3. Move broader historical context into `links:` or body notes rather than keeping it bundled as an
   implicit epic-ledger review gate.
4. Preserve historical honesty through explicit notes inside canonical sections, not by keeping
   legacy structure.
5. If a file still carries multiple real review surfaces after the rewrite, split it further rather
   than preserving a structurally odd retained record.

### Checkpoint C. Repair crosslinks and planning surfaces

1. Update `docs/index.md` so it points to the migrated review docs.
2. Update touched backlog docs and `.agents/handoff.md` so active planning notes stop implying the
   older bundled-review shape.
3. Keep [REF-review-workflow](../../reference/ref-review-workflow.md) as the governing migration
   reference throughout the slice.

### Checkpoint D. Validate the contract

1. Run `pdm run docs-validate`.
2. Spot-check the migrated records against the primary-target rules in
   [REF-review-workflow](../../reference/ref-review-workflow.md).

## Test plan

- `pdm run docs-validate`
- `rg -n "REV-EPIC-08|REV-EPIC-14|REV-EPIC-23" docs/backlog/reviews docs/index.md docs/backlog -g '*.md'`

## Rollback plan

This slice is docs-only.

If a migrated review record proves historically misleading:

1. keep `EPIC-34` active
2. create a correcting follow-up under `ST-34-02`
3. restore the affected record only with explicit legacy framing, not by silently reviving the old
   bundled-review contract
