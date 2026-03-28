---
type: review
id: REV-EPIC-29
title: "Review: Klassrumskartan desktop-first workspace overhaul"
status: changes_requested
owners: "agents"
created: 2026-03-28
reviewer: "lead-developer"
epic: EPIC-29
adrs:
  - ADR-0069
  - ADR-0071
  - ADR-0072
stories:
  - ST-29-01
  - ST-29-02
  - ST-29-03
  - ST-29-04
  - ST-29-05
  - ST-29-06
  - ST-29-07
---

## TL;DR

EPIC-29 proposes a dedicated redesign lane for Klassrumskartan now that the planner logic is
largely in place. The package keeps core planner contracts stable while overhauling the interface
as a desktop-first, symbol-led, workspace-heavy product: shared control primitives first, shell
compression second, then overview/grouping/seating/rules composition, and only after that a reduced
mobile companion layout.

## Problem Statement

Klassrumskartan has reached the point where presentation quality is the main product risk. The
planner works, but the current interface still spends too much visual budget on stacked bands,
card-equal sections, and text-heavy controls. Existing nearby polish stories help, but they do not
yet form a coherent redesign framework or a clear desktop-first end-state.

## Proposed Solution

Create a new dedicated redesign epic instead of stretching EPIC-26 export/import work or EPIC-27
smart-assignment work beyond their reviewed scope. Start with canonical symbols and shared control
primitives, then compress the shell and stabilize shared desktop workspace composition, then
redesign overview/grouping/seating/rules in order, and only then define reduced mobile companion
layouts. Use the new workspace doctrine as the planning reference throughout.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md` | Target end-state and desktop-first doctrine | 6 min |
| `docs/backlog/epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md` | Scope and sequencing | 8 min |
| `docs/backlog/stories/story-29-01-klassrumskartan-canonical-operation-symbols-and-planner-control-primitives.md` | Shared symbols and control system | 5 min |
| `docs/backlog/stories/story-29-02-klassrumskartan-workspace-shell-compression-and-low-value-feedback-band-reduction.md` | Shell compression and feedback model | 5 min |
| `docs/backlog/stories/story-29-03-klassrumskartan-shared-desktop-workspace-composition-primitives.md` | Shared desktop layout primitives | 5 min |
| `docs/backlog/stories/story-29-04-klassrumskartan-overview-hierarchy-and-class-first-dashboard-redesign.md` | Overview hierarchy | 4 min |
| `docs/backlog/stories/story-29-05-klassrumskartan-grouping-and-seating-desktop-workspace-overhaul.md` | Grouping and seating composition | 5 min |
| `docs/backlog/stories/story-29-06-klassrumskartan-rules-workspace-rail-map-inspector-rebalance.md` | Rules workspace hierarchy | 4 min |
| `docs/backlog/stories/story-29-07-klassrumskartan-reduced-mobile-companion-layouts-and-breakpoint-cutover.md` | Mobile companion scope and breakpoint policy | 4 min |

**Total estimated time:** ~46 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| New epic instead of extending EPIC-26 or EPIC-27 | Export/import and smart-assignment are active but narrower lanes; the redesign needs its own outcome and review surface | [ ] |
| Desktop-first is the canonical product stance | Prevent desktop workspaces from collapsing into mobile-first stacked compromises | [ ] |
| Symbol system ships before layout restyling | Shared operation language must stabilize before workspace-specific redesign begins | [ ] |
| Shared primitives ship before workspace-specific slices | Later stories should build on common shell/zoning/scroll/control seams | [ ] |
| Reduced mobile companion layouts ship last | Smaller-screen behavior should adapt from the settled desktop product, not shape it prematurely | [ ] |

## Review Checklist

- [x] ADRs still provide sufficient product/contract boundaries
- [x] EPIC scope is appropriate
- [ ] Stories have testable acceptance criteria
- [ ] Sequencing reduces redesign risk instead of front-loading visual churn
- [ ] Risks and overlaps with existing EPIC-26 stories are identified clearly

## Review Feedback

**Reviewer:** @lead-developer
**Date:** 2026-03-28
**Verdict:** changes_requested

### Required Changes

1. Resolve the EPIC-26 overlap explicitly before approval. `ST-26-06`, `ST-26-07`, and
   `ST-26-08` cannot remain as a parallel ready polish lane while `ST-29-03` and `ST-29-04`
   absorb the same desktop composition and hierarchy work. Update EPIC-26 / EPIC-29 so it is
   clear whether those stories are prerequisites, folded in, or superseded.
2. Define a canonical viewport-proof matrix for the redesign. The doctrine/epic should name the
   exact breakpoint tokens or viewport widths used for `phone`, `tablet`, `laptop`, and
   `desktop` proof so the repeated "canonical desktop widths" / "common laptop widths" acceptance
   criteria become reviewable instead of interpretive.
3. Move the accessibility/discoverability requirement in `ST-29-01` into acceptance criteria.
   Icon-first controls are the right direction, but tooltip/label/aria expectations cannot live
   only in notes if this story is meant to lock the shared control contract.
4. Align the sequencing contract for `Regler`. `ST-29-06` should either depend on `ST-29-03` or
   explicitly explain why the rules workspace is allowed to bypass the shared desktop-composition
   primitives even though the epic says workspace-specific slices build on them.

### Suggestions (Optional)

- If `ST-26-06`, `ST-26-07`, and `ST-26-08` are folded into EPIC-29, preserve their sharper
  desktop-proof language so the redesign stories inherit concrete usability checks instead of only
  aesthetic direction.

### Decision Approvals

- [x] New epic instead of extending EPIC-26 or EPIC-27
- [x] Desktop-first as the canonical product stance
- [x] Symbol system before layout restyling
- [ ] Shared primitives before workspace-specific slices
- [x] Reduced mobile companion layouts last

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `EPIC-29` | Drafted a dedicated redesign epic aligned to the new workspace doctrine |
| 2 | `ST-29-01`..`ST-29-07` | Added a paced story stack from shared symbols/primitives into workspace-specific redesign and responsive cutover |
| 3 | `REV-EPIC-29` | Created the required review surface before any implementation begins |
| 4 | `EPIC-26`, `EPIC-29`, `PR-0127`..`PR-0132`, `ST-29-03`, `ST-29-04` | Resolved overlap by moving redesign execution ownership into `EPIC-29`, reparenting the applicable task slices into the new story stack, and removing the conflicting EPIC-26 story docs |
| 5 | `EPIC-29`, `REF-klassrumskartan-workspace-ui-doctrine-2026-03-28`, `ST-29-02`..`ST-29-07` | Added an explicit `phone` / `tablet` / `laptop` / `desktop` viewport-proof matrix and updated acceptance criteria to reference the named review viewports |
| 6 | `ST-29-01` | Moved icon accessibility and discoverability requirements into acceptance criteria so the symbol-system slice locks both space efficiency and usability |
| 7 | `ST-29-06` | Added `ST-29-03` as an explicit dependency so the rules workspace cannot bypass shared desktop-composition primitives |
