---
type: pr
id: PR-0049
title: "Refactor: backend SRP split for largest god modules"
status: ready
owners: "agents"
created: 2026-01-21
updated: 2026-01-21
stories:
  - "ST-06-16"
tags: ["backend", "refactor", "srp", "ddd"]
acceptance_criteria:
  - "Each targeted module is split into smaller, cohesive units (generally <=400–500 LOC) with clear single responsibilities."
  - "DDD/Clean boundaries are preserved: domain stays pure, web stays thin, infrastructure implements protocols."
  - "Protocol-first DI remains intact; repositories still avoid committing and UoW owns transactions."
  - "Behavior is preserved (no API or user-facing behavior changes) and tests are updated/added where structure changes."
  - "Module entrypoints and docs are updated to reflect the new structure (imports/exports remain stable or are explicitly updated)."
---

## Problem

Several backend modules have grown into large, multi-responsibility files that are difficult to reason about and test.
This creates review risk, slows iteration, and hides subtle regressions.

## Goal

- Split the largest backend “god modules” into cohesive units that follow SRP and DDD/Clean boundaries.
- Preserve behavior while improving readability, testability, and ownership clarity.
- Prefer clean refactors over minimizing churn.

## Non-goals

- Feature work or behavior changes.
- Refactoring script bank scripts (content, not architecture).
- Changing persistence or domain invariants.

## Implementation plan

### 1) Target inventory (baseline sizes on 2026-01-21)

Prioritize the largest backend modules that mix responsibilities. Exclude script bank scripts.

- `src/skriptoteket/application/editor/completion_handler.py` (~1297 LOC)
- `src/skriptoteket/infrastructure/runner/docker/runner.py` (~702 LOC)
- `src/skriptoteket/protocols/llm.py` (~582 LOC)
- `src/skriptoteket/infrastructure/editor/unified_diff/normalize.py` (~533 LOC)
- `src/skriptoteket/application/editor/chat_stream_orchestrator.py` (~522 LOC)
- `src/skriptoteket/web/api/v1/editor/models.py` (~485 LOC)
- `src/skriptoteket/application/editor/edit_ops_handler.py` (~440 LOC)
- `src/skriptoteket/workers/execution_queue_job_processor.py` (~410 LOC)
- `src/skriptoteket/di/infrastructure.py` (~380 LOC)

### 2) Refactor approach

- Start by mapping responsibilities inside each module (group by concerns like parsing, normalization, routing, IO, logging).
- Extract cohesive submodules into a package adjacent to the original file (e.g., `completion/`, `llm/`, `normalize/`).
- Keep public entrypoints stable where possible; if re-exporting is needed, use thin wrapper modules.
- Keep DI and protocol boundaries explicit; avoid cross-layer dependencies.
- Update tests to import the stable entrypoints or update fixtures if module paths change.

### 3) Acceptance checks

- Each target module reduced below the size budget unless a well-justified exception is recorded.
- No behavior changes (API responses, domain behavior, side effects) beyond internal structure.
- All tests/lint/typecheck remain green.

## Test plan

- `pdm run lint`
- `pdm run typecheck`
- `pdm run test`

## Rollback plan

- Revert the PR to restore the previous module layout.
