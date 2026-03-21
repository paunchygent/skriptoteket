---
type: story
id: ST-24-05
title: "Klassrumskartan — Codebase Realignment and Superseded Contract Removal"
status: in_progress
owners: "agents"
created: 2026-03-21
updated: 2026-03-21
epic: "EPIC-24"
acceptance_criteria:
  - "Given the classroom planner codebase still contains superseded solver-first contracts, when this story is complete, then the active frontend, backend, domain, persistence, and API surfaces only express approved fundamentals and the class-first product direction."
  - "Given lesson-mode bootstrap, planning-profile tuning, pair constraints, suggestion generation, whole-workspace randomization, finalize, and snapshots are no longer part of the approved near-term plan, when the story ships, then those concepts are removed from the curated app codebase rather than left behind as hidden compatibility paths or dormant abstractions."
  - "Given grouping and seating are separate teacher tasks, when the default planner surfaces render, then they do not leak opposite-axis context by default and they do not teach one global whole-workspace mental model."
  - "Given the current owner-global active-draft invariant conflicts with the approved class-first draft model, when this story ships, then no owner-global single-active-draft contract remains in code or schema."
  - "Given EPIC-24's later stories depend on a clean foundation, when this story is done, then ST-24-02, ST-24-03, and ST-24-04 can build forward without preserving superseded planner contracts, aliases, or legacy behavior."
---

## Context

The current documentation now points clearly toward a class-first, fundamentals-only
Klassrumskartan. The codebase does not yet match that direction. Old solver-first concepts are
still present in live store state, frontend types, API routes, domain models, persistence seams,
and draft lifecycle rules.

This story exists to make the redirection explicit. It is not feature expansion. It is a
remediation gate that removes superseded ideas before later class-first workspace, grouping, and
seating work continues.

## Notes

- This story is the active EPIC-24 prerequisite for `ST-24-02`, `ST-24-03`, and `ST-24-04`.
- No compatibility shims or keep-for-later code paths should remain when the story is done.
- If a concept is not part of the current approved plan, it should not remain in the classroom
  planner codebase as active contract surface.
- Hidden technical debt is still technical debt; “not currently on the screen” is not a valid
  reason to keep superseded planner behavior in the app contract.
- The intent is to preserve genuinely useful fundamentals and reusable normalized concepts, not to
  salvage old solver-era abstractions by renaming them.
