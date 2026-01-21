---
type: adr
id: ADR-0065
title: "Runner contract v3 (state_update, structured errors, session promotions)"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2026-01-20
updated: 2026-01-20
links: ["EPIC-19", "ADR-0015", "ADR-0022", "ADR-0024", "ADR-0064"]
---

## Context

The current runner result contract v2 (`/work/result.json`) supports `outputs`, `next_actions`, and `state`, but it has
three foundation gaps:

1) `state` has ambiguous semantics (`null` vs `{}` vs missing)
2) errors are only `error_summary` (hard to handle deterministically)
3) there is no standard way for tools/platform to request/record promotions (artifact → session file)

## Decision

### 1) Extend `/work/result.json` to contract version 3

`/work/result.json` becomes `contract_version: 3` and adds:

- `state_update` with explicit semantics (`no_change|clear|set`)
- `error` (structured) alongside `error_summary`
- `promotions` for tool-requested session promotions + platform-applied outcomes

Contract v2 is not supported after cutover (no shims).

### 2) `state_update` semantics

`state_update` is one of:

- `{ "kind": "no_change" }`
- `{ "kind": "clear" }`
- `{ "kind": "set", "state": { ... } }`

This makes the runner boundary unambiguous and aligns with optimistic concurrency (`state_rev`) semantics.

### 3) Structured error payload

`error` is optional on success and SHOULD be present on failures.

Shape:

```json
{
  "kind": "tool_user_error|tool_runtime_error|contract_violation",
  "code": "string",
  "details": { "any": "json" }
}
```

`error_summary` remains the single safe, end-user-displayable string.

### 4) Promotions (hybrid semantics)

- Tools MAY request promotions from run artifacts → session files.
- Vault persistence is explicitly user-initiated (ADR-0059) and MUST NOT be tool-auto-triggered.

Promotion requests must be validated and applied atomically from the user perspective.

## Consequences

- Tool interactivity becomes deterministic (explicit state updates, structured errors).
- Multi-step workflows can safely reuse outputs via session promotions without introducing new parallel pipelines.
- Requires coordinated breaking cutover across runner + backend parsing + in-repo scripts/templates.
