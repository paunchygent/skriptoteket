---
type: task
id: TASK-SKRIPT-REP-0072
title: 'EPIC-SKILL-18: Skriptoteket compose secrets overlays for production, staging and observability'
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-11-23'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-11-23T22:05:51Z'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: "TASK-SKRIPT-REP-0072#closeout; whole retained review changes_requested at 38cca38c2; rereview-skriptoteket-97c5fe19f.md (d7b01fdf) changes_requested; rereview-skriptoteket-e298cb874.md (1f0e0f63) changes_requested; rereview-skriptoteket-67b12315c.md (6fe3a214) changes_requested; rereview-skriptoteket-0d5bc4180.md (b6b96bff) approved."
task_kind: repository
acceptance_criteria:
  - Given compose.prod.yaml, compose.hemma-dev.yaml and compose.observability.yaml, when the leaf closes, then none interpolates a secret, compose.secrets.prod.yaml, compose.secrets.hemma-dev.yaml and compose.secrets.observability.yaml hold them with required guards, and `docker compose config` with test values renders the same service environment.
backlog_document_profile: contract-derived
---

## Implementation Contract

Leaf of skill-repository `EPIC-SKILL-18` (decided terms D3, D6, D7, D8, D13,
D14, D15, D18, D19). Shared rules for every leaf:

- A secret reaches a process only through
  `agent-secrets run --set <set> -- <command>`; the set names below are
  declared in skill-repository `resources/agent-secrets.toml` (D18). Under
  sudo, pass `sudo --preserve-env="$AGENT_SECRETS_VARIABLES" ...`.
- Compose: every secret interpolation moves out of the base compose files into
  one secrets overlay file per project, written `${VAR:?run through <wrapper>}`.
  Only the deploy, recreate, build-with-secrets and one-off `run` paths pass
  the overlay, through the wrapper; `ps`, `logs`, `stop`, `config`, `exec` and
  boot paths use the base files and read no secret (D15). A path that runs
  `up` on existing production containers without the overlay changes to
  `start` (D15, docker docs: `start` never creates containers).
- Host-run code reads secrets from the process environment only; `.env`
  fallbacks for secret names (`load_dotenv`, `dotenv_values`, hand parsers,
  `source .env`) are removed for those names; `.env` keeps configuration.
- This leaf changes code only: no `.env` edit, no deploy, no container
  restart. The live switch is a later step, and production steps need Olof's
  approval (D13).

## Contract Inputs

Secrets: SECRET_KEY, SKRIPTOTEKET_DB_PASSWORD, SKRIPTOTEKET_DEV_DB_PASSWORD, EMAIL_SMTP_PASSWORD, GRAFANA_ADMIN_PASSWORD, HULEEDU_INTERNAL_API_KEY, SIR_CONVERT_A_LOT_V2_API_KEY. Literal defaults for secrets are removed. Absorbs the compose part of TASK-SKRIPT-REP-0017. Sets: `skriptoteket-prod`, `skriptoteket-staging`.

## Core Vertical And Performance

One wrapped command per changed path runs on Hemma after the tooling release, with its secret absent from `.env`.

## Validation

Focused tests for changed code (argv and environment of the wrapped commands,
no `.env` secret fallback); lint and typecheck on changed files.

## Stop Conditions

Stop and report a path that needs a secret at boot, or a secret that has to
reach a container this leaf cannot route through the wrapper.

## Decided Contract Terms

| ID  | Decided contract term                                   |
| --- | ------------------------------------------------------- |
| D1  | EPIC-SKILL-18 decided terms apply; this leaf adds none. |

## Closeout

The compose secrets overlays shipped in `e216f16b0` and were repaired through
the review chain below, which covered this task together with
TASK-SKRIPT-REP-0073 and TASK-SKRIPT-REP-0074.

- Whole retained review at `38cca38c2` (independent ruthless reviewer,
  `changes_requested`): admitted findings included a blocker on the deploy
  launcher opening the worker before the remote checkout was synced, highs on
  the inherited-environment secrets bypass, the bootstrap password reaching
  `docker exec` argv, a host-only `agent-secrets` call inside the web image,
  stale base-only recreation recipes in the compose comments, README and
  runbooks, and a medium on the retired lifecycle-proof password alias. The
  `config.py` dotenv finding was not admitted; D9 removes the `.env` secret
  lines at cutover.
- Rereview `d7b01fdf` at `97c5fe19f` (2026-11-23T21:24Z, `changes_requested`):
  the exec-argv and seed-wrapper findings were resolved; the stale-worker,
  secrets-bypass and overlay-example findings were not, and two new highs were
  admitted — the runbooks misclassified `BOOTSTRAP_SUPERUSER_EMAIL` as a
  secret and the new `.env` config parsers mishandled quoted values with
  inline comments.
- Rereview `1f0e0f63` at `e298cb874` (2026-11-23T21:38Z, `changes_requested`):
  the stale-worker and secrets-bypass findings and both new highs were
  resolved; the overlay finding stayed open because
  `compose.secrets.prod.yaml` still carried a runnable production `up -d`
  example, and one new high was admitted — the launcher handed the production
  set to an arbitrary operator-selected script.
- Rereview `6fe3a214` at `67b12315c` (2026-11-23T21:55Z, `changes_requested`):
  the overlay finding was resolved; `compose.secrets.prod.yaml` no longer
  carries a runnable recipe and points to the two deploy aliases. The launcher
  high stayed open because an operator-selected checkout directory could still
  supply an unchecked worker.
- Final rereview `b6b96bff` at `0d5bc4180` (2026-11-23T22:05:51Z, `approved`):
  the launcher opens only the tracked worker at the Git root of the fixed
  production checkout after a fast-forward sync. Code integration may proceed
  at the reviewed SHA.
- The live switch — production `.env` secret removal, deploys and service
  restarts on Hemma — is a later step outside this closeout; it needs the
  tooling release and Olof's approval (D13).
