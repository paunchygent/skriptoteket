---
type: pr
id: PR-0052
title: "Runner: request.json envelope + FileRef resolver + contract v3 parsing"
status: ready
owners: "agents"
created: 2026-01-22
updated: 2026-01-22
stories:
  - "ST-19-01"
  - "ST-19-02"
  - "ST-19-03"
tags: ["backend", "runner", "contracts"]
acceptance_criteria:
  - "Runner writes `/work/request.json` per ADR-0063 and removes env-var JSON payloads (no shims)."
  - "FileRef resolver stages inputs under `/work/input/` and request envelope manifests include `ref` mapping."
  - "Runner contract v3 parsing supports `state_update`, structured `error`, and promotions per ADR-0065."
  - "Selector is the only switch; no feature flags. V2 factory/parser are removed after cutover."
  - "Runner tests + docs contract validation pass."
---

## Problem

The runner currently uses env-var JSON payloads and contract v2 result parsing, which blocks the EPIC-19 foundation:
request.json envelope, FileRef staging, and explicit v3 state/error/promotions.

## Goal

- Implement request.json envelope (ADR-0063) and remove env-var JSON payloads (no shims).
- Resolve FileRefs and stage inputs under `/work/input/` (ADR-0064).
- Parse result.json contract v3 with explicit state_update + structured errors + promotions (ADR-0065).
- Cut over via selector only; remove V2 factory/parser after V3 is active.

## Non-goals

- UI changes for file pickers or vault workflows.
- Execution worker architecture changes beyond required seams.
- Any feature-flag based rollout.

## Implementation plan

1. **ST-19-01: request.json envelope**
   - Add V3 request factory to build `RunnerRequestEnvelopeV1` and write `/work/request.json`.
   - Remove env-var JSON payloads for V3.
   - Update runner toolkit + script bank to read request.json.
2. **ST-19-02: FileRef resolver**
   - Add FileRef resolver protocol + implementation.
   - Stage files into `/work/input/` and include `ref` mapping in request.json.
3. **ST-19-03: contract v3 parsing**
   - Add V3 result parser + state_update/error/promotions handling.
4. **Cutover**
   - Switch selector to V3 contract (no feature flags).
   - Delete V2 factory/parser modules and tests.

## Test plan

- `pdm run lint`
- `pdm run typecheck`
- `pdm run pytest -q tests/unit/infrastructure/runner/...` (new V3 tests + existing runner tests)
- `pdm run docs-validate` (after story/epic updates)

## Rollback plan

- Revert selector to V2 contract (if still present) or revert PR entirely.
