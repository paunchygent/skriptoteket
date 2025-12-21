---
type: reference
id: REF-sprint-planning-workflow
title: "Sprint planning workflow (PRD → epic → story)"
status: active
owners: "agents"
created: 2025-12-19
topic: "sprint-planning"
---

This repo uses a Docs-as-Code contract (`pdm run docs-validate`) to keep planning artifacts consistent.
This document describes the expected workflow for planning and executing a sprint, from PRD down to story level.

## Mental model (traceability chain)

- **PRD** answers *what* and *why* (product outcome, goals, non-goals, requirements).
- **ADR** answers *how* for major decisions (architecture, contracts, security boundaries).
- **Epic** answers *what outcome will we deliver* (measurable result + scope boundaries).
- **Story** answers *what change will we ship next* (testable acceptance criteria, implementable slice).
- **Sprint plan** answers *what we will do this iteration* (selected stories + demo/test plan + decision log).

Recommended traceability:

- PRD feature → one or more EPICs
- Each EPIC → a set of ST stories
- Stories reference ADRs when they depend on a decision/contract

## Status conventions (docs contract)

- **PRD**: `draft` → `active` → `superseded`
- **ADR**: `proposed` → `accepted` (or `superseded` / `deprecated`)
- **Epic**: `proposed` → `active` → `done` (or `dropped`)
- **Story**: `ready` → `in_progress` → `done` (or `blocked`)

## Planning steps (PRD → stories)

### 1) Start with PRD scope

1. Identify which PRD version the sprint contributes to (or create a new PRD if this is a new product slice).
2. Ensure the PRD has:
   - clear Goals / Non-goals
   - user roles impacted
   - success metrics (even if rough)
3. If the PRD introduces new capabilities/risks, open ADRs early (next step).

### 2) Write ADRs for “decision surfaces”

Create ADRs when you are deciding things that will be expensive to change later, especially:

- Contracts (runner ↔ app, tool UI contracts, API payload shapes)
- Security boundaries (what is trusted/untrusted; sandboxing assumptions)
- Persistence model changes (new tables, state semantics)
- “Two-paradigm” choices (HTMX vs embedded SPA boundaries)

ADR status is `proposed` during discussion and changed to `accepted` once a reviewer approves it.

### 3) Create or update the epic

Create a new epic when the work has a distinct outcome and spans multiple stories.
Re-open an epic only if the new work is clearly the same outcome area (design harmonization, execution, identity, etc.).

Epic checklist:

- Outcome is measurable (“users can X”, “system supports Y contract v2”).
- Scope describes what is in/out.
- Risks and dependencies are listed (include ADR ids).

### 4) Break into stories (vertical slices)

Each story must be independently shippable, with testable acceptance criteria:

- Acceptance criteria: *Given/When/Then* phrased in observable behavior.
- Dependencies: list required ADRs / prerequisite stories.
- UI impact / data impact: include if relevant (optional keys supported by the docs contract).
- Keep stories small enough to complete in one sprint; split “plumbing” vs “UX” if needed.

Recommended “Definition of Ready” for a story:

- Status is `ready`
- Acceptance criteria are complete and testable
- Risks/edge cases are called out
- Implementation approach is not blocked by an undecided ADR

## Sprint plan (iteration-level coordination)

Use a sprint plan doc (`type: sprint`) to snapshot the intent for the iteration:

- objective (what success looks like by sprint end)
- included stories (IDs + links)
- decisions required (ADRs to approve)
- demo plan and test/verification checklist
- explicit “not in scope”

Use `docs/templates/template-sprint-plan.md` as the starting point and save under `docs/backlog/sprints/`.

## During the sprint

- Change story status to `in_progress` when started.
- Keep the sprint plan updated if scope changes (swap stories, add dependencies).
- When an ADR is decided, flip it to `accepted` and update dependent stories if needed.

## Sprint close

- Ensure each shipped story is `done` and has met acceptance criteria.
- Update epic status if the epic outcome is now complete.
- Capture any follow-ups as new `ready` or `blocked` stories (do not keep hidden TODOs).
- If the sprint introduced a new operational concern, add/update a runbook.

## Releases (REQUIRED when shipping a version)

When a PRD milestone is ready to ship (e.g. v0.1), cut a release as an explicit Docs-as-Code artifact.

### Release notes

- Create a release notes doc under `docs/releases/` using `docs/templates/template-release-notes.md`.
- Status progression:
  - `draft`: planned / preparing the release
  - `published`: release shipped (set `released: YYYY-MM-DD`)
  - `superseded`: a later release replaces these notes (optional, e.g. hotfix rollups)
- Release notes MUST link to the PRD(s) and key ADR(s) that define scope and major decisions.

### Minimum content for a release

- Summary + highlights (user-visible value)
- Compatibility/upgrade notes (DB migrations, config/env changes, operational concerns)
- Known issues / limitations (explicitly documented)

### Repo hygiene (recommended)

- Tag the release in git (e.g. `v0.1.0`) and align the release notes `version` accordingly.
- Follow the current UI paradigm ADRs (currently: full SPA per ADR-0027).
