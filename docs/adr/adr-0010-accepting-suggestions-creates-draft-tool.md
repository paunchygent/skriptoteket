---
type: adr
id: ADR-0010
title: "Accepting a suggestion creates a draft tool entry (no auto-code generation)"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-13
---

## Context

Contributors can propose new scripts/tools. Admins must be able to accept suggestions in a way that is traceable and sets up the implementation/publication work without coupling the product to Git workflows.

## Decision

When an admin **accepts** a suggestion:

- Create a **Draft Tool entry** (e.g., `ToolDraft` / `ToolSpec`) populated from the suggestion metadata (title, description, professions, categories, etc.).
- Link the draft tool back to the originating suggestion and record the decision/audit trail.
- The draft tool is **not runnable** and **not visible** to normal users until it is implemented and published.

Out of scope for v0.1:

- auto-generating repo folders/code or opening PRs automatically

## Consequences

- Clear pipeline: `Suggested → Under review → Accepted (draft created) → Implemented (PR merged) → Published/Depublished`.
- Keeps governance and product state in the app while leaving code changes to normal PR review.
