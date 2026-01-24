---
type: story
id: ST-19-03
title: "Runner contract v3: structured errors + state_update + promotions"
status: done
owners: "agents"
created: 2026-01-20
epic: "EPIC-19"
acceptance_criteria:
  - "Given a runner tool completes, when writing `/work/result.json`, then it uses `contract_version: 3` and includes `state_update` with explicit semantics (`no_change|clear|set`)."
  - "Given a runner tool fails, when writing `/work/result.json`, then it includes a structured `error` payload (`kind`, `code`, optional `details`) alongside `error_summary`."
  - "Given a tool requests session promotions, when the run is finalized, then promotions are applied (or the run fails) and no partial interactive state/actions are exposed."
  - "Given the platform is upgraded, then contract v2 is rejected (no shims) and in-repo scripts are updated."
dependencies:
  - "ADR-0015"
  - "ADR-0022"
  - "ST-19-02"
  - "ADR-0065"
ui_impact: "No"
data_impact: "No"
---

## Context

We currently use contract v2 (`/work/result.json`) with:

- `state: dict | null` (ambiguous semantics for “no change” vs “clear”)
- `error_summary` only (insufficient for deterministic handling + debugging)
- no standard way for tools/platform to request/record promotions (artifact → session/vault)

PR-0048 made state semantics explicit internally (platform-side). This story makes those semantics explicit at the
runner boundary too.

## Notes

- This story is explicitly **breaking** by design (no migration path). Runner/app/tool scripts are upgraded together.
- ADR updates (ADR-0015 + ADR-0022 + ADR-0024) must be reviewed before implementation.

## Proposed contract v3 additions (shape sketch)

- `state_update`:
  - `{ "kind": "no_change" }`
  - `{ "kind": "clear" }`
  - `{ "kind": "set", "state": {...} }`
- `error` (optional on success):
  - `{ "kind": "tool_user_error|tool_runtime_error|contract_violation", "code": "string", "details": {...}? }`
- `promotions` (optional):
  - requested session promotions and applied promotion outcomes (for auditability and strict failure on partial
    persistence)

Vault persistence is explicitly user-initiated (ADR-0059 / ST-14-36) and must not be tool-auto-triggered.

## Implementation plan

1) Runner (`runner/_runner.py`)

- Write `contract_version: 3` and emit `state_update` instead of `state`.
- Emit structured `error` alongside `error_summary` on failure.

2) Backend parsing + normalization

- Add a v3 parser + Pydantic models and delete v2 parsing after cutover.
- Apply `state_update` semantics consistently in:
  - synchronous handlers (initial runs + actions)
  - queued worker finalization

3) Promotions integration

- Wire promotion requests from `result.json` into the promotion primitives from ST-19-02.
- Strict failure invariant: if a run returned next actions but promotion/state persistence fails, fail the run and do not
  expose broken interactivity.

## Test plan

- Unit: runner contract parsing rejects v2 after cutover.
- Unit: `state_update` semantics are correct and `state_rev` increments on interactive turns.
- Integration: session promotions requested by a tool result in session file availability (or fail run strictly).
