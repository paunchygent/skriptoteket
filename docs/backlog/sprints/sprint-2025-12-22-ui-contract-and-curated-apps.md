---
type: sprint
id: SPR-2025-12-22
title: "Sprint 2025-12-22: Tool UI contract v2 foundations"
status: planned
owners: "agents"
created: 2025-12-19
starts: 2025-12-22
ends: 2026-01-05
objective: "Establish the contract + persistence foundations for typed outputs/actions/state, enabling multi-turn tools and a curated apps path."
prd: "PRD-script-hub-v0.2"
epics: ["EPIC-10"]
stories: ["ST-10-01", "ST-10-02", "ST-10-03"]
adrs: ["ADR-0022", "ADR-0023", "ADR-0024", "ADR-0025"]
---

## Objective

Establish the contract + persistence foundations for typed outputs/actions/state, enabling multi-turn tools and a curated apps path.

## Scope (committed stories)

- ST-10-01: Tool UI contract v2 (runner result.json)
- ST-10-02: Tool sessions (state + optimistic concurrency)
- ST-10-03: UI payload normalizer + storage on tool runs

## Out of scope

- Curated apps registry + execution (planned next sprint)
- Editor SPA implementation work (planned next sprint)
- Arbitrary script-provided JS in end-user UI (explicitly not supported)

## Decisions required (ADRs)

- ADR-0022: Tool UI contract v2
- ADR-0024: Tool sessions and UI payload persistence
- ADR-0023: Curated apps registry and execution (review in parallel; implement later)
- ADR-0025: Embedded SPA islands (scope + coexistence + tooling)

## Risks / edge cases

- Payload bloat: enforce strict size budgets and deterministic truncation.
- Contract mismatch: runner/app must be upgraded together; treat mismatches as contract violations.
- Multi-tab races: require `expected_state_rev` for all state-mutating actions.

## Execution plan

1. Merge/accept ADRs for the contract and persistence model.
2. Implement contract v2 parsing + normalization + persistence (unit-tested).
3. Add minimal session state access + optimistic concurrency behavior.

## Demo checklist

- Execute a tool “turn” and show typed outputs rendered (at least one non-HTML output kind).
- Show state persistence across two turns for the same user/tool.
- Show stale `expected_state_rev` being rejected.

## Verification checklist

- `pdm run docs-validate`
- `pdm run test` (or targeted unit tests for the normalizer)

## Notes / follow-ups

- Next sprint: ST-10-04, ST-10-05, ST-10-06 (API endpoints + curated apps registry/execution).
