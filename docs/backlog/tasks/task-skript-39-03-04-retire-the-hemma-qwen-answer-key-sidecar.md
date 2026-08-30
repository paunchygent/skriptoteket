---
type: task
id: TASK-SKRIPT-39-03-04
title: Retire the Hemma Qwen answer-key sidecar
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-08-30'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- The authenticated answer-key workflow remains operational through the Luna and GLM
  remote-provider line while the Hemma Qwen answer-key sidecar and its obsolete configuration
  and operational surfaces are absent
story: ST-SKRIPT-39-03
backlog_document_profile: contract-derived
---

## Implementation Contract

After the authenticated lane uses the completed remote provider line and the
Sir exam lane has retired, remove the Hemma Qwen answer-key sidecar.

- Remove the sidecar from Hemma deployment configuration and runtime.
- Remove its exam-specific settings, secrets, health checks, operational
  commands, and documentation wherever they no longer serve another consumer.
- Preserve the Luna-primary, GLM-failover, daily-token-lease behavior completed
  by `ST-SKRIPT-39-02`.
- Retain no disabled Qwen fallback or compatibility configuration.

## Contract Inputs

- Completed Task 03 and confirmation that no active consumer uses the Qwen
  answer-key sidecar.
- `ST-SKRIPT-39-02` remote-provider and lease contract.
- Current Hemma workload declarations, secrets, service health, operations,
  and documentation for the sidecar.

## Core Vertical And Performance

The authenticated Exam Converter completes its answer-key workflow through the
remote provider line while no Qwen answer-key service is deployed or
referenced. Removing the unused sidecar releases its host workload without
changing the remote provider request path.

## Validation

- Hemma runs without the Qwen answer-key service or obsolete configuration.
- The authenticated answer-key workflow remains functional after removal.
- Host, repository, configuration, and documentation inspection confirm that
  no active consumer references the retired sidecar.
- Affected deployment and docs gates pass in each owning repository.

## Stop Conditions

- Do not begin before the last exam consumer has moved.
- Do not remove a Qwen service or setting proven to serve another capability.
- Stop if removal would change the accepted Luna/GLM provider or lease
  behavior.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| T1 | The Qwen answer-key sidecar retires only after its last exam consumer moves. |
| T2 | Luna-primary, GLM-failover, and the shared daily token lease remain unchanged. |
| T3 | Sidecar service, obsolete configuration, secrets, health checks, operations, and docs retire without a dormant fallback. |
