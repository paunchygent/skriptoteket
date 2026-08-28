---
type: task
id: TASK-SKRIPT-REP-0032
title: Adopt shared Hemma workload switching for Skriptoteket production services
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-08-28'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: repository
dependencies:
- Skill Repository TASK-SKILL-05-10-01
acceptance_criteria:
- Skriptoteket web and worker declare exact start, stop, status, readiness, cleanup,
  and terminal-outcome adapters for the shared workload-switch package.
- A recorded running web or worker service is restored after a conflicting workload
  stops or fails, while an intentionally stopped service remains stopped.
- Skriptoteket does not duplicate hostwide ordering, state storage, transaction locking,
  or Hule-owned orchestration.
backlog_document_profile: contract-derived
---

## Implementation Contract

After the shared provider release, pin its exact immutable revision and add the
Skriptoteket-owned declaration/adapter for production `web` and `worker`.
Declare exact start, stop, status, readiness, cleanup, timeout, and terminal
outcome commands. The adapter reports product truth to the shared transaction;
it does not own hostwide order, locks, receipts, conflict selection, or restore
policy.

When the shared transaction records a running Skriptoteket service before a
conflicting workload stops it, restoration starts and verifies that service.
A service recorded as stopped remains stopped. Cleanup timers report success or
explicit intentional idle and never turn an intentionally stopped product into
an unexplained failure.

## Contract Inputs

- Skill Repository `ST-SKILL-05-10` and released
  `TASK-SKILL-05-10-01` package identity.
- Existing Skriptoteket production web/worker Compose, deploy, worker-health,
  public `/healthz`, and cleanup-unit commands.
- Hule `TASK-HULE-09-02-26` integration coordinator.
- Existing auth-edge distinction: self-health does not certify Hule-owned
  protected API readiness.

## Core Vertical And Performance

Through the real shared package adapter boundary, inventory running web/worker
state, stop only the declared selected conflicts, then restore and verify only
the recorded services. Prove the intentionally-stopped case without starting
either service.

The adapter performs bounded Compose/status/health calls only. It introduces no
continuous polling, rebuild, database lifecycle, or cleanup scan.

## Validation

- Focused adapter tests assert exact argv, declared service membership,
  accepted terminal outcomes, cleanup success/intentional-idle handling,
  unknown-service refusal, and exact-subset restoration.
- Existing web, worker, public health, and cleanup contracts remain green.
- Run `pdm run docs-sync`, `pdm run docs-validate`, affected repository checks,
  and `git diff --check`.
- Real Hemma switching is run only through the Hule-owned integration packet
  after the shared provider and all product adapters are released.

## Stop Conditions

- The exact shared-package release or immutable pin is unavailable.
- The adapter would duplicate transaction storage, locking, hostwide order, or
  Hule-owned orchestration.
- Web/worker state or cleanup outcome cannot be classified exactly.
- Protected readiness would be certified from Skriptoteket self-health alone.
- Restoration would start a service not recorded as running before displacement.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D01 | Skriptoteket owns only exact web/worker commands and readiness outcomes; the shared package owns switching state and restoration. |
| D02 | A recorded running service is restored and verified; an initially stopped service remains stopped. |
| D03 | Cleanup is an explicit success or intentionally-idle outcome, not a reason to infer product failure. |
| D04 | The adapter never duplicates hostwide order or Hule-owned auth-edge orchestration. |
| D05 | Adoption uses one exact released provider pin. |
