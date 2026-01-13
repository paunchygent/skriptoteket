---
type: adr
id: ADR-0058
title: "Tool datasets: per-user library + runner injection"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2026-01-12
---

## Context

Tools need reusable, user-specific lists (class rosters, group sets, templates). Today we only have a single settings
dict per tool, which is not suitable for CRUD-style datasets.

## Decision

- Add a per-user dataset library scoped to a tool.
- Persist datasets in a new table (e.g., `tool_datasets`) keyed by `(tool_id, user_id, name)` with JSON payload + size
  caps and timestamps.
- Provide CRUD API endpoints for list/read/create/update/delete with optimistic concurrency on updates.
- In the tool run UI, users select exactly one dataset for a run (optional).
- When a dataset is selected, inject it into runner memory as:
  - `memory["dataset"]`: the selected dataset payload (JSON object/array)
  - `memory["dataset_meta"]`: `{ "name": <string>, "id": <uuid>, "updated_at": <iso> }`
- Datasets are never written by the runner; writes only happen through the UI and API.

## Consequences

- Enables roster reuse without file re-uploads and supports multi-run flows like group generation.
- Requires new persistence, API, and UI surfaces plus validation/size caps.
- Tools must tolerate missing datasets (`memory["dataset"]` absent) and remain backward compatible.
