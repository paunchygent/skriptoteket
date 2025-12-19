---
type: adr
id: ADR-0024
title: "Tool sessions and UI payload persistence"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-19
links: ["ADR-0022", "ADR-0023", "PRD-script-hub-v0.2", "EPIC-10"]
---

## Context

Tool UI contract v2 (ADR-0022) introduces:

- `outputs[]` and `next_actions[]` that must be stored for replay/auditing
- `state` that must persist across sessions to enable multi-turn tools

We need a persistence model that:

- supports end users running tools interactively (multi-turn)
- supports both runner-based tools and curated apps (ADR-0023)
- remains safe (strict size budgets)
- is concurrency-safe (multi-tab, double-submit)

## Decision

### 1) Introduce `tool_sessions`

Add a `tool_sessions` table keyed by (`tool_id`, `user_id`, `context`) containing:

- `state` JSONB (size-capped)
- `state_rev` integer used for optimistic concurrency
- `created_at` / `updated_at`

### 2) Store normalized UI payload per run

Extend `tool_runs` with a stored, normalized `ui_payload` JSONB.

- `ui_payload` is produced by a deterministic normalizer (policy-driven allowlists + size budgets).
- The normalizer is the only code allowed to write `ui_payload` (no raw runner payload persistence).

### 3) Support multiple run “source kinds”

Extend `tool_runs` to represent either:

- tool-version runs: `source_kind="tool_version"` with `tool_id` + `version_id`
- curated app runs: `source_kind="curated_app"` with `curated_app_id` + `curated_app_version`

### 4) Minimal API surface

Provide a minimal API for interactive “turn taking”:

- `start_action`: create run, execute, persist `ui_payload`, persist updated state (state_rev)
- `get_session_state`: return current state + available actions
- `get_run`: return stored `ui_payload` + logs/artifacts metadata
- `list_artifacts`: return stored artifacts for a run

## Consequences

### Benefits

- Enables multi-turn tools with explicit, auditable state changes.
- Keeps UI output safe: only normalized payload is stored/rendered.
- Supports curated apps without forcing them into the tool version workflow.

### Tradeoffs / Risks

- Adds DB schema changes (new table + new columns) and migration complexity.
- Requires careful size budgeting to avoid DB bloat (state/payload caps are mandatory).
- Requires clear ownership for where actions come from (runner vs backend vs curated).

