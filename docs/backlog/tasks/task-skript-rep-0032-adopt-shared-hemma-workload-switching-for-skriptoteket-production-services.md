---
type: task
id: TASK-SKRIPT-REP-0032
title: Adopt shared Hemma workload switching for Skriptoteket production services
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-08-28'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: repository
dependencies:
  - Skill Repository TASK-SKILL-05-10-01
acceptance_criteria:
  - Skriptoteket exports importable web and worker WorkloadDeclaration objects and typed owner adapters for exact start, stop, status, and readiness outcomes.
  - A separate Skriptoteket-owned cleanup gate reports exact cleanup outcomes, and only succeeded advances the required gate.
  - The declarations enable Hule TASK-HULE-09-02-26 to prove that recorded running services are restored while initially stopped services remain stopped.
  - Skriptoteket does not duplicate hostwide ordering, state storage, transaction locking, registry composition, target/conflict selection, or Hule-owned orchestration.
backlog_document_profile: contract-derived
---

## Implementation Contract

After a corrected shared provider release, pin its exact immutable revision and
add Skriptoteket-owned `WorkloadDeclaration` exports and typed adapters for
production `web` and `worker`. Declare exact start, stop, status, readiness,
timeout, and terminal-outcome commands. Keep cleanup as a separate required
gate because the shared `WorkloadAdapter` protocol has no cleanup phase. The
exports report product truth to the Hule-owned host composer; they do not own a
closed registry, controller, hostwide order, locks, receipts, target/conflict
selection, or restore policy.

The separate cleanup surface preserves the released idle-safe command truth.
`succeeded` advances the required cleanup gate. `intentionally_idle` remains an
explicit observable outcome for an absent or stopped web container, but it does
not satisfy that required gate.

Hule `TASK-HULE-09-02-26` owns the one closed cross-product registry and
controller, target/conflict selection, shared-engine transaction, and
exact-subset restoration walking skeleton using these released declarations.

## Contract Inputs

- Skill Repository `ST-SKILL-05-10` and released
  `TASK-SKILL-05-10-01` package identity.
- Existing Skriptoteket production web/worker Compose, deploy, worker-health,
  public `/healthz`, and cleanup-unit commands.
- Hule `TASK-HULE-09-02-26` integration coordinator.
- Existing auth-edge distinction: self-health does not certify Hule-owned
  protected API readiness.

## Core Vertical And Performance

Through the real shared package boundary, prove that the importable web and
worker declarations bind exact Skriptoteket services and that their adapters
invoke exact product-owned start, stop, status, and readiness commands. Prove
the separate cleanup gate maps exact command results without treating
`intentionally_idle` as required-gate success.

The adapter performs bounded Compose/status/health calls only. It introduces no
continuous polling, rebuild, database lifecycle, or cleanup scan.

## Validation

- Focused tests assert exact argv, declared service membership, accepted
  terminal outcomes, status/readiness mapping, cleanup
  succeeded/intentionally-idle handling, unknown-service refusal, and
  importability by the Hule-owned host composer.
- Existing web, worker, public health, and cleanup contracts remain green.
- Run `pdm run docs-sync`, `pdm run docs-validate`, affected repository checks,
  and `git diff --check`.
- Engine-level inventory, stop, restore, and exact-subset proof run only through
  the Hule-owned integration packet after the shared provider and all product
  adapters are released.

## Stop Conditions

- The exact shared-package release or immutable pin is unavailable.
- The released provider has a confirmed defect on the required live path.
- The adapter would duplicate transaction storage, locking, hostwide order, or
  Hule-owned registry composition or orchestration.
- Web/worker state or cleanup outcome cannot be classified exactly.
- Protected readiness would be certified from Skriptoteket self-health alone.
- Local proof would require inventing a target/conflict identity or executing
  the Hule-owned transaction.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                              |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| D01 | Skriptoteket owns exact web/worker declaration exports, commands, and readiness outcomes; the shared package owns switching state and restoration. |
| D02 | Hule TASK-HULE-09-02-26 owns the closed cross-product registry, controller, target/conflict selection, and exact-subset restoration proof.         |
| D03 | Cleanup is a separate required gate; succeeded advances it, while intentionally_idle remains observable and does not satisfy it.                   |
| D04 | The adapter never duplicates hostwide order, registry composition, or Hule-owned auth-edge orchestration.                                          |
| D05 | Adoption uses one corrected exact released provider pin; 0.11.24 is inadmissible because its required live inventory path is defective.            |

## Implementation Review

- Timestamp: `2026-08-28T13:22:10+02:00`
- Reviewer: exact independent `ruthless-reviewer`
- Decision: `approved`
- Reviewed scope and authority: the concrete implementation checkpoint over
  `pyproject.toml`, `pdm.lock`, `scripts/hemma_workload.py`, and
  `tests/unit/scripts/test_hemma_workload.py` on contract checkpoint
  `48e2841f7ced1ef78031e30b628c1c402922085e`, including the privilege-boundary
  remediation, under this task's accepted option-A contract and D01-D05.
- Findings: none after remediation.
- Permitted next step: independent `spec-verifier` checkpoint.
- Residual risk and validation not run: no Hemma mutation or engine-level
  transaction/restoration proof was run. Cross-product registry composition,
  target/conflict selection, and exact-subset restoration remain owned by Hule
  `TASK-HULE-09-02-26`. The parent supplied 54 passing affected tests, passing
  scoped Ruff/format, passing targeted mypy, and passing `git diff --check`.
