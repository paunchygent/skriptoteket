---
type: sprint
id: SPR-2026-01-06
title: "Sprint 2026-01-06: Interactive API + curated apps MVP"
status: planned
owners: "agents"
created: 2025-12-19
starts: 2026-01-06
ends: 2026-01-19
objective: "Ship turn-taking APIs and a curated apps MVP using the same typed UI contract and persistence model."
prd: "PRD-script-hub-v0.2"
epics: ["EPIC-10"]
stories: ["ST-10-04", "ST-10-05", "ST-10-06"]
adrs: ["ADR-0022", "ADR-0023", "ADR-0024"]
---

## Objective

Ship the minimal API surface for multi-turn interactivity and a curated apps MVP that appears in Katalog, executes, and
persists runs using the same UI contract and UI payload normalizer.

## Scope (committed stories)

- ST-10-04: Interactive tool API endpoints (start_action + read APIs)
- ST-10-05: Curated apps registry and catalog integration
- ST-10-06: Curated app execution + persisted runs

## Out of scope

- SPA island implementation work (planned later)
- Additional output kinds beyond the initial allowlist
- Notebook-style long-running compute sessions

## Decisions required (ADRs)

- ADR-0023: Curated apps registry and execution
- ADR-0024: Tool sessions and UI payload persistence

## Risks / edge cases

- Authorization: curated apps must be role-gated and auditable.
- Contract drift: ensure runner tools and curated apps share a single normalization path.
- Artifact handling: ensure the same path safety rules apply to both source kinds.

## Demo checklist

- Start an action via API and show a new run with stored `ui_payload`.
- List curated apps in Katalog and run one (even a trivial “hello” app).
- Show artifacts listing/download for at least one run.

## Verification checklist

- `pdm run docs-validate`
- `pdm run test` (or targeted unit tests for API + curated app executor seams)
