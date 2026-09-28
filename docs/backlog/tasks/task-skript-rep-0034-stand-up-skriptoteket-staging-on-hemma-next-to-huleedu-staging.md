---
type: task
id: TASK-SKRIPT-REP-0034
title: Stand up Skriptoteket staging on Hemma next to HuleEdu staging
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-09-28'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - A skriptoteket-dev compose project on Hemma's rootless daemon runs its own Postgres, web, worker, and runner image; web answers as skriptoteket-web on huleedu-dev_hule-network, publishes only on 127.0.0.1:18000, and trusts the HuleEdu staging identity key; web and worker share artifact storage at matching paths
  - Start and reset run db-upgrade on the staging database before web starts; a fresh-volume start and a repeat start both succeed; reset touches only skriptoteket-dev resources
  - A Hemma user Vite unit serves the Skriptoteket frontend on 127.0.0.1:5173 with protected /api proxied to the Gateway at 127.0.0.1:18080 and backend and public-API routes to 127.0.0.1:18000, and the Mac tunnel forwards 127.0.0.1:15173 to it
  - The proof-subject import runs with --apply, and a repeatable setup step creates one harmless staging tool whose maintainer is the proof contributor, with the contributor's draft
  - In the in-app browser at http://127.0.0.1:15173 the proof contributor signs in through HuleEdu staging, returns to /auth/callback, locks and runs the draft in the editor sandbox, and sees its result; then a named reversible action recorded beforehand shows an existing failure toast and the page stays usable
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
  `web` and `worker` share project-owned artifact storage at the same paths as
  the production shape.
- `web` joins `huleedu-dev_hule-network` under alias `skriptoteket-web`, so the
  HuleEdu staging Gateway route `/api` to `http://skriptoteket-web:8000`
  reaches it, and publishes only on Hemma `127.0.0.1:18000`. `web` trusts the
  HuleEdu staging internal identity public key through
  `HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH`, key id, issuer, and audience
  settings, with the staging key directory mounted read-only.
- `web` and `worker` run as container root, mount the rootless socket, and set
  `DOCKER_HOST` to it; the per-run runner keeps its existing limits.
- Start and reset first bring up only the staging database, wait for it, run
  `db-upgrade` to the checked-out revision, then start `web` and `worker`.
  Later starts reconcile the schema before `web` starts. Reset removes only
  `skriptoteket-dev` resources; it never resets HuleEdu identities or removes
  the external HuleEdu network.
- A Hemma user systemd unit runs the Skriptoteket Vite dev server on
  `127.0.0.1:5173`, like `huleedu-vite-dev.service`. Protected `/api` goes to
  the HuleEdu staging Gateway at `127.0.0.1:18080`; the backend and public-API
  proxy targets go to `127.0.0.1:18000`. The Sir Convert route is out of scope.
- Add the forward `127.0.0.1:15173 -> 127.0.0.1:5173` to the Mac file
  `~/.local/bin/hemma-shared-tunnel`, reload LaunchAgent
  `com.paunchygent.hemma-shared-tunnel`, and record the exact line in the
  runbook.
- Import the HuleEdu staging proof-subject export written by
  TASK-HULE-REP-0087 with
  `consume-huleedu-subject-export --export-json <recorded path> --apply`, so
  `skriptoteket-proof-user`, `-contributor`, and `-admin` hold their mapped
  roles. A repeatable setup step in start and reset then uses existing
  application operations to create one harmless staging tool, make the proof
  contributor its maintainer, and create the contributor's draft. The runbook
  records the fixture and its rerun procedure.
- Skriptoteket owns the hemma-dev compose file, pdm lifecycle commands
  (build, start, status, stop, reset), and a staging runbook. The
  skill-repository `local-devops` and `hemma-devops` Skriptoteket references
  point to them; their exact wording is presented to the user before editing.
- Non-goals: public DNS, TLS, or edge routes; production stack changes;
  production data or tools; the Sir Convert route; source control for the Mac
  tunnel script.

## Contract Inputs

- Retained plan
  `.orchestration/context/sessions/01a0e51f-20f9-76fd-9425-b0ffa4866168/evidence/planning/TASK-SKRIPT-REP-0034/plan.md`,
  D1-D21, the discovery records it lists, and its advisory second opinion
  `architecture-second-opinion.md` F3, F4, F6.
- Depends on TASK-HULE-REP-0087 merged and deployed to HuleEdu staging.
- Production shape `compose.prod.yaml`; runner limits
  `src/skriptoteket/infrastructure/runner/docker/execution.py`; identity
  verifier `src/skriptoteket/infrastructure/security/huleedu_internal_identity.py`;
  schema startup check `src/skriptoteket/web/startup_checks.py`; import command
  `src/skriptoteket/cli/commands/consume_huleedu_subject_export.py`; sandbox
  rules `src/skriptoteket/application/scripting/handlers/run_sandbox.py`; Vite
  proxy lanes `frontend/apps/skriptoteket/vite.config.ts`.

## Core Vertical And Performance

The proof contributor opens `http://127.0.0.1:15173` on the Mac, signs in
through HuleEdu staging, returns to `/auth/callback`, opens the fixture tool's
draft in the editor, locks it, runs it in the sandbox on the rootless runner,
and sees its result. A named, reversible action recorded before it runs then
shows an existing failure toast, and the page stays usable. Staging runs beside
HuleEdu staging on one host; no material runtime performance concern is
identified beyond the runner's existing limits.

## Validation

- A fresh-volume start and a repeat start both succeed.
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
- Do not cause an uncontrolled staging outage to produce the failure toast, and
  do not count an inline sandbox error as the toast.
- Never print or retain proof-account passwords or key material.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                           |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | The walk proves `main` after merge and push; failures are fixed forward. Source: retained D1.                                                                                   |
| D2  | Separate `skriptoteket-dev` project on the rootless daemon with its own Postgres, on `huleedu-dev_hule-network` as `skriptoteket-web`. Source: retained D2.                     |
| D3  | Full parity: web, worker, and runner; web and worker run as root on the rootless socket; runner image built into that daemon. Source: retained D4.                              |
| D4  | The SPA runs as a Hemma user Vite unit on `127.0.0.1:5173`. Source: retained D5.                                                                                                |
| D5  | Skriptoteket owns compose, pdm lifecycle commands, and runbook; skill-repository references point to them. Source: retained D6.                                                 |
| D6  | Mac tunnel forward `15173 -> 5173` added locally and recorded in the runbook. Source: retained D8, D14.                                                                         |
| D7  | Script accounts come from the proof-subject import of the HuleEdu staging export. Source: retained D9, D12.                                                                     |
| D8  | Depends on TASK-HULE-REP-0087. Source: retained D10.                                                                                                                            |
| D9  | Acceptance is the contributor script-run walk plus a healthy status command. Source: retained D11.                                                                              |
| D10 | Import with `--apply`; a repeatable setup step creates one staging tool maintained by the proof contributor, with the contributor's draft. Source: retained D16.                |
| D11 | Web publishes only on `127.0.0.1:18000`; Vite sends protected `/api` to the Gateway and backend and public-API routes to 18000; Sir Convert out of scope. Source: retained D17. |
| D12 | Start and reset run `db-upgrade` before web starts; shared artifact storage; reset limited to `skriptoteket-dev`; fresh-volume and repeat start proven. Source: retained D19.   |
| D13 | The failure toast comes from a named, reversible existing action recorded before it runs. Source: retained D21.                                                                 |
