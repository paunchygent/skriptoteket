---
type: review
id: REV-EPIC-24
title: "Review: Klassrumskartan Slice 1 Assessment & Slice 2 Planning"
status: pending
owners: "agents"
created: 2026-03-20
reviewer: "external-architect"
epic: EPIC-24
adrs:
  - ADR-0069
stories: []
---

## TL;DR

Epic 23 (Slice 1 of the Group Seating Studio) has been successfully implemented and packaged into `repomix-epic-23-implementation.xml`. We are requesting a review of the implementation against our architectural rules, and seeking guidance for planning Epic 24 (Slice 2) which introduces the suggestion engine, constraints, and snapshot finalization.

## Problem Statement

To seamlessly transition from the manual planning foundation (Slice 1) to the intelligent recommendation phase (Slice 2), we need architectural validation of the current baseline and structural decisions on how the suggestion engine will operate without violating our "no vibe-coding / explicit rules" and "teacher-first" mandates.

## Proposed Solution / Review Focus

1. **Implementation Assessment (Slice 1)**: Review the provided XML package to ensure the `ClassroomPlannerView.vue` shell, the normalized Pinia state (`useClassroomState.ts`), and the SQLAlchemy persistence models (`Roster`, `RoomTemplate`, `PlanDraft`) adhere to ADR-0069.
2. **Slice 2 Planning Guidance**: Provide direction on the architectural patterns for:
   - The Constraint / Scoring Engine (where should rules live? Client-side or Server-side?)
   - Snapshot Finalization (deep copy immutability implementation)

## Artifacts to Review

| File/Artifact | Focus | Time |
|------|-------|------|
| `repomix-epic-23-implementation.xml` | Codebase structural compliance, DI wiring, Pinia state normalization | 30 min |
| `docs/adr/adr-0069-group-seating-studio-domain-model.md` | Baseline rules for persistence vs assignments | 10 min |
| `docs/prd/prd-group-seating-studio-v0.1.md` | Product rules for Slice 2 features | 5 min |

**Total estimated time:** ~45 minutes

## Key Decisions Needed for Slice 2

| Decision | Context | Guidance Needed |
|----------|-----------|----------|
| **Suggestion Engine Location** | Will the solver run purely in the browser (TS) using the normalized state, or remotely (Python) requiring round-trips? | [ ] |
| **Constraint Model** | How should teacher constraints (e.g., "keep apart", "needs focus") be modeled in the database and mapped to students? | [ ] |
| **Validation UX** | Real-time warnings vs. explicit "Validate" button? | [ ] |

## Review Checklist

- [ ] Implementation of Slice 1 adheres to ADR-0069
- [ ] Code quality meets `skriptoteket` standards (<500 LOC, Protocol-first DI)
- [ ] Clear path established for Epic 24 (Slice 2) architecture
- [ ] Constraints and scoring rules align with "suggest and explain" product boundaries

---

## Review Feedback

**Reviewer:** @external-architect
**Date:** YYYY-MM-DD
**Verdict:** [pending | approved | changes_requested | rejected]

### Assessment of Slice 1

[Feedback on the provided `repomix` implementation package]

### Architectural Guidance for Slice 2

[Specific direction on how to architect the Suggestion Engine and Snapshot Finalization]

### Recommendations / Requirements for EPIC-24

[High-level list of technical requirements to seed the EPIC-24 stories]

### Decision Approvals

- [ ] Suggestion Engine Location
- [ ] Constraint Model
- [ ] Validation UX
