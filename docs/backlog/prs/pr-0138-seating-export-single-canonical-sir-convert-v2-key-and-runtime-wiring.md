---
type: pr
id: PR-0138
title: "Klassrumskartan: single canonical Sir Convert v2 API key and runtime wiring remediation"
status: ready
owners: "agents"
created: 2026-03-25
updated: 2026-03-25
stories:
  - "ST-26-05"
tags: ["backend", "ops", "klassrumskartan", "export", "remediation", "sir-convert"]
dependencies:
  - "PR-0122"
  - "PR-0125"
acceptance_criteria:
  - "Given Skriptoteket integrates only with Sir Convert-a-Lot v2, when local, production, or operator docs describe the API key contract, then they use `SIR_CONVERT_A_LOT_V2_API_KEY` as the single canonical env key and do not document or rely on any obsolete alias."
  - "Given the local Docker hot-reload stack wires the export lane, when `compose.dev.yaml` injects Sir Convert settings, then it forwards only `SIR_CONVERT_A_LOT_V2_API_KEY` and defaults the upstream to `https://convert.hule.education` instead of a hidden laptop-local sidecar."
  - "Given local host-side export verification runs through `smoke-seating-export-readiness`, when the developer environment is configured with the canonical v2 base URL, API key, and callback base URL, then the smoke reaches export job creation without a missing-config or missing-key failure."
  - "Given the sibling `sir-convert-a-lot` repo exposes CLI/devops/runtime helpers, when they resolve the shared API key env var, then they use the same canonical `SIR_CONVERT_A_LOT_V2_API_KEY` name instead of a legacy alias."
  - "Given Hemma carries the production Skriptoteket and Sir Convert env files, when the canonical key rollout is applied, then the affected services are recreated so the new key contract is actually loaded into the running containers."
  - "Given developers explicitly need a laptop-local Sir Convert path, when that local profile is documented or implemented, then it is a CPU-only Docker dev container on the MacBook and never a ROCm-dependent or host-uvicorn default lane."
---

## Problem

The remaining local seating-export failure is not a PR-0137 import regression. The confirmed issue is
runtime drift: local host-side export verification fails first because the callback base URL is absent,
and then because the host runtime still expects a legacy Sir Convert API key shape in some places.

That ambiguity is currently baked into the repo through a dev compose fallback and scattered helper/docs
references to an obsolete API key alias. Keeping both names makes failures harder to diagnose and
encourages partial environment updates.

## Goal

Canonicalize the Skriptoteket export lane and related Sir Convert operational surfaces on one env key,
`SIR_CONVERT_A_LOT_V2_API_KEY`, while also making Hemma's public conversion domain the default local
development upstream. Any laptop-local converter path must remain an explicit CPU-only Docker debug
profile instead of an implicit default.

## Non-goals

- Changing the export artifact contract or teacher-facing export UX.
- Broad refactors of webhook orchestration or seating export handlers.
- Supporting both key names with compatibility shims or warnings.

## Implementation plan

- Add a focused remediation PR doc for the single-key rollout and link it from `docs/index.md`.
- Remove the dev-stack fallback from `compose.dev.yaml` so only `SIR_CONVERT_A_LOT_V2_API_KEY` is used and the default upstream is the Hemma public conversion domain.
- Update `.env.example`, local `.env`, and any local helper/docs references in this repo to the canonical v2 key and the Hemma-by-default runtime policy.
- Update the sibling `sir-convert-a-lot` repo where CLI/devops/runtime references still use the legacy key.
- Update Hemma env files and recreate affected Skriptoteket and Sir Convert services so running containers load the canonical key.

## Test plan

- `pdm run ruff check src/skriptoteket/config.py src/skriptoteket/cli/commands/smoke_seating_export_readiness.py`
- `pdm run docs-validate`
- `BOOTSTRAP_SUPERUSER_EMAIL=... PYTHONPATH=src pdm run python -m skriptoteket.cli smoke-seating-export-readiness --timeout-seconds 90 --poll-interval-seconds 2`
- Hemma env verification plus service recreation for Skriptoteket and Sir Convert.

## Rollback plan

- Restore the previous env variable names in local and Hemma `.env` files.
- Recreate the affected services with the restored env contract.
- Revert the focused PR-0138 file and config/doc updates if the canonical rollout introduces an unexpected downstream dependency.
