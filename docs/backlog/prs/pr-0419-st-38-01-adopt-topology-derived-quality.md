---
type: pr
id: PR-0419
title: "ST-38-01 Adopt topology-derived quality"
status: blocked
owners: "agents"
created: 2026-07-31
updated: 2026-07-31
stories: ["ST-38-01"]
dependencies: ["PR-0418"]
tags: ["repository-governance", "quality"]
acceptance_criteria:
  - "Schema-v3 facts and complete generated bindings preserve repository-owned producers while deriving truthful complete and named backend/frontend scopes."
  - "Check planning is inspected before only approved named scopes execute; no unscoped aggregate runs."
---

## Problem

Skriptoteket has local quality commands but no common facts, complete routine
aggregate, or topology-derived named scopes.

## TASK-SKRIPT-REP-0004 admission ledger

This PR is a non-authorizing planning envelope and remains `blocked` until the
parent closes every gate below with authority-backed evidence. Implementers may
not infer a missing value, widen the tracked write set, replace a local producer,
or treat this record as permission to run quality commands.

| ID | Closure gate | Required closure evidence |
| --- | --- | --- |
| SKR-REP-0003-01 | Complete generated binding set | At this slice's execution start, the currently approved immutable `repository-governance` release is selected; its consumer dependency, lock version, lock `ref`, lock `revision`, and installed version match exactly and are recorded in retained execution evidence with one generated binding block containing exactly `setup`, `new-worktree`, `format`, `lint`, `typecheck`, `test`, `check`, `new-doc`, `new-epic`, `new-story`, `new-task`, `new-review`, `docs-sync`, `docs-validate`, `format-md`, `check-md`, `format-md-all`, `check-md-all`, plus auxiliary `run-hemma` and `staleness-audit`. Generation is package-owned and atomic; no hand-authored partial block, alias, wrapper, fallback, second facts home, or cutover-wide package freeze is admitted. |
| SKR-REP-0003-02 | Schema-v3 facts home | One root TOML facts home is present with schema `3`, repository `"skriptoteket"`, typed owner `service = ["skriptoteket"]`, and root setup groups exactly `["default", "monorepo-tools"]`. Its quality declaration uses schema-v3 `cohorts`, `producers`, `aggregates`, complete `validators`, and diagnostic producer references; no serialized schema-v2 component/scope matrix or compatibility parser is admitted. |
| SKR-REP-0003-03 | Producer inventory | A frozen inventory names every repository-owned producer by exact intent, project, command/arguments, and diagnostic ownership, including backend, frontend, Markdown, format/lint, typecheck, test, and complete-validator producers that exist in the local checkout. Each producer is mapped to its declared project and intent; missing, duplicate, mismatched, or package-invented producers fail admission. |
| SKR-REP-0003-04 | Cohort and aggregate inventories | A topology ledger names every schema-v3 cohort (kind, root/path, producer mapping, and exclusions) and every aggregate (name and exact member set), derived from Git-tracked paths rather than the raw filesystem. It records active, absent, and tracked-but-empty component behavior and rejects missing roots, untracked/empty declarations, invalid membership, and scope-name collisions. |
| SKR-REP-0003-05 | Named scope ledger | The parent freezes the accepted named backend/frontend (and any other explicitly approved) scopes with exact names, topology-derived paths, typecheck/test narrowing, producer/project assignments, and exact argv. Complete defaults remain the ordered union of all derived selections; named scopes narrow only typecheck/test, while changed-set lint, complete validators, and `git diff --check` remain complete. |
| SKR-REP-0003-06 | Local behavior preservation | A file- and surface-level preservation list covers bootstrap, database/migrations, native libraries, observability, Docker/deploy, auth/Gateway, workers, product commands, environment loading, and lower-level local producers. Positive focused proof shows those producers and product commands remain unchanged; no central replacement or retirement is admitted in this slice. |
| SKR-REP-0003-07 | Plan visibility and execution boundary | A retained `pdm run check --plan` result is reconciled against the frozen facts, producer/cohort/aggregate inventories, and named-scope ledger before execution. Only the accepted named commands and exact argv may run after review; no unscoped aggregate execution, broad repository suite, or inferred scope is permitted. |

The parent owns all ledger closure, authority decisions, generated surfaces,
shared writes, and integration. Any missing or conflicting fact returns to
planning or the user; it is not selected during implementation.

## Implementation plan

After all admission rows close, inventory tracked backend, frontend, tests,
producers, marker exclusions, and diagnostic ownership. Freeze the exact
schema-v3 facts, producer/cohort/aggregate inventories, and named-scope ledger;
preserve local producers and product behavior; verify the complete generated
binding set; inspect `check --plan`; and prove only the accepted named scopes.
This PR remains blocked until that exact ledger and its prerequisite review
evidence close.

## Test plan

Focused binding/facts/schema-v3 drift tests; producer/cohort/aggregate inventory
and topology derivation tests; complete-plan inspection; positive local-producer
and product-command preservation checks; approved named backend/frontend
commands; docs validation; and diff check. No unscoped aggregate execution.

## Rollback plan

Restore the prior facts/binding bytes and producer routing; do not add aliases.

## Stop conditions

- Any binding, package/lock identity, facts-home, producer, cohort, aggregate,
  validator, diagnostic, or named-scope row is missing, ambiguous, or differs
  from its authority-backed ledger.
- Topology derivation reads untracked filesystem state, accepts schema-v2
  serialized selections, or silently drops absent/empty tracked components.
- A producer, product command, bootstrap/database/migration/native-library,
  observability, Docker/deploy, auth/Gateway, worker, environment, or lower-level
  local surface would be replaced or changed by this slice.
- `check --plan` is unavailable or not reconciled before execution, or any
  unscoped aggregate execution, broad suite, inferred scope, alias, wrapper,
  fallback, or compatibility branch is requested.
- A prerequisite review or parent-owned closure is missing; this PR remains a
  blocked non-authorizing envelope and cannot transition itself to `ready`.
