---
type: epic
id: EPIC-24
title: "Curated app: Klassrumskartan (Fundamentals Recovery)"
status: active
owners: "agents"
created: 2026-03-20
updated: 2026-03-21
outcome: "Teachers work from a class-first workspace, enter separate grouping or seating drafts as needed, use classrooms as secondary context, and save meaningful class-owned history without being forced through undeclared advanced planning controls."
dependencies: ["ADR-0059", "ADR-0069", "ADR-0071", "ADR-0072", "EPIC-23"]
---

## Scope

- Re-center Klassrumskartan on a teacher-first, fundamentals-only workflow.
- Make `Class` the primary anchor of the product and treat `Classroom` as secondary reusable context.
- Keep the landing page the default first interaction again, but evolve it away from symmetric class/classroom launch selection and toward a class-first workspace.
- Re-center the app around class-scoped work:
  - active seating draft
  - active grouping draft
  - secondary class-owned history
- Treat `Grupper` and `Sittplatser` as two separate planner tasks with separate draft semantics, separate mental models, and separate visible controls.
- Preserve `Slumpa` as a practical helper, but keep smart logic and tunable settings out of the default main view.
- Split randomize/save behavior by teacher task so grouping and seating stop behaving like one global workspace action.
- Allow grouping to be classroom-agnostic or classroom-aware.
- Require seating to be classroom-bound.
- Let teachers save meaningful named outputs:
  - named groupings for completed group assignments
  - named seating arrangements for completed seat assignments
- Model saved outputs as class-owned teacher artifacts that can be renamed, edited, deleted, and later surfaced through the vault without mutating the live draft.
- Persist saved arrangements and their relevant settings into the user file vault so the work can be found, edited, and deleted later.
- Add an explicit draft lifecycle so the server understands active/resumable/abandoned/history work instead of accumulating hidden orphan drafts.
- Establish one active draft per class per draft kind, with automatic demotion of the previous active draft of the same kind to history.
- Remove superseded solver-first planner contracts from the active codebase before later class-first workspace, grouping, and seating slices continue.

## Out of scope

- Re-exposing the validation panel, suggestion engine, snapshot history, or abstract planning-rule language in the default planner view.
- Visible pair-rule controls, zone-preference controls, or multi-slider rule-engine tuning in the main teacher workflow.
- Full smart-placement settings design beyond what is required to keep future defaults hidden and separate.
- Export generation itself (PDF/XLSX), even if this epic prepares the saved-arrangement concepts used later.
- Treating the current whole-workspace `ArrangementSnapshot` finalize flow as the teacher-facing save model for groupings or seating arrangements.
- Treating generic abandoned drafts as the preferred future history source for smart placement.

## Stories

- [x] [ST-24-01: Landing page fundamentals](../stories/story-24-01-group-seating-studio-landing-page-fundamentals.md)
- [x] [ST-24-05: Codebase realignment and superseded contract removal](../stories/story-24-05-group-seating-studio-codebase-realignment-and-superseded-contract-removal.md)
- [ ] [ST-24-02: Class-first workspace and draft entry](../stories/story-24-02-group-seating-studio-class-first-workspace.md)
- [ ] [ST-24-03: Grouping fundamentals + saved groupings](../stories/story-24-03-group-seating-studio-grouping-fundamentals-and-saved-groupings.md)
- [ ] [ST-24-04: Seating fundamentals + saved seating arrangements](../stories/story-24-04-group-seating-studio-seating-fundamentals-and-saved-arrangements.md)

## Implementation Summary (as of 2026-03-21)

- EPIC-24 has been re-scoped away from the earlier “show everything” Slice 2 surface.
- The governing product direction is now fundamentals first:
  - class-first workspace hierarchy
  - separate grouping and seating work
  - classrooms as secondary context
  - hidden smart logic/settings until explicitly defined and approved
- A remediation gate now precedes the later stories:
  - `ST-24-05` removes superseded solver-first contracts from the active codebase
  - later stories must build on a cleaned planner contract rather than preserve legacy planner state, APIs, or persistence seams
- `ST-24-05` is now implemented locally across `PR-0082` to `PR-0085`:
  - visible legacy planner surfaces are removed
  - frontend store/types no longer encode superseded planner semantics
  - backend/domain/persistence no longer expose lesson-mode/suggestion/snapshot/global-randomize contracts
  - draft lifecycle is now class-scoped by draft kind (`grouping` / `seating`) instead of owner-global
- ST-24-01 shipped locally across PR-0079 to PR-0081 as a recovery slice:
  - landing page no longer exposes lesson mode as part of the default teacher workflow
  - planner start currently depends on class + classroom only and returns cleanly to the landing page
  - resumable work is explicit through `POST /drafts/resolve` and `GET /drafts/resumable`
  - roster/template delete is blocked when an active draft still depends on the asset, with teacher-facing modal feedback
  - this slice is explicitly transitional; ST-24-02 replaces the symmetric class/classroom launch model with a class-first workspace
- The newer review guidance also clarifies three structural decisions for implementation:
  - class-first workspace with classrooms as secondary context
  - one active draft per class per draft kind
  - named saved outputs as class-owned teacher artifacts, not unnamed whole-workspace snapshots
- `ST-24-02`, `ST-24-03`, and `ST-24-04` now depend on the remediation gate because the current
  code still contains active solver-era models, routes, store state, and owner-global draft
  invariants that would otherwise bleed into later work.
- Future smart placement, historical reuse, and constraint logic remain valid long-term goals, but should only ship through later approved stories after the fundamentals above are trusted.
