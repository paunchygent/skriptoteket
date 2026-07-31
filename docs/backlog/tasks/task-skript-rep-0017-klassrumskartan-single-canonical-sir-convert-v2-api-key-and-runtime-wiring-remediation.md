---
type: task
id: TASK-SKRIPT-REP-0017
title: 'Klassrumskartan: single canonical Sir Convert v2 API key and runtime wiring
  remediation'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- Given Skriptoteket integrates only with Sir Convert-a-Lot v2, when local, production,
  or operator docs describe the API key contract, then they use `SIR_CONVERT_A_LOT_V2_API_KEY`
  as the single canonical env key and do not document or rely on any obsolete alias.
- Given the local Docker hot-reload stack wires the export lane, when `compose.dev.yaml`
  injects Sir Convert settings, then it forwards only `SIR_CONVERT_A_LOT_V2_API_KEY`
  and defaults the upstream to `https://convert.hule.education` instead of a hidden
  laptop-local sidecar.
- Given local host-side export verification runs through `smoke-seating-export-readiness`,
  when the developer environment is configured with the canonical v2 base URL, API
  key, and callback base URL, then the smoke reaches export job creation without a
  missing-config or missing-key failure.
- Given the sibling `sir-convert-a-lot` repo exposes CLI/devops/runtime helpers, when
  they resolve the shared API key env var, then they use the same canonical `SIR_CONVERT_A_LOT_V2_API_KEY`
  name instead of a legacy alias.
- Given Hemma carries the production Skriptoteket and Sir Convert env files, when
  the canonical key rollout is applied, then the affected services are recreated so
  the new key contract is actually loaded into the running containers.
- Given developers explicitly need a laptop-local Sir Convert path, when that local
  profile is documented or implemented, then it is a CPU-only Docker dev container
  on the MacBook and never a ROCm-dependent or host-uvicorn default lane.
---

## Context

Source: `docs/backlog/prs/pr-0138-seating-export-single-canonical-sir-convert-v2-key-and-runtime-wiring.md`. Klassrumskartan: single canonical Sir Convert v2 API key and runtime wiring remediation.

The remaining local seating-export failure is not a PR-0137 import regression. The confirmed issue is runtime drift: local host-side export verification fails first because the callback base URL is absent, and then because the host runtime still expects a legacy Sir Convert API key shape in some places. That ambiguity is currently baked into the repo through a dev compose fallback and scattered helper/docs references to an obsolete API key alias. Keeping both names makes failures harder to diagnose and encourages partial environment updates. Canonicalize the Skriptoteket export lane and related Sir Convert operational surfaces on one env key, `SIR_CONVERT_A_LOT_V2_API_KEY`, while also making

## Impact And Escalation

The source task remains bounded to its repository-owned surface; product behavior or unapproved scope escalates to the parent story/epic.

## Decision And Assumption Ledger

| ID | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | --- | --- | --- | --- | --- |
| MIG-TASK-SKRIPT-REP-0017 | migration | closed | How is source meaning preserved? | Preserve the source task contract, current relationships, and status while changing identity only. | ST-SKILL-08-06; TASK-SKRIPT-REP-0003 |

## Contract Inputs

- Source task/PR and audit-approved migration authority.
- Current story or repository relationship in candidate frontmatter.

## Plan

Execute only the bounded plan represented by the source record; do not add scope during migration.

## Implementation Steps

1. Preserve the source implementation or proof sequence.
2. Verify current relationships and focused evidence at task closeout.

## Proof

The source proof obligations are retained as historical evidence below; no execution proof is asserted by this candidate.

## Validation

Run the task-selected focused gates and repository docs validation after parent integration.

## Stop Conditions

Stop for missing authority, unresolved identity/relationship, terminal ancestry, or scope expansion.

## Lessons Learned

The source material is retained verbatim below for migration fidelity.

## Notes

### Source evidence

### Problem

The remaining local seating-export failure is not a PR-0137 import regression. The confirmed issue is
runtime drift: local host-side export verification fails first because the callback base URL is absent,
and then because the host runtime still expects a legacy Sir Convert API key shape in some places.

That ambiguity is currently baked into the repo through a dev compose fallback and scattered helper/docs
references to an obsolete API key alias. Keeping both names makes failures harder to diagnose and
encourages partial environment updates.

### Goal

Canonicalize the Skriptoteket export lane and related Sir Convert operational surfaces on one env key,
`SIR_CONVERT_A_LOT_V2_API_KEY`, while also making Hemma's public conversion domain the default local
development upstream. Any laptop-local converter path must remain an explicit CPU-only Docker debug
profile instead of an implicit default.

### Non-goals

- Changing the export artifact contract or teacher-facing export UX.
- Broad refactors of webhook orchestration or seating export handlers.
- Supporting both key names with compatibility shims or warnings.

### Implementation plan

- Add a focused remediation PR doc for the single-key rollout and link it from `docs/index.md`.
- Remove the dev-stack fallback from `compose.dev.yaml` so only `SIR_CONVERT_A_LOT_V2_API_KEY` is used and the default upstream is the Hemma public conversion domain.
- Update `.env.example`, local `.env`, and any local helper/docs references in this repo to the canonical v2 key and the Hemma-by-default runtime policy.
- Update the sibling `sir-convert-a-lot` repo where CLI/devops/runtime references still use the legacy key.
- Update Hemma env files and recreate affected Skriptoteket and Sir Convert services so running containers load the canonical key.

### Test plan

- `pdm run ruff check src/skriptoteket/config.py src/skriptoteket/cli/commands/smoke_seating_export_readiness.py`
- `pdm run docs-validate`
- `BOOTSTRAP_SUPERUSER_EMAIL=... PYTHONPATH=src pdm run python -m skriptoteket.cli smoke-seating-export-readiness --timeout-seconds 90 --poll-interval-seconds 2`
- Hemma env verification plus service recreation for Skriptoteket and Sir Convert.

### Rollback plan

- Restore the previous env variable names in local and Hemma `.env` files.
- Recreate the affected services with the restored env contract.
- Revert the focused PR-0138 file and config/doc updates if the canonical rollout introduces an unexpected downstream dependency.

## Readiness

No specialist approval is asserted; parent review remains required.

## Closeout

No closeout evidence is asserted in this candidate.
