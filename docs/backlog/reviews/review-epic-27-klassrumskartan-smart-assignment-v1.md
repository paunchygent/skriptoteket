---
type: review
id: REV-EPIC-27
title: "Review: Klassrumskartan smart assignment v1"
status: approved
owners: "agents"
created: 2026-03-25
updated: 2026-05-11
reviewer: "lead-developer"
epic: EPIC-27
adrs:
  - ADR-0074
stories:
  - ST-27-01
  - ST-27-02
  - ST-27-06
  - ST-27-03
  - ST-27-07
  - ST-27-04
  - ST-27-05
---

## TL;DR

EPIC-27 proposes the first approved smart-assignment lane for Klassrumskartan after fundamentals
and explicit seating exports. The package keeps the visible teacher model intentionally small,
reuses `Slumpa` as the main action with a small per-mode `Smart` toggle, moves primary smart-rule
authoring into a dedicated `Regler` workspace, defines export-backed checkpoints as the only
smart-history source, and reintroduces smart grouping/seating through a clean backend-owned
contract rather than by reviving the older solver-first shell.

## Problem Statement

Klassrumskartan now has the right fundamentals and the first explicit seating export artifacts, but
it still lacks the later smart-assignment lane that the product direction reserved. The current
codebase also contains the opposite risk: the old solver-era contract was already removed, so
smart behavior cannot safely return through ad hoc tweaks to the existing randomizer, the old
planner-note surface, a seating-embedded rule panel, or a drawer-first per-student editing model.

## Proposed Solution

Create a new smart-assignment package with:

- a fresh ADR for controls, checkpoints, and solver boundaries
- one proposed epic
- a clean contract-reset story
- an export-checkpoint history story
- separate smart seating and smart grouping stories
- one shared rules-workspace cut-over story
- a final explanation/rerun-messaging polish story

The package keeps the smart model intentionally small, deletes the older visible planner metadata
semantics instead of mapping them forward, treats successful changed exports as the only eligible
history checkpoints, and keeps the student metadata drawer secondary to the main smart workflow.
After `PR-0151` clarified the backend ownership boundary, the package also now includes one
explicit frontend remediation slice so the planner session shape mirrors that split instead of
re-coupling it through one shared save contract.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/reference/ref-klassrumskartan-smart-assignment-v1-decision-memo-2026-03-25.md` | Locked product decisions and repo conflicts | 6 min |
| `docs/adr/adr-0074-klassrumskartan-smart-assignment-v1.md` | Controls, checkpoints, persistence, solver boundaries | 8 min |
| `docs/backlog/epics/epic-27-klassrumskartan-smart-assignment-v1.md` | Scope in/out and sequencing | 6 min |
| `docs/backlog/stories/story-27-01-klassrumskartan-smart-assignment-contract-reset-and-control-model.md` | Contract reset and deletion posture | 5 min |
| `docs/backlog/stories/story-27-02-klassrumskartan-export-checkpoints-for-smart-history.md` | History source and dedupe policy | 5 min |
| `docs/backlog/stories/story-27-06-klassrumskartan-planner-session-lanes-and-transition-matrix-remediation.md` | Frontend session shape and transition semantics | 6 min |
| `docs/backlog/stories/story-27-03-klassrumskartan-smart-seating-v1.md` | Seating smart lane | 5 min |
| `docs/backlog/stories/story-27-07-klassrumskartan-rules-workspace-and-dual-map-authoring.md` | Dedicated rules workspace and task-pane summary cut-over | 6 min |
| `docs/backlog/stories/story-27-04-klassrumskartan-smart-grouping-v1.md` | Grouping smart lane, classroom-aware compactness, and history split | 5 min |
| `docs/backlog/stories/story-27-05-klassrumskartan-smart-explanations-and-alternate-options.md` | Explanation and rerun-messaging UX | 4 min |
| `docs/backlog/prs/pr-0152-klassrumskartan-planner-session-lanes-and-transition-matrix-remediation.md` | Implementation-ready remediation design task | 6 min |
| `docs/backlog/prs/pr-0155-klassrumskartan-rules-workspace-dual-map-authoring-and-summary-cutover.md` | Implementation-ready dedicated rules workspace design task | 6 min |

**Total estimated time:** ~68 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Keep `Slumpa` as the main action and add a small per-mode `Smart` toggle | Preserves a low-button surface while keeping smart behavior explicit | [ ] |
| Use a dedicated `Regler` workspace plus compact task-pane summaries instead of drawer-first per-student editing | Matches the teacher's whole-class mental model without bloating `Sittplatser`/`Grupper` | [ ] |
| Use export-backed checkpoints only, with assignment-hash dedupe | Aligns history input with current PRD/ADR direction and avoids raw-draft ambiguity | [ ] |
| Delete old visible planner metadata semantics without migration | Cleaner reset than mixing incompatible teacher models; no real users exist yet | [ ] |
| Keep smart grouping and smart seating in the same epic, but with separate mode toggles | Matches the shared hidden relation model while preserving separate teacher tasks | [ ] |
| Keep classroom-aware grouping separate from history and expose it through `Klassrum` + `Sittschemat` in Smart-inställningar | Preserves clear teacher intent without turning history into a hidden room-awareness switch | [ ] |
| Soft-degrade history-enabled first runs with no eligible checkpoints | Prevents error-like first-run feedback while keeping draft history ineligible | [ ] |
| Treat later grouping checkpoints as the primary grouping-history lane | Keeps grouping mode-specific while still allowing seating checkpoints as a secondary source | [ ] |
| Mirror roster-global vs draft-local ownership in the frontend session shape | Prevents one shared planner save contract from reintroducing the same transition bugs under new names | [ ] |

## Review Checklist

- [ ] ADR defines a clear contract reset
- [ ] EPIC scope is appropriate and does not reopen the solver-first shell
- [ ] Primary smart-rule authoring is centered in `Regler`, not in drawers or task-pane editors
- [ ] Stories have testable acceptance criteria
- [ ] Implementation direction aligns with the repo's current class-first planner architecture
- [ ] Frontend transition semantics are explicit and lane-owned
- [ ] Risks and deletion posture are explicit

## Review Feedback

**Reviewer:** @lead-developer
**Date:** 2026-03-25
**Verdict:** approved

### Required Changes

- None.

### Suggestions (Optional)

- None.

### Decision Approvals

- [x] Keep `Slumpa` as the main action and add a small per-mode `Smart` toggle
- [x] Use a dedicated `Regler` workspace plus compact task-pane summaries instead of drawer-first per-student editing
- [x] Use export-backed checkpoints only, with assignment-hash dedupe
- [x] Delete old visible planner metadata semantics without migration
- [x] Keep smart grouping and smart seating in the same epic
- [x] Keep classroom-aware grouping separate from history and expose it through `Klassrum` + `Sittschemat` in Smart-inställningar
- [x] Mirror roster-global vs draft-local ownership in the frontend session shape

## Post-Approval Refinements

- 2026-03-26 product-direction correction before further implementation:
  - the primary smart editing flow is now explicitly class-wide and visual
  - `Support seat` is replaced with seating-only `Närmare läraren`
  - the student metadata drawer is now secondary notes/history only
- 2026-03-27 post-approval frontend session remediation:
  - review of the post-`PR-0151` shape found the backend ownership boundary mostly correct but the
    frontend still partially behaving like one shared planner save machine
  - added `ST-27-06` plus `PR-0152` to lock the required cut-over to one session controller, one
    draft lane, one smart-rule lane, one separate smart-rule UI bucket, and an explicit transition
    matrix
  - locked draft-first fail-safe workspace loading, draft-only `undo` / `redo`, smart-lane-first
    `abandonDraft` semantics with explicit class-wide discard wording, one timer per lane, and a
    strict separation between smart-rule hydration failure and smart-rule persistence failure
- 2026-03-25 reviewer findings were resolved before approval:
  - common smart controls are now explicitly separate from the grouping-only
    classroom-aware lane
  - later grouping checkpoints are now the primary grouping-history lane
  - history-enabled smart runs originally blocked with a short message when no eligible
    checkpoints existed; `PR-0316` later supersedes that first-run behavior with no-history
    soft-degrade while keeping checkpoint-only history sources
  - checkpoint dedupe now defines canonical assignment-hash semantics
  - smart reruns now belong to the core `Slumpa` contract rather than to a
    separate alternate-result control
- 2026-03-27 workspace refinement before later UI implementation:
  - added `ST-27-07` plus `PR-0155` to make `Regler` the dedicated smart-rule authoring home
  - `Planeringskarta` is now the default desktop authoring map, with `Sittschema` as an optional
    exact-current-arrangement view
  - `Sittplatser` and `Grupper` now keep only compact smart summaries plus a small settings-link
    affordance near `Smart`; drawers may summarize but not edit rules
- 2026-04-01 planning-map product correction:
  - `Planeringskarta` is no longer allowed to reuse classroom geometry once seating/classroom
    context exists
  - `ST-27-07`, `PR-0155`, `ADR-0074`, and `EPIC-27` are refined so the canonical behavior is now
    one permanent abstract alphabetical planning layout plus one separate exact `Sittschema` view
- 2026-03-29/2026-03-30 smart-grouping precedence refinement before `ST-27-04` implementation:
  - grouping history is now explicitly separate from classroom-aware compactness
  - grouping `Use history` now means label-insensitive grouping anti-repeat memory based on
    normalized student partitions and repeated co-memberships rather than raw group ids
  - classroom-aware grouping is now exposed through `Klassrum` + `Sittschemat` in Smart-inställningar
    rather than described as a separate seat-distance toggle
  - classroom-aware grouping now means a soft seat-topology compactness lane that reads the active
    seating draft first and eligible seating checkpoints second, penalizing same-group spread
    quadratically beyond a local elastic radius instead of acting like grouping history
  - for smart grouping, rerun diversity now sits below explicit relation rules, classroom-aware
    compactness when enabled, and grouping-history anti-repeat memory
- 2026-03-30 compactness-tuning simulation follow-up under `ST-27-04`:
  - the first tuning lane should evaluate whole-class seating projections rather than sparse
    continuity hints
  - the primary operator artifact is now a rough seating-map overlay with group-colored student
    squares plus disconnected component boxes so local clusters, splashes, and islands remain
    visible
  - compactness tuning should be reviewed from both metrics and overlays, not from prose or raw
    scores alone
- 2026-05-11 Smart history first-run refinement under `ST-27-05` / `PR-0316`:
  - authenticated `Historik` remains default-on
  - no eligible checkpoints is treated as a normal first-run state
  - Smart seating/grouping runs without history, reports `used_history=false`, and shows normal
    Smart-run feedback
  - raw drafts, undo/redo, abandoned drafts, history-drawer drafts, and public guest local state
    remain ineligible as Smart-history sources

## Suggested Approval Wording

**Reviewer:** @lead-developer
**Date:** 2026-03-25
**Verdict:** approved

EPIC-27 is approved as the next Klassrumskartan lane after the fundamentals and
explicit export work. The package keeps the visible teacher model intentionally
small, reuses `Slumpa` with small per-draft `Smart` toggles, uses explicit
export-backed checkpoints instead of draft history, and reintroduces smart
grouping and seating through a clean backend-owned contract. The epic may move
to `active`, `ADR-0074` may move to `accepted`, and `ST-27-01` may move to
`active` while the remaining stories stay `ready`.

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | ADR-0074 | Drafted the smart-assignment contract reset around small controls, export checkpoints, and backend authority |
| 2 | EPIC-27 | Drafted the smart-assignment epic with explicit scope, out-of-scope, and story chain |
| 3 | ST-27-01..05 | Drafted the story package for contract reset, checkpoints, seating, grouping, and explanation UX |
| 4 | ST-27-06, PR-0152 | Added the frontend session-remediation slice so later smart seating/grouping work inherits explicit lane-owned transition semantics |
| 5 | ST-27-07, PR-0155 | Added the dedicated rules workspace cut-over so later smart seating/grouping UI does not accrete around seating/grouping drawers |
