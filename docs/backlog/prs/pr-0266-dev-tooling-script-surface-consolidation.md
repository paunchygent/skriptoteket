---
type: pr
id: PR-0266
title: "Dev tooling script surface consolidation"
status: done
owners: "agents"
created: 2026-04-14
updated: 2026-04-14
stories: []
tags: ["tooling", "local-dev", "docs-as-code"]
acceptance_criteria:
  - "Given pyproject scripts should stay durable, when Docker dev stack operations are needed, then one broad command exposes stable subcommands instead of one PDM script per Compose flag combination."
  - "Given observability stack operations have the same shape, when Prometheus/Grafana/Jaeger/Loki are operated locally, then one broad command exposes stable subcommands instead of one PDM script per Compose verb."
  - "Given the dev stack must remain easy to operate, when the broad command runs start/recreate/build/reset paths, then it still applies `alembic upgrade head` through the Docker web service."
  - "Given retained auth proof commands are named audit surfaces, when this cleanup audits pyproject, then those proof aliases are either intentionally retained or moved only through a separately governed proof-runner slice."
  - "Given active runbooks and agent rules guide daily work, when duplicated aliases are removed, then current operational docs point to the surviving broad command surface."
---

## Problem

`pyproject.toml` has begun to accumulate narrow script aliases for small command variations. The
Docker dev workflow is the clearest example: multiple `dev-*` entries repeat the same Compose files
and migration step with only minor flag differences.

## Goal

Consolidate the day-to-day Docker dev stack controls behind one broad command:

- `pdm run dev-stack start`
- `pdm run dev-stack stop`
- `pdm run dev-stack restart`
- `pdm run dev-stack recreate`
- `pdm run dev-stack build-start`
- `pdm run dev-stack rebuild`
- `pdm run dev-stack build-start-clean`
- `pdm run dev-stack db-upgrade`
- `pdm run dev-stack db-reset`
- `pdm run dev-stack logs`
- `pdm run dev-stack ps`

Consolidate the observability Compose controls behind one broad command:

- `pdm run obs-stack start`
- `pdm run obs-stack stop`
- `pdm run obs-stack restart`
- `pdm run obs-stack logs`
- `pdm run obs-stack status`

Also record the audit boundary: retained PR proof aliases remain for now because their names are
part of existing evidence contracts.

## Non-goals

- Do not rename retained PR proof command surfaces in this slice.
- Do not change Docker Compose service definitions.
- Do not start, stop, rebuild, or reset the shared local dev stack as part of validation.
- Do not redesign frontend, SDS, or textbook corpus tooling in this first cleanup.

## Implementation plan

1. Add small Python dispatchers with explicit subcommands for dev and observability stacks.
2. Replace duplicated Docker dev and observability PDM aliases with `dev-stack` and `obs-stack`.
3. Remove the unreferenced host-process `kill-dev` shortcut.
4. Update active agent rules and runtime error copy to point at the broad command.
5. Add unit tests for command construction and failure handling.
6. Leave historical backlog evidence untouched where it records old commands that were actually run.

## Audit disposition

- Retained PR proof aliases (`pr-0252-*` through `pr-0262-*`) remain because they are named
  evidence surfaces in backlog/review docs and retained manifests. If they are consolidated later,
  do it as a governed proof-runner slice that preserves manifest command semantics.
- Frontend aliases remain because they mirror stable package-manager verbs (`dev`, `build`,
  `typecheck`, `lint`, `test`, watch, coverage) and are common daily entrypoints.
- Admin/CLI aliases remain because they are product operations over the single
  `skriptoteket.cli` surface and carry stable user-facing intent.
- SDS and textbook-corpus aliases are candidates for a later corpus/tooling consolidation if those
  workflows become active again; this slice does not rename historical domain workflow commands.
- `shellcheck`/`shellcheck-all`, `skills-prompt`/`skills-validate`, and
  `openapi-export-v1`/`fe-gen-api-types` remain because each pair covers a different operating
  mode: targeted vs repo-wide, prompt generation vs validation, schema export vs generated client
  refresh.

## Test plan

- `pdm run pytest -q tests/unit/scripts/test_dev_stack.py`
- `pdm run pytest -q tests/unit/scripts/test_obs_stack.py`
- `pdm run pytest -q tests/unit/infrastructure/runner/test_docker_runner_execute.py`
- `pdm run python -m scripts.dev_stack --help`
- `pdm run python -m scripts.obs_stack --help`
- `pdm run docs-validate`
- `pdm run ruff check scripts/_command_dispatch.py scripts/dev_stack.py scripts/obs_stack.py tests/unit/scripts/test_dev_stack.py tests/unit/scripts/test_obs_stack.py`
- `pdm run ruff format --check scripts/_command_dispatch.py scripts/dev_stack.py scripts/obs_stack.py tests/unit/scripts/test_dev_stack.py tests/unit/scripts/test_obs_stack.py`

## Rollback plan

Restore the previous `dev-*` and `obs-*` PDM aliases, remove the new dispatcher modules/tests, and
return active docs/error copy to the old commands.
