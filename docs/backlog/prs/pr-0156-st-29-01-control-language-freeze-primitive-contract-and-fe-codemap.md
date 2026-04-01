---
type: pr
id: PR-0156
title: "ST-29-01: control-language freeze, primitive contract, and frontend codemap"
status: done
owners: "agents"
created: 2026-03-28
updated: 2026-04-01
stories:
  - "ST-29-01"
tags: ["frontend", "docs", "design-system", "klassrumskartan", "editor"]
dependencies:
  - "EPIC-29"
acceptance_criteria:
  - "Given ST-29-01 now has a locked control-language v1, when implementation planning starts, then the story exposes one explicit PR-sized sequence instead of an implied redesign lane."
  - "Given a frontend designer or implementer needs to understand the design system, when they read the new codemap, then they can locate the governing docs, token pipeline, primitive files, icon assets, editor examples, planner examples, and current structural gaps from one canonical reference."
  - "Given repo-shared planning/docs skills are consulted from this repository, when they are used after this slice, then they do not direct agents to dead paths such as `.agents/session/handoff.md` or missing `run-local-pdm` wrappers."
---

## Problem

`ST-29-01` now has a stable vocabulary, but the implementation pathway is still too implicit. The
story needs one explicit slice plan, one canonical frontend codemap, and one cleanup pass on the
shared skills that were still pointing this repo at non-existent docs paths and command wrappers.

## Goal

Make the first implementation lane for `ST-29-01` concrete before any UI code changes begin:

- publish one frontend design-system codemap for the current SPA
- define the exact PR-sized sequence for the primitive overhaul
- wire the story and docs index to those artifacts
- remove stale shared-skill path guidance that causes docs lookup drift

## Non-goals

- Implementing new Vue primitives.
- Changing planner or editor UI behavior.
- Moving primitives into a new package.
- Finalizing the visual design of the symbol set.

## Implementation plan

1. Publish the codemap.
   - Add one reference doc that maps the full frontend design-system surface:
     - docs-as-code governance
     - stack + workspace entrypoints
     - token pipeline
     - icon assets
     - shared UI primitives
     - dense tool examples in the editor
     - dense workspace examples in Klassrumskartan
     - current structural gap: no dedicated `frontend/packages/huleedu-ui` package yet

2. Freeze the implementation lane.
   - Add three PR-sized backlog docs for `ST-29-01`.
   - Keep the sequence explicit:
     - docs/rules/codemap foundation
     - shared primitive implementation
     - first proving-ground adoption in `Sittplatser`

3. Repair stale shared skill guidance.
   - Update the shared docs/planning skill text so it defers to the local repository’s
     `AGENTS.md`, `docs/index.md`, and actual command set instead of assuming HuleEdu-specific paths
     that do not exist here.

4. Wire the docs together.
   - Update `ST-29-01` references.
   - Update `docs/index.md`.

## PR-sized execution checklist

- [ ] Add `REF-frontend-design-system-codemap-2026-03-28`
- [ ] Add `PR-0156`, `PR-0157`, and `PR-0158`
- [ ] Update `ST-29-01` with the explicit execution path
- [ ] Update `docs/index.md`
- [ ] Patch stale path guidance in the shared docs/planning skills
- [ ] Run docs validation

## Test plan

- `pdm run docs-validate`

## Rollback plan

- Revert the new reference and PR docs together if the slice decomposition proves wrong.
- Keep `REF-shared-tool-control-language-v1` intact so the vocabulary work survives even if the
  execution plan is re-cut.
