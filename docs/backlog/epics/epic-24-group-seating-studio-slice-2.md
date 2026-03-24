---
type: epic
id: EPIC-24
title: "Curated app: Klassrumskartan (Fundamentals Recovery)"
status: active
owners: "agents"
created: 2026-03-20
updated: 2026-03-23
outcome: "Teachers work from a class-first workspace with a compact overview-first dashboard, enter separate grouping or seating drafts as needed, use classrooms as secondary context, rely on autosave plus bounded undo/redo draft history, and get task-local `Slumpa` without being forced through undeclared advanced planning controls."
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
- Preserve `Slumpa` inside both visible teacher modes:
  - grouping mode randomizes groups
  - seating mode randomizes seat assignments
- Allow grouping to be classroom-agnostic or classroom-aware.
- Keep seating outcomes classroom-bound while allowing the seating draft to open before room selection and manage room context inside the seating workspace.
- Keep one active draft per class and task, with bounded recent draft history for undo/redo inside the workspace.
- Treat autosave and in-workspace undo/redo as draft mechanics, not as teacher-facing file-vault artifacts.
- Prepare later export/checkpoint flows without conflating them with normal draft save/resume behavior.
- Add an explicit draft lifecycle so the server understands active/resumable/abandoned/history work instead of accumulating hidden orphan drafts.
- Establish one active draft per class per draft kind, with automatic demotion of the previous active draft of the same kind to history.
- Remove superseded solver-first planner contracts from the active codebase before later class-first workspace, grouping, and seating slices continue.
- Evolve `Översikt` into the compact desktop-first dashboard for:
  - resumable draft continuation
  - class selection and editing
  - classroom selection, preview, creation, editing, and delete
- Keep the remaining cutover explicit:
  - move the minimum resumable/home logic onto the new main page
  - improve it there rather than preserve the old landing CTA as a long-lived duplicate
  - then remove the separate landing page in one clean tandem cutover as soon as the replacement works
- Make `Avsluta` leave Klassrumskartan entirely after the cutover, returning the teacher to the page they entered from rather than just toggling back to overview.

## Out of scope

- Re-exposing the validation panel, suggestion engine, snapshot history, or abstract planning-rule language in the default planner view.
- Visible pair-rule controls, zone-preference controls, or multi-slider rule-engine tuning in the main teacher workflow.
- Full smart-placement settings design beyond what is required to keep future defaults hidden and separate.
- Shipping smart seating or smart grouping placement semantics in the main view before their later dedicated stories.
- Export generation itself (PDF/XLSX), even if this epic prepares the saved-arrangement concepts used later.
- Treating ordinary draft autosave or undo/redo history as the teacher-facing export or artifact model.
- Treating the current whole-workspace `ArrangementSnapshot` finalize flow as the teacher-facing save model for groupings or seating arrangements.
- Treating generic abandoned drafts as the preferred future history source for smart placement.
- Treating mobile-first composition as the primary design source for the app; desktop and laptop remain canonical.

## Stories

- [x] [ST-24-01: Landing page fundamentals](../stories/story-24-01-group-seating-studio-landing-page-fundamentals.md)
- [x] [ST-24-05: Codebase realignment and superseded contract removal](../stories/story-24-05-group-seating-studio-codebase-realignment-and-superseded-contract-removal.md)
- [x] [ST-24-02: Class-first workspace and draft entry](../stories/story-24-02-group-seating-studio-class-first-workspace.md)
- [x] [ST-24-03: Grouping fundamentals + draft history](../stories/story-24-03-group-seating-studio-grouping-fundamentals-and-saved-groupings.md)
- [x] [ST-24-04: Seating fundamentals, room-builder ergonomics, and draft history](../stories/story-24-04-group-seating-studio-seating-fundamentals-and-saved-arrangements.md)
- [ ] [ST-24-06: Seating `Slumpa` fundamentals](../stories/story-24-06-group-seating-studio-seating-slumpa-fundamentals.md)
- [ ] [ST-24-07: Overview-first workspace management](../stories/story-24-07-group-seating-studio-overview-first-workspace-management.md)
- [ ] [ST-24-08: Landing-page cutover and exit-to-origin flow](../stories/story-24-08-group-seating-studio-landing-cutover-and-exit-to-origin.md)

## Implementation Summary (as of 2026-03-23)

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
- `ST-24-02` is now implemented locally across `PR-0086` to `PR-0089`:
  - landing keeps the top-level resumable CTA outside the class workspace
  - selecting a class opens a neutral class workspace rather than jumping straight into a planner
  - overview, grouping, and seating share a fixed top toggle in the same placement and size
  - seating opens directly and assigns or switches classroom context inside the seating workspace
  - grouping remains classroom-agnostic by default with optional classroom awareness
  - switching to `Översikt` preserves active work, while `Avsluta` leaves back to the landing surface
  - grouping/seating history stays separate and secondary through task-specific drawers
- ST-24-01 shipped locally across PR-0079 to PR-0081 as a recovery slice:
  - landing page no longer exposes lesson mode as part of the default teacher workflow
  - planner start currently depends on class + classroom only and returns cleanly to the landing page
  - resumable work is explicit through `POST /drafts/resolve` and `GET /drafts/resumable`
  - roster/template delete is blocked when an active draft still depends on the asset, with teacher-facing modal feedback
  - this slice is explicitly transitional; ST-24-02 replaces the symmetric class/classroom launch model with a class-first workspace
- The newer review guidance also clarifies three structural decisions for implementation:
  - class-first workspace with classrooms as secondary context
  - one active draft per class per draft kind
  - draft-local undo/redo history now, with later explicit export artifacts instead of unnamed whole-workspace snapshots
- `ST-24-02`, `ST-24-03`, and `ST-24-04` now depend on the remediation gate because the current
  code still contains active solver-era models, routes, store state, and owner-global draft
  invariants that would otherwise bleed into later work.
- Future smart placement, historical reuse, and constraint logic remain valid long-term goals, but should only ship through later approved stories after the fundamentals above are trusted.
- `ST-24-03` is now shipped:
  - grouping has blank new-draft lifecycle, grouping-only autosave undo/redo, and class-scoped
    continuity through the secondary overlay drawer
  - historic grouping drafts can be reopened or deleted with confirmation without polluting the
    active grouping workspace
- `ST-24-04` is now shipped:
  - room-builder ergonomics and object-visual slices (`PR-0101` to `PR-0103`) are done
  - `PR-0105` shipped the seating continuity drawer in `Sittplatser`, classroom-required `Nytt
    sittschema`, and reopen/delete for historic seating drafts with a dedicated browser proof
  - `PR-0106` shipped seating-specific `Ångra` / `Gör om`, bounded in-draft history, shared
    backend undo/redo routes with neutral draft-history contracts, and a targeted browser proof
    that continuity stays draft-level while classroom switching stays outside seating undo/redo
- EPIC-24 remains open after `ST-24-04` because two user-visible fundamentals are still part of
  the intended outcome:
  - seating still lacks task-local `Slumpa`
  - the compact overview-first dashboard has not yet absorbed class/classroom management strongly
    enough to support the final landing-page cutover
- The remaining planned closure slices are now:
  - `ST-24-06`: add seating `Slumpa` as a full-draft reshuffle inside `Sittplatser`, with
    autosave and undo/redo integration but no smart-placement settings
  - `ST-24-07`: make `Översikt` the compact desktop-first dashboard for class management,
    classroom management, and the improved resumable/home surface that can replace landing
  - `ST-24-08`: perform the tandem big-bang landing-page cutover, remove the superseded
    landing-only surface immediately after the replacement works, and make `Avsluta` leave the app
    back to the teacher's entry origin
