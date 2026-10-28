---
type: task
id: TASK-SKRIPT-REP-0052
title: The runner and web images install their locked dependencies again
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-28'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-28'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Light route without review (D2). Root cause: pdm 2.26.2 accepts unearth>=0.17.5 unbounded and unearth 0.19 moved PyPIClient onto httpx2, so the locked install raised TypeError. 6ab2619cb installs pdm[locked]==2.26.2 in the web builder, web production and runner stages; the scratch build of web and runner passed on Hemma 2026-10-28.'
task_kind: repository
acceptance_criteria:
  - docker compose -f compose.hemma-dev.yaml --profile build-only build web runner completes on Hemma from current main
  - The PDM install inside the images no longer fails with the PDMPyPIClient TypeError
backlog_document_profile: contract-derived
---

## Implementation Contract

The Hemma staging build of `web` and `runner` fails at `pdm install --frozen-lockfile --prod --no-editable --no-self` (`Dockerfile.runner:62`, `Dockerfile:104`). PDM 2.26.2, pinned at `Dockerfile.runner:57` and `Dockerfile:99`, crashes while creating its PyPI client: `TypeError: super(type, obj): obj (instance of PDMPyPIClient) is not an instance or subtype of type (Client)` in `httpx/_client.py`. The install layer reruns because commit 9207a9132 changed `pdm.lock`. Production (50a7b84e3) was built before that change. Make the image install work again with a pinned, reproducible PDM toolchain, and change nothing else.

## Contract Inputs

- Build log on Hemma: `~/logs/stg-runner-build-20261028.log`; `Dockerfile`, `Dockerfile.runner`, `pdm.lock`, `compose.hemma-dev.yaml`.

## Core Vertical And Performance

One image build: pip installs the pinned PDM toolchain, then PDM installs the locked production dependencies. Build time stays as it is.

## Validation

- Find the root cause first and record it; confirm the failure on the current Dockerfile before changing it.
- `docker compose -f compose.hemma-dev.yaml -p <scratch project> --profile build-only build web runner` passes from the task worktree with `DOCKER_HOST=unix:///run/user/1000/docker.sock`.

## Stop Conditions

- The fix needs a change to `pdm.lock` content or to an application dependency version. Report it instead.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                            |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Pin the image toolchain so the locked install succeeds (for example PDM together with the dependency that breaks it); every image that installs PDM gets the same pin.           |
| D2  | Light route: one junior, root cause recorded, the two-image build as proof, no review. Orchestrator decision 2026-10-28; it blocks staging walks and the next production deploy. |
