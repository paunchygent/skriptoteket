---
type: review
id: REV-EPIC-23
title: "Review of EPIC-23: Klassrumskartan (Slice 1)"
status: approved
owners: "agents"
reviewer: "architect"
epic: "EPIC-23"
created: 2026-03-20
---

## 1. TL;DR
This review covers Slice 1 of the new "Klassrumskartan" (Group Seating Studio) curated app. It proposes treating seat assignment and group assignment as strictly decoupled, using an app-specific relational persistence model rather than generic `tool_sessions`, and implementing a manual-only drag-and-drop prototype first.

## 2. Problem Statement
The current iteration of the seating planner tool lacks strict invariant control (failing to handle seat swapping properly), relies on hardcoded room constants, and uses a standard generic runner UI that does not fit the highly interactive drag-and-drop nature of seating maps.

## 3. Proposed Solution
Build a first-class curated app using Vue SPA with `vue-draggable-plus`. Define `ADR-0069` to enforce strict domain invariants mapping `SeatAssignment` and `GroupAssignment` separately keyed on `student_id`. Slice 1 will introduce the app with backend CRUD forms for roster/room template configurations and an interactive, visually synchronized 2D grid/list workspace, deferring the generative solver algorithms to Slice 2.

## 4. Artifacts to Review
1. [ADR-0069: Klassrumskartan Domain Model and Data Persistence](../../adr/adr-0069-group-seating-studio-domain-model.md)
2. [EPIC-23: Kurated app: Klassrumskartan (Slice 1)](../../backlog/epics/epic-23-group-seating-studio.md)
3. [ST-23-01: Klassrumskartan — Registry, App Route, Bootstrap Endpoint](../../backlog/stories/story-23-01-group-seating-studio-skeleton.md)
4. [ST-23-02: Klassrumskartan — Roster/Room Persistence & Lesson Mode](../../backlog/stories/story-23-02-group-seating-studio-manual-planner.md)
5. [ST-23-03: Klassrumskartan — Group Assignment Board](../../backlog/stories/story-23-03-group-seating-studio-drag-drop-canvas.md)
6. [ST-23-04: Klassrumskartan — Seat Assignment Canvas](../../backlog/stories/story-23-04-group-seating-studio-seat-canvas.md)
7. [ST-23-05: Klassrumskartan — Cross-View Synchronization and Invariants](../../backlog/stories/story-23-05-group-seating-studio-sync-engine.md)
8. [ST-23-06: Klassrumskartan — PlanDraft Persistence and Autosave](../../backlog/stories/story-23-06-group-seating-studio-draft-persistence.md)

## 5. Key Decisions
| Decision | Description | Status |
|----------|-------------|--------|
| **App-Specific Persistence** | Dedicated robust DB models for Rosters, Templates, and Drafts instead of caching transient form data or using generic `tool_sessions`. | Pending |
| **Normalized State** | View state must not rely on fragile array mutation; assignments are mapped relationally by `student_id`. | Pending |
| **Separate Draft/Final** | Distinguish between a mutable real-time PlanDraft and an immutable ArrangementSnapshot. | Pending |
| **Decoupled Axes** | Dropping an item onto a Seat assigns the seat only. Dropping into a Group assigns the group only. | Pending |

## 6. Review Checklist
- [x] Are the 5 stories adequately isolated?
- [x] Are the acceptance criteria observable and behavior-driven?
- [x] Does the Domain Model conform to repository conventions?
- [x] Decision to decouple generative algorithms from Slice 1 mapping.

## Review Feedback

**Reviewer:** @architect
**Date:** 2026-03-20
**Verdict:** approved

### Required Changes
None, changes have been applied.

### Approved Decisions
- [x] App-Specific Persistence
- [x] Normalized State
- [x] Separate Draft/Final
- [x] Decoupled Axes
