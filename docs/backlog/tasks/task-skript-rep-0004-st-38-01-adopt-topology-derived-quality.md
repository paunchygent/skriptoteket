---
type: task
id: TASK-SKRIPT-REP-0004
title: ST-38-01 Adopt topology-derived quality
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: done
readiness_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User approved immediate implementation on 2026-07-31
closeout_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User directed completion without further ceremony on 2026-07-31
task_kind: repository
acceptance_criteria:
  - Schema-v3 facts and complete generated bindings preserve repository-owned producers while deriving truthful complete and named backend/frontend scopes.
  - Check planning is inspected before only approved named scopes execute; no unscoped aggregate runs.
---

## Context

Skriptoteket has one Python backend, one PNPM frontend workspace, current shared
Docs-as-Code, and a separate historical-only terminal backlog validator. This
task gives the shared routine enough facts to organize those existing quality
commands without redefining repository architecture or product behavior.

## Impact And Escalation

The task changes only repository-governance facts, generated bindings, the
Markdown selection policy required by the routine, a broken pre-commit pytest
argv, its focused tests, and this record. Shared frontend resources remain in
Task 0005. Product, Docker, deployment, database, auth, worker, and observability
surfaces remain unchanged.

## Decision And Assumption Ledger

| ID     | Status | Decision                                                                                                                                                                                                    | Evidence                                  |
| ------ | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| TQ-001 | closed | Model one root PDM project, one backend aggregate, and one frontend path cohort.                                                                                                                            | Retained topology discovery               |
| TQ-002 | closed | Backend typecheck covers `src` and `tests`; runtime plan proof excluded `runner` and `migrations` because they are not clean under the existing mypy contract, while `scripts` remains explicitly excluded. | Backend Explorer and inspected named run  |
| TQ-003 | closed | Backend tests use the existing native-library-aware `test-parallel` producer.                                                                                                                               | Backend Explorer and focused helper test  |
| TQ-004 | closed | Frontend facts name the workspace, root manifest, app manifest, lock derived by the package, and no exceptions.                                                                                             | Frontend parity Explorer                  |
| TQ-005 | closed | Frontend typecheck and tests use `fe-type-check` and `fe-test`; Task 0005 owns absent catalog/resource files and adoption proof.                                                                            | Frontend parity Explorer                  |
| TQ-006 | closed | Complete validators are current docs, shared skills, shared handoff, and binding drift; `git diff --check` is built in.                                                                                     | Validator Explorer                        |
| TQ-007 | closed | The historical validator remains manual and read-only; conditional migration, hazard, shell, product, and operations checks remain outside the complete routine.                                            | Validator Explorer and Task 0003 contract |
| TQ-008 | closed | Execute only the inspected named `backend` and `frontend` scopes.                                                                                                                                           | User approval, 2026-07-31                 |

## Plan

Declare the small routing manifest, regenerate package-owned bindings, align the
installed immutable runtime with the existing dependency and lock, inspect the
complete and named plans, then run only `check backend` and `check frontend`.

## Implementation Steps

1. Add frontend workspace and dependency-manifest facts.
2. Add backend/frontend cohorts, existing producers, the backend aggregate, and complete validators.
3. Restore the required Markdown selection mapping and generated auxiliary bindings.
4. Route targeted pre-commit pytest through `test-parallel` so `-q` reaches pytest.
5. Inspect complete, backend, and frontend plans before execution.
6. Execute only the two approved named checks and focused contract tests.

## Proof

- `pdm run check --plan`, `pdm run check backend --plan`, and
  `pdm run check frontend --plan` must match TQ-001 through TQ-007.
- `pdm run check backend` and `pdm run check frontend` are the only quality
  aggregates authorized here.
- Focused bootstrap/binding and targeted-pytest tests prove facts and argv.
- Docs validation and diff hygiene cover the changed governed surfaces.

## Validation

No unscoped `check`, broad repository suite, product proof, Docker operation, or
historical-validator execution is part of this task.

## Stop Conditions

- A plan replaces a local producer, includes a nonexistent frontend resource,
  routes the historical validator into current gates, or expands beyond the two
  named scopes.
- Facts or generated bindings differ from the installed immutable package.
- Product or operational code would need to change.

## Lessons Learned

The manifest is a workload organizer and quality-control routing table. The
repository topology and existing commands remain authoritative; the manifest
must stay smaller than the system it describes.

## Notes

Discovery is retained under the Task 0004 task root and its origin planning
session. No shared-package version is pinned in this backlog record.

## Readiness

TQ-001 through TQ-008 are closed. The user approved implementation and asked
that this step proceed without additional ceremony.

## Closeout

The package-owned setup aligned the installed runtime and generated the complete
binding block. Complete, backend, and frontend plans were inspected before only
the two named checks ran. Backend mypy is green for `src` and `tests`; frontend
typecheck is green; focused facts, binding, and targeted-pytest tests pass; and
docs, skills, handoff, Markdown/YAML, and diff validation pass.

The named runs also made existing repository debt visible: backend tests report
16 failures and one collection error, while frontend tests report six failures.
Focused Explorer classification proves none is caused by this task. The backend
clusters are an absent generated SPA shell, three pre-existing route annotation
violations, an ignored artifact-coupled test, and a dev-only dependency omitted
from governed setup. The frontend clusters are stale runtime/advisory fixtures,
one stale artifact expectation, and missing help topics. These remain explicit
readiness debt; the manifest is not widened or weakened to conceal them.
