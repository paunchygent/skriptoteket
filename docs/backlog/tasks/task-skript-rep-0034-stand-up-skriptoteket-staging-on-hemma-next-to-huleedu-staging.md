---
type: task
id: TASK-SKRIPT-REP-0034
title: Stand up Skriptoteket staging on Hemma next to HuleEdu staging
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-09-28'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - A skriptoteket-dev compose project on Hemma's rootless daemon runs its own Postgres, web, worker, and runner image; web answers as skriptoteket-web on huleedu-dev_hule-network and trusts the HuleEdu staging identity key
  - A Hemma user Vite unit serves the Skriptoteket frontend on 127.0.0.1:5173, the Mac tunnel forwards 127.0.0.1:15173 to it, and the proof-subject import gives the skriptoteket-proof accounts their roles
  - In the in-app browser at http://127.0.0.1:15173 a proof contributor signs in through HuleEdu staging, returns to /auth/callback, runs one script in the editor sandbox, and sees its result and a failure toast
  - Skriptoteket pdm hemma-dev build, start, status, stop, and reset commands and a staging runbook exist, status reports web, worker, database, and frontend healthy, and the skill-repository Skriptoteket references point to them
dependencies:
  - TASK-HULE-REP-0087
backlog_document_profile: contract-derived
---

## Implementation Contract

Stand up a Skriptoteket staging environment on Hemma next to HuleEdu staging,
reached from the Mac through the shared tunnel, for the per-task Hemma walk.

- Hemma checkout `/home/paunchygent/apps/skriptoteket-dev`, updated only by
  `git fetch origin main` and `git merge --ff-only origin/main`. The walk
  proves `main` after merge and push; a failed walk is fixed forward.
- A separate compose project `skriptoteket-dev` on the rootless daemon
  (`unix:///run/user/1000/docker.sock`) with its own Postgres, `web`,
  `worker`, and the runner image built into that daemon's image store.
- `web` joins `huleedu-dev_hule-network` under alias `skriptoteket-web`, so the
  HuleEdu staging Gateway route `/api` to `http://skriptoteket-web:8000`
  reaches it. `web` trusts the HuleEdu staging internal identity public key
  through `HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH`, key id, issuer, and
  audience settings, with the staging key directory mounted read-only.
- `web` and `worker` run as container root, mount the rootless socket, and set
  `DOCKER_HOST` to it; the per-run runner keeps its existing limits.
- A Hemma user systemd unit runs the Skriptoteket Vite dev server on
  `127.0.0.1:5173`, proxying `/api` to the HuleEdu staging Gateway, like
  `huleedu-vite-dev.service`.
- Add the forward `127.0.0.1:15173 -> 127.0.0.1:5173` to the Mac file
  `~/.local/bin/hemma-shared-tunnel`, reload LaunchAgent
  `com.paunchygent.hemma-shared-tunnel`, and record the exact line in the
  runbook.
- Import the HuleEdu staging proof-subject export written by
  TASK-HULE-REP-0087 with `consume-huleedu-subject-export`, so the fixed
  `skriptoteket-proof-*` accounts hold their mapped roles.
- Skriptoteket owns the hemma-dev compose file, pdm lifecycle commands
  (build, start, status, stop, reset), and a staging runbook. The
  skill-repository `local-devops` and `hemma-devops` Skriptoteket references
  point to them; their exact wording is presented to the user before editing.
- Non-goals: public DNS, TLS, or edge routes; production stack changes;
  production data; source control for the Mac tunnel script.

## Contract Inputs

- Retained plan
  `.orchestration/context/sessions/01a0e51f-20f9-76fd-9425-b0ffa4866168/evidence/planning/TASK-SKRIPT-REP-0034/plan.md`,
  D1-D14, and the discovery records it lists.
- Depends on TASK-HULE-REP-0087 merged and deployed to HuleEdu staging.
- Production shape `compose.prod.yaml`; runner limits
  `src/skriptoteket/infrastructure/runner/docker/execution.py`; identity
  verifier `src/skriptoteket/infrastructure/security/huleedu_internal_identity.py`;
  import command `src/skriptoteket/cli/commands/consume_huleedu_subject_export.py`.

## Core Vertical And Performance

A proof contributor opens `http://127.0.0.1:15173` on the Mac, signs in through
HuleEdu staging, returns to `/auth/callback`, opens the editor, runs one script
in the sandbox on the rootless runner, and sees its result and a failure
toast. Staging runs beside HuleEdu staging on one host; no material runtime
performance concern is identified beyond the runner's existing limits.

## Validation

- In-app browser walk of the core vertical at `http://127.0.0.1:15173`.
- The Hemma status command reports web, worker, database, and frontend healthy.
- `pdm run docs-validate` and `git diff --check` pass.

## Stop Conditions

- Stop if TASK-HULE-REP-0087 is not deployed to HuleEdu staging, or if the
  staging identity key or proof-subject export is missing.
- Stop before any change to production containers, production data, the
  system Docker socket, or HuleEdu staging containers other than joining its
  network.
- Stop if a runner limit fails on the rootless daemon; do not weaken limits.
- Never print or retain proof-account passwords or key material.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                       |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | The walk proves `main` after merge and push; failures are fixed forward. Source: retained D1.                                                               |
| D2  | Separate `skriptoteket-dev` project on the rootless daemon with its own Postgres, on `huleedu-dev_hule-network` as `skriptoteket-web`. Source: retained D2. |
| D3  | Full parity: web, worker, and runner; web and worker run as root on the rootless socket; runner image built into that daemon. Source: retained D4.          |
| D4  | The SPA runs as a Hemma user Vite unit on `127.0.0.1:5173`. Source: retained D5.                                                                            |
| D5  | Skriptoteket owns compose, pdm lifecycle commands, and runbook; skill-repository references point to them. Source: retained D6.                             |
| D6  | Mac tunnel forward `15173 -> 5173` added locally and recorded in the runbook. Source: retained D8, D14.                                                     |
| D7  | Script accounts come from the proof-subject import of the HuleEdu staging export. Source: retained D9, D12.                                                 |
| D8  | Depends on TASK-HULE-REP-0087. Source: retained D10.                                                                                                        |
| D9  | Acceptance is the contributor script-run walk plus a healthy status command. Source: retained D11.                                                          |
