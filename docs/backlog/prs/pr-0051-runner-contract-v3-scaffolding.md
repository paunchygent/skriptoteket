---
type: pr
id: PR-0051
title: "Runner: contract v3 scaffolding + request envelope schemas"
status: done
owners: "agents"
created: 2026-01-22
updated: 2026-01-22
stories:
  - "ST-19-01"
  - "ST-19-02"
  - "ST-19-03"
tags: ["backend", "runner", "contracts"]
acceptance_criteria:
  - "Contract v3 helper modules exist under infrastructure/runner/contracts with Pydantic schemas and validators."
  - "Workdir archive builder helper is extracted without changing V2 output behavior."
  - "RunnerRequest includes optional request_json_bytes for V3 without affecting V2."
  - "No runner lifecycle behavior changes; V2 remains the active contract."
  - "Docs capture the V3 module layout + DI switch plan (no feature flags)."
---

## Problem

EPIC-19 introduces the request.json envelope + contract v3 payloads, but the current runner code has no
schema-first helper modules to support a clean, parallel V3 implementation and DI switch.

## Goal

- Add contract v3 scaffolding (request envelope + promotions + state update + result payload models).
- Extract archive builder helpers so V3 can add `request.json` without touching Docker lifecycle code.
- Extend `RunnerRequest` with optional `request_json_bytes` for V3 without changing V2 behavior.
- Persist the agreed V3 module layout + DI switch plan (no feature flags).

## Non-goals

- Implementing V3 contract behavior or activating V3 in DI.
- Introducing FileRef resolver logic or promotion application behavior.
- Changing Docker execution/adoption flow.

## Decisions

- V3 contract models live under `src/skriptoteket/infrastructure/runner/contracts/`.
- `RunnerRequest` includes optional `request_json_bytes` for V3 (V2 sets `None`).
- Contract selection stays via the existing selector; no feature flags.
- After V3 cutover, remove V2 `request_factory.py` / `result_parser.py` and collapse the selector.

## Implementation plan

1. Add `infrastructure/runner/contracts/` schemas:
   - `request_envelope_v1.py`, `file_refs.py`, `state_update_v3.py`,
     `promotions_v3.py`, `result_payload_v3.py`.
2. Extract `WorkdirArchiveEntry` + `build_workdir_archive_from_entries` in
   `docker/workdir_archive.py`.
3. Extend `RunnerRequest` with `request_json_bytes: bytes | None` (V2 sets None).
4. Record V3 module layout + DI switch plan for a later V3 implementation (no feature flags).

## Test plan

- `pdm run lint`
- `pdm run typecheck`
- `pdm run pytest -q tests/unit/infrastructure/runner/test_docker_runner_execute.py \
  tests/unit/infrastructure/runner/test_docker_runner_adoption.py \
  tests/unit/infrastructure/runner/test_runner_contract_seams.py`
- `pdm run docs-validate`

## Rollback plan

- Revert new `contracts/` modules and archive helper extraction.
- Remove `request_json_bytes` from `RunnerRequest`.
