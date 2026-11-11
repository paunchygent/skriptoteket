---
type: task
id: TASK-SKRIPT-REP-0070
title: The Hemma staging web service runs under init so its healthcheck children are reaped
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-11-11'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer 95ad3eae-f186-4cd1-9b7a-86162253ac05
  decided_at: '2026-11-11T14:57:18+00:00'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: TASK-SKRIPT-REP-0070#closeout
task_kind: repository
acceptance_criteria:
  - '`init: true` is set on the `web` service in `compose.hemma-dev.yaml`.'
  - '`docker compose -f compose.hemma-dev.yaml config` shows `init: true` for `web` and no other change.'
  - 'After the skriptoteket-dev staging stack is recreated on Hemma, the `web` container reports `HostConfig.Init` true and has no `<defunct>` child after a period of at least two healthcheck intervals.'
backlog_document_profile: contract-derived
---

## Implementation Contract

Add `init: true` to the `web` service block, and change nothing else. `db` is excluded.

## Contract Inputs

On 11 Nov 2026 Hemma had 56 `[curl] <defunct>` zombie processes. Each was a
healthcheck `curl` left unreaped by a staging container's PID 1, and none of
those containers set `HostConfig.Init` (evidence: skill-repository retained
root `01a1cb01-9638-7245-b286-37175a5a9e1e`). Compose `init: true` maps to the
Docker Engine `HostConfig.Init`, which runs Docker's built-in init as PID 1 to
forward signals and reap child processes (docker/compose `pkg/compose/create.go`,
fetched through ctx7 on 11 Nov 2026).
In skriptoteket-dev, the `web` container (`pdm run serve`) had 7 zombies.

## Core Vertical And Performance

## Validation

- `docker compose -f compose.hemma-dev.yaml config` before and after.
- On Hemma after the recreate: `docker inspect` Init for `web`, plus a `ps` count of its `<defunct>` children.

## Stop Conditions

- Stop if the `web` image or entrypoint already runs its own init.

## Decided Contract Terms

| ID  | Decided contract term                                                                                     |
| --- | --------------------------------------------------------------------------------------------------------- |
| D1  | The scope is the staging `web` service, which has a curl healthcheck (user, 11 Nov 2026).                 |
| D2  | After merge, skriptoteket-dev staging is recreated through `pdm run hemma-dev start` (user, 11 Nov 2026). |

## Closeout

- Outcome: `init: true` is set on the services the acceptance criteria list; reviewed commit `ae6f0af7e` was approved with no findings.
- Review: ruthless-reviewer 95ad3eae-f186-4cd1-9b7a-86162253ac05 approved on 2026-11-11T14:57:18+00:00. Record, in the skill-repository primary checkout: `.orchestration/context/sessions/01a1cb01-9638-7245-b286-37175a5a9e1e/evidence/review/init-review.md`.
- Runtime proof after staging recreate: see below.
