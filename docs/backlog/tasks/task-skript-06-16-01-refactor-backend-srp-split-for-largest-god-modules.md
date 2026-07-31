---
type: task
id: TASK-SKRIPT-06-16-01
title: 'Refactor: backend SRP split for largest god modules'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-06-16
task_kind: story
acceptance_criteria:
- Each targeted module is split into smaller, cohesive units (generally <=400–500
  LOC) with clear single responsibilities.
- 'DDD/Clean boundaries are preserved: domain stays pure, web stays thin, infrastructure
  implements protocols.'
- Protocol-first DI remains intact; repositories still avoid committing and UoW owns
  transactions.
- Behavior is preserved (no API or user-facing behavior changes) and tests are updated/added
  where structure changes.
- Module entrypoints and docs are updated to reflect the new structure (imports/exports
  remain stable or are explicitly updated).
---

## Context

Source: `docs/backlog/prs/pr-0049-backend-srp-refactor-god-modules.md`. Refactor: backend SRP split for largest god modules.

Several backend modules have grown into large, multi-responsibility files that are difficult to reason about and test. This creates review risk, slows iteration, and hides subtle regressions. - Split the largest backend “god modules” into cohesive units that follow SRP and DDD/Clean boundaries. - Preserve behavior while improving readability, testability, and ownership clarity. - Prefer clean refactors over minimizing churn. - Feature work or behavior changes. - Refactoring script bank scripts (content, not architecture). - Changing persistence or domain invariants. Prioritize the largest backend modules that mix responsibilities. Exclude script bank scripts. - `src/skriptoteket/application/

## Decision And Assumption Ledger

| ID | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | --- | --- | --- | --- | --- |
| MIG-TASK-SKRIPT-06-16-01 | migration | closed | How is source meaning preserved? | Preserve the source task contract, current relationships, and status while changing identity only. | ST-SKILL-08-06; TASK-SKRIPT-REP-0003 |

## Story Contract Slice

The task preserves the source implementation slice under its current story parent.

## Contract Inputs

- Source task/PR and audit-approved migration authority.
- Current story or repository relationship in candidate frontmatter.

## Plan

Execute only the bounded plan represented by the source record; do not add scope during migration.

## Implementation Steps

1. Preserve the source implementation or proof sequence.
2. Verify current relationships and focused evidence at task closeout.

## Proof

The source proof obligations are retained as historical evidence below; no execution proof is asserted by this candidate.

## Validation

Run the task-selected focused gates and repository docs validation after parent integration.

## Stop Conditions

Stop for missing authority, unresolved identity/relationship, terminal ancestry, or scope expansion.

## Lessons Learned

The source material is retained verbatim below for migration fidelity.

## Notes

### Source evidence

### Problem

Several backend modules have grown into large, multi-responsibility files that are difficult to reason about and test.
This creates review risk, slows iteration, and hides subtle regressions.

### Goal

- Split the largest backend “god modules” into cohesive units that follow SRP and DDD/Clean boundaries.
- Preserve behavior while improving readability, testability, and ownership clarity.
- Prefer clean refactors over minimizing churn.

### Non-goals

- Feature work or behavior changes.
- Refactoring script bank scripts (content, not architecture).
- Changing persistence or domain invariants.

### Implementation plan

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

### 2) Prioritized order + dependency mapping

### Suggested order (least churn + dependency-aware)

1) `src/skriptoteket/protocols/llm.py`
   - Foundation for editor + infra LLM usage; stabilize via re-exports to minimize call-site churn.
2) `src/skriptoteket/application/editor/completion_handler.py`
   - Largest module; depends on LLM protocols and provider wiring.
3) `src/skriptoteket/application/editor/chat_stream_orchestrator.py`
   - Shares LLM protocol surface; refactor after protocol split.
4) `src/skriptoteket/infrastructure/editor/unified_diff/normalize.py`
   - Used by edit-ops preview; small, localized split reduces risk.
5) `src/skriptoteket/application/editor/edit_ops_handler.py`
   - Depends on unified diff helpers + LLM protocols.
6) `src/skriptoteket/web/api/v1/editor/models.py`
   - DTOs rely on LLM protocol types; split after protocol stabilization.
7) `src/skriptoteket/infrastructure/runner/docker/runner.py`
   - Infra-only refactor; coordinate with runner protocol boundaries.
8) `src/skriptoteket/workers/execution_queue_job_processor.py`
   - Depends on runner protocols; refactor after runner package split.
9) `src/skriptoteket/di/infrastructure.py`
   - Final wiring pass after module paths settle.

### Dependency map (A -> B means B depends on A)

- `protocols/llm` -> `application/editor/completion_handler`, `application/editor/chat_stream_orchestrator`,
  `application/editor/edit_ops_handler`, `web/api/v1/editor/models`,
  `infrastructure/editor/unified_diff/normalize`, `infrastructure/llm/*`, `di/llm`.
- `infrastructure/editor/unified_diff/normalize` -> `application/editor/edit_ops_preview_handler`.
- `application/editor/completion_handler` -> `web/api/v1/editor/completions`.
- `application/editor/chat_stream_orchestrator` -> `web/api/v1/editor/chat`.
- `infrastructure/runner/docker/runner` -> `di/infrastructure`, `protocols/runner` integration, worker wiring.
- `workers/execution_queue_job_processor` -> `protocols/runner` + DI-provided runner.
- `di/infrastructure` -> all refactored module entrypoints (final wiring).

### 3) Refactor approach

- Start by mapping responsibilities inside each module (group by concerns like parsing, normalization, routing, IO, logging).
- Extract cohesive submodules into a package adjacent to the original file (e.g., `completion/`, `llm/`, `normalize/`).
- Keep public entrypoints stable where possible; if re-exporting is needed, use thin wrapper modules.
- Keep DI and protocol boundaries explicit; avoid cross-layer dependencies.
- Update tests to import the stable entrypoints or update fixtures if module paths change.

### Checklist (live)

- [x] Split `src/skriptoteket/protocols/llm.py` into `src/skriptoteket/protocols/llm/` package and delete the old module (no shim; package `__init__` re-exports).
- [x] Refactor `src/skriptoteket/application/editor/completion_handler.py` into `application/editor/completion/` (attempts/normalization/telemetry/capture/flow) with a thin handler entrypoint.
- [x] Extract chat stream capture + context-window error helpers into `application/editor/chat_stream/` and slim `chat_stream_orchestrator.py`.
- [x] Extract unified-diff line normalization steps into `infrastructure/editor/unified_diff/normalize_steps.py`.
- [x] Refactor `src/skriptoteket/application/editor/edit_ops_handler.py` into cohesive submodules.
- [x] Split `src/skriptoteket/web/api/v1/editor/models.py` into request/response/common DTO modules.
- [x] Split `src/skriptoteket/infrastructure/runner/docker/runner.py` into request/result/container helper modules with a thin orchestrator.
- [x] Refactor `src/skriptoteket/workers/execution_queue_job_processor.py` into orchestration/state/telemetry helpers.
- [x] Split `src/skriptoteket/di/infrastructure.py` into per-domain wiring modules.
- [ ] Update tests/imports and run the full quality gate set.

**Decisions recorded**

- No legacy shim file for `protocols.llm`; the import path remains stable via the package `__init__` re-exports.

### 4) Acceptance checks

- Each target module reduced below the size budget unless a well-justified exception is recorded.
- No behavior changes (API responses, domain behavior, side effects) beyond internal structure.
- All tests/lint/typecheck remain green.

### Test plan

- `pdm run lint`
- `pdm run typecheck`
- `pdm run test`

### Rollback plan

- Revert the PR to restore the previous module layout.

## Plan Document Review

No specialist approval is asserted; parent review remains required.

## Implementation Review

No closeout evidence is asserted in this candidate.
